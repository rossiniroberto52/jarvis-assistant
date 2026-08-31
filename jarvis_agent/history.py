import sqlite3
import datetime
import os
import re

DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis_history.db")
DEFAULT_PRUNE_DAYS = 30

_SENSITIVE_PATTERNS = [
    re.compile(r'(senha|password|passwd|pwd)\b[^\n]{0,30}?\s*[:=é]\s*\S+', re.IGNORECASE),
    re.compile(r'(token|api[_-]?key|secret|chave)\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),
    re.compile(r'ghp_[a-zA-Z0-9]{36}'),
    re.compile(r'AKIA[0-9A-Z]{16}'),
    re.compile(r'[a-zA-Z0-9]{32,}(?=\s|$)'),
]

def _redact(text):
    """Mascara dados sensíveis (senhas, tokens, API keys) antes de persistir."""
    if not text:
        return text
    for pattern in _SENSITIVE_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_tables(conn)
    return conn

def _ensure_tables(conn):
    """Cria tabelas e triggers se não existirem. Chamado automaticamente em _connect()."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS comandos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            comando TEXT NOT NULL,
            resposta TEXT,
            backend_usado TEXT,
            duracao_ms INTEGER,
            relevancia INTEGER DEFAULT 0
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS comandos_fts USING fts5(
            comando,
            resposta,
            content='comandos',
            content_rowid='id',
            tokenize='unicode61'
        );

        CREATE TRIGGER IF NOT EXISTS comandos_ai AFTER INSERT ON comandos BEGIN
            INSERT INTO comandos_fts(rowid, comando, resposta)
            VALUES (new.id, new.comando, new.resposta);
        END;

        CREATE TRIGGER IF NOT EXISTS comandos_ad AFTER DELETE ON comandos BEGIN
            INSERT INTO comandos_fts(comandos_fts, rowid, comando, resposta)
            VALUES ('delete', old.id, old.comando, old.resposta);
        END;

        CREATE TRIGGER IF NOT EXISTS comandos_au AFTER UPDATE ON comandos BEGIN
            INSERT INTO comandos_fts(comandos_fts, rowid, comando, resposta)
            VALUES ('delete', old.id, old.comando, old.resposta);
            INSERT INTO comandos_fts(rowid, comando, resposta)
            VALUES (new.id, new.comando, new.resposta);
        END;

        CREATE INDEX IF NOT EXISTS idx_comandos_timestamp ON comandos(timestamp);
        CREATE INDEX IF NOT EXISTS idx_comandos_relevancia ON comandos(relevancia DESC);
    """)
    conn.commit()

def save_command(comando, resposta=None, backend_usado="erro", duracao_ms=None):
    now = datetime.datetime.now().isoformat()
    conn = _connect()
    cursor = conn.execute(
        """INSERT INTO comandos (timestamp, comando, resposta, backend_usado, duracao_ms)
           VALUES (?, ?, ?, ?, ?)""",
        (now, _redact(comando), _redact(resposta), backend_usado, duracao_ms)
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id

def _sanitize_fts_query(text):
    """Remove caracteres especiais que quebram a sintaxe do FTS5 MATCH."""
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def search_similar(comando_texto, days=7, limit=3):
    """Busca comandos parecidos dos últimos N dias via FTS5."""
    safe_query = _sanitize_fts_query(comando_texto)
    if not safe_query:
        return []

    conn = _connect()
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    try:
        rows = conn.execute(
            """SELECT c.id, c.timestamp, c.comando, c.resposta, c.backend_usado,
                      c.duracao_ms, c.relevancia
               FROM comandos_fts fts
               JOIN comandos c ON c.id = fts.rowid
               WHERE comandos_fts MATCH ? AND c.timestamp >= ?
               ORDER BY c.relevancia DESC, c.timestamp DESC
               LIMIT ?""",
            (safe_query, cutoff, limit)
        ).fetchall()
    except Exception as e:
        print(f"[History] Erro FTS5 na busca: {e}")
        rows = []
    conn.close()
    return [dict(r) for r in rows]

def get_history(limit=20, relevante=False):
    conn = _connect()
    if relevante:
        rows = conn.execute(
            "SELECT * FROM comandos ORDER BY relevancia DESC, timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM comandos ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def increment_relevance(row_id):
    conn = _connect()
    conn.execute(
        "UPDATE comandos SET relevancia = relevancia + 1 WHERE id = ?",
        (row_id,)
    )
    conn.commit()
    conn.close()

def prune_old(days=DEFAULT_PRUNE_DAYS):
    """Remove comandos antigos com relevância baixa."""
    conn = _connect()
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    deleted = conn.execute(
        "DELETE FROM comandos WHERE timestamp < ? AND relevancia < 3",
        (cutoff,)
    ).rowcount
    conn.commit()
    conn.close()
    return deleted

# Garante que as tabelas existem ao importar o módulo
conn = _connect()
conn.close()
