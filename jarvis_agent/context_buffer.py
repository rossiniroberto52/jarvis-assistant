import os
import datetime

BUFFER_FILE = os.path.join(os.path.dirname(__file__), "context_buffer.md")

def init_context_buffer():
    """Garante a existência do arquivo context_buffer.md com estrutura inicial."""
    if not os.path.exists(BUFFER_FILE):
        header = """# Buffer de Contexto Histórico do JARVIS

## Visão Geral
Este arquivo serve como buffer persistente em disco (.md) para salvar históricos de conversas anteriores e economizar VRAM e RAM durante a execução dos modelos de linguagem.

## Histórico de Conversas Arquivadas
"""
        try:
            with open(BUFFER_FILE, "w", encoding="utf-8") as f:
                f.write(header)
        except Exception as e:
            print(f"[ContextBuffer] Erro ao inicializar {BUFFER_FILE}: {e}")

def get_context_buffer() -> str:
    """Retorna todo o conteúdo do buffer de contexto em Markdown."""
    init_context_buffer()
    try:
        with open(BUFFER_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"[ContextBuffer] Erro ao ler buffer: {e}")
        return f"Erro ao ler buffer de contexto: {e}"

def get_buffer_summary_snippet(max_chars: int = 800) -> str:
    """Retorna um resumo/trecho das últimas entradas do buffer para injeção no prompt do sistema."""
    text = get_context_buffer()
    if not text or len(text) <= max_chars:
        return text
    # Retorna o trecho mais recente (final do arquivo)
    return "... " + text[-max_chars:].strip()

def append_to_context_buffer(user_msg: str, assistant_msg: str):
    """Adiciona um par de mensagens (usuário e assistente) ao arquivo context_buffer.md."""
    init_context_buffer()
    timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    user_clean = str(user_msg or "").strip().replace("\n", " ")
    assistant_clean = str(assistant_msg or "").strip().replace("\n", " ")

    entry = f"\n### [{timestamp}]\n- **Senhor**: {user_clean}\n- **JARVIS**: {assistant_clean}\n"

    try:
        with open(BUFFER_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        print(f"[ContextBuffer] Erro ao salvar no buffer: {e}")

def trim_chat_history(chat_history: list, max_messages: int = 6) -> list:
    """
    Controla o tamanho da memória RAM/VRAM descartando mensagens antigas.
    As mensagens removidas são salvas permanentemente no context_buffer.md.
    Preserva a mensagem 'system' no topo e as últimas `max_messages`.
    """
    if not chat_history:
        return chat_history

    system_msg = chat_history[0] if chat_history[0].get("role") == "system" else None
    non_system = [m for m in chat_history if m.get("role") != "system"]

    if len(non_system) <= max_messages:
        return chat_history

    cut_idx = len(non_system) - max_messages
    while cut_idx > 0 and non_system[cut_idx].get("role") in ("tool", "assistant"):
        cut_idx -= 1

    to_archive = non_system[:cut_idx]
    to_keep = non_system[cut_idx:]

    # Extrai pares e salva no buffer
    i = 0
    while i < len(to_archive):
        msg = to_archive[i]
        role = msg.get("role")
        if role == "user":
            u_text = msg.get("content", "")
            a_text = ""
            if i + 1 < len(to_archive) and to_archive[i + 1].get("role") == "assistant":
                a_text = to_archive[i + 1].get("content", "")
                i += 2
            else:
                i += 1
            if u_text:
                append_to_context_buffer(u_text, a_text)
        else:
            i += 1

    trimmed_history = []
    if system_msg:
        trimmed_history.append(system_msg)
    trimmed_history.extend(to_keep)

    return trimmed_history
