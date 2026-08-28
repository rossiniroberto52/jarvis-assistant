import datetime
import os
import platform
import subprocess
import urllib.request
import urllib.parse
import json
import re
import psutil
import imaplib
import smtplib
import email
import webbrowser
from email.header import decode_header
from email.mime.text import MIMEText
from gmail_config import GMAIL_USER, GMAIL_APP_PASSWORD

N8N_SERVER_URL = "http://100.120.161.101:5678"

def get_time():
    """Retorna a data e hora atuais."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_system_info():
    """Retorna informações básicas de sistema (CPU, RAM, OS)."""
    cpu = platform.processor() or platform.machine()
    ram = psutil.virtual_memory()
    ram_str = f"{ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB"
    return f"OS: {platform.system()} {platform.release()} | CPU: {cpu} | RAM: {ram_str}"

def open_app(app_name: str):
    """Abre um aplicativo localmente no computador do usuário (ex: 'firefox', 'code', 'alacritty', 'vlc')."""
    app_lower = app_name.strip().lower()
    
    app_map = {
        "firefox": "firefox",
        "navegador": "firefox",
        "browser": "firefox",
        "code": "code",
        "vscode": "code",
        "editor": "code",
        "terminal": "alacritty",
        "alacritty": "alacritty",
        "vlc": "vlc",
        "arquivos": "thunar",
        "gerenciador de arquivos": "thunar"
    }
    
    executable = app_map.get(app_lower, app_lower)
    
    try:
        subprocess.Popen([executable], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Aplicativo '{executable}' aberto com sucesso no seu computador local, Senhor!"
    except Exception as e:
        return f"Erro ao tentar abrir '{executable}': {e}"

def open_url(url: str):
    """Abre uma página web ou URL diretamente no navegador local do computador do usuário."""
    try:
        webbrowser.open(url)
        return f"Página '{url}' aberta com sucesso no navegador local, Senhor!"
    except Exception as e:
        return f"Erro ao abrir URL: {e}"

def play_youtube(query: str):
    """Pesquisa e toca o primeiro vídeo/música correspondente diretamente no YouTube."""
    try:
        query_encoded = urllib.parse.quote(query)
        search_url = f"https://www.youtube.com/results?search_query={query_encoded}"
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
        
        target_url = search_url
        with urllib.request.urlopen(req, timeout=6) as resp:
            html = resp.read().decode("utf-8")
            video_ids = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
            if video_ids:
                target_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
                
        webbrowser.open(target_url)
        return f"Reproduzindo o vídeo '{query}' no YouTube, Senhor!"
    except Exception as e:
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
        return f"Pesquisa de '{query}' aberta no YouTube, Senhor!"

def run_command(cmd: str):
    """Executa um comando no terminal local e retorna a saída."""
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        out = res.stdout or res.stderr
        return out.strip() if out else "Comando executado sem retorno."
    except Exception as e:
        return f"Erro ao executar comando: {e}"

def list_tailscale_devices():
    """Lista todos os dispositivos e IPs da sua rede Tailscale."""
    try:
        res = subprocess.run("tailscale status", shell=True, capture_output=True, text=True, timeout=10)
        return res.stdout.strip() if res.stdout else "Nenhum dispositivo encontrado na rede Tailscale."
    except Exception as e:
        return f"Erro ao listar dispositivos Tailscale: {e}"

def run_remote_command(target: str, cmd: str, user: str = "rossini"):
    """Executa um comando SSH em um nó remoto da rede Tailscale."""
    try:
        ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {user}@{target} \"{cmd}\""
        res = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=20)
        out = res.stdout or res.stderr
        return out.strip() if out else "Comando remoto executado com sucesso sem saída."
    except Exception as e:
        return f"Erro ao executar comando remoto via SSH: {e}"

def fetch_remote_file(target: str, remote_file_path: str, local_destination: str = "/tmp/", user: str = "rossini"):
    """Copia/baixa um arquivo de uma máquina remota Tailscale via SCP."""
    try:
        scp_cmd = f"scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 {user}@{target}:\"{remote_file_path}\" \"{local_destination}\""
        res = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            return f"Arquivo '{remote_file_path}' transferido com sucesso para '{local_destination}'!"
        return f"Erro ao copiar arquivo: {res.stderr}"
    except Exception as e:
        return f"Erro na cópia remota: {e}"

def get_weather(city: str = ""):
    """Consulta a previsão do tempo atual para uma cidade."""
    try:
        city_name = city.strip() if city else "auto"
        city_encoded = urllib.parse.quote(city_name)
        url = f"https://wttr.in/{city_encoded}?format=3"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.read().decode("utf-8").strip()
    except Exception as e:
        return f"Erro ao buscar previsão do tempo: {e}"

def send_email(to_email: str, subject: str, body: str):
    """Envia um e-mail usando a conta do Gmail cadastrada."""
    if GMAIL_USER == "seu_email@gmail.com" or not GMAIL_APP_PASSWORD:
        return "Erro: Credenciais do Gmail não configuradas no arquivo gmail_config.py."
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = GMAIL_USER
        msg["To"] = to_email

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, [to_email], msg.as_string())
        return f"E-mail enviado com sucesso para {to_email}!"
    except Exception as e:
        return f"Erro ao enviar e-mail: {e}"

def read_latest_emails(limit: int = 3):
    """Lê os últimos e-mails da caixa de entrada do Gmail."""
    if GMAIL_USER == "seu_email@gmail.com" or not GMAIL_APP_PASSWORD:
        return "Erro: Credenciais do Gmail não configuradas no arquivo gmail_config.py."
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()
        if not email_ids:
            return "Nenhum e-mail encontrado na caixa de entrada."

        results = []
        latest_ids = email_ids[-limit:]
        for e_id in reversed(latest_ids):
            _, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8", errors="ignore")
                    from_email = msg.get("From", "Desconhecido")
                    results.append(f"- De: {from_email} | Assunto: {subject}")
        mail.logout()
        return "\n".join(results)
    except Exception as e:
        return f"Erro ao ler e-mails: {e}"

def trigger_n8n_workflow(path: str, data: dict = None):
    """Dispara um workflow ou webhook no servidor n8n."""
    try:
        url = f"{N8N_SERVER_URL}/webhook/{path.lstrip('/')}"
        payload = json.dumps(data or {}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return f"n8n Workflow acionado com sucesso (Status: {resp.status})"
    except Exception as e:
        return f"Falha ao acionar n8n no servidor: {e}"

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Obtém a data e hora atual do sistema.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Obtém dados sobre CPU, RAM e sistema operacional.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Abre um programa ou aplicativo localmente no computador do usuário (ex: 'firefox', 'code', 'terminal', 'vlc').",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Nome do programa para abrir (ex: 'firefox', 'code')"}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Abre uma URL ou site no navegador local do computador.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL completa do site para abrir (ex: 'https://google.com')"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_youtube",
            "description": "Busca e toca o primeiro vídeo/música correspondente diretamente no YouTube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Nome da música, artista ou vídeo para tocar no YouTube"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tailscale_devices",
            "description": "Lista os dispositivos, IPs e status de toda a sua rede privada Tailscale.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_remote_command",
            "description": "Executa um comando remoto via SSH em outro dispositivo da rede Tailscale.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "IP Tailscale ou nome do dispositivo alvo"},
                    "cmd": {"type": "string", "description": "Comando bash a ser executado remotamente"},
                    "user": {"type": "string", "description": "Usuário SSH (padrão 'rossini')"}
                },
                "required": ["target", "cmd"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_remote_file",
            "description": "Transfere/baixa um arquivo de outro dispositivo da rede Tailscale para este computador via SCP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "IP ou hostname do dispositivo remoto"},
                    "remote_file_path": {"type": "string", "description": "Caminho completo do arquivo remoto"},
                    "local_destination": {"type": "string", "description": "Pasta de destino local (padrão '/tmp/')"},
                    "user": {"type": "string", "description": "Usuário SSH (padrão 'rossini')"}
                },
                "required": ["target", "remote_file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Obtém a previsão do tempo atual de uma cidade.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Nome da cidade para consultar o clima"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_latest_emails",
            "description": "Lê os últimos e-mails recebidos na caixa de entrada do Gmail.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Quantidade de e-mails para ler (padrão: 3)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Envia um e-mail para um destinatário.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_email": {"type": "string", "description": "E-mail do destinatário"},
                    "subject": {"type": "string", "description": "Assunto do e-mail"},
                    "body": {"type": "string", "description": "Conteúdo do e-mail"}
                },
                "required": ["to_email", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Executa um comando bash/shell no sistema local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "O comando bash a ser executado"}
                },
                "required": ["cmd"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_n8n_workflow",
            "description": "Aciona uma automação/webhook no servidor n8n.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Caminho do webhook no n8n"}
                },
                "required": ["path"]
            }
        }
    }
]

TOOL_MAP = {
    "get_time": lambda kwargs: get_time(),
    "get_system_info": lambda kwargs: get_system_info(),
    "open_app": lambda kwargs: open_app(kwargs.get("app_name", "")),
    "open_url": lambda kwargs: open_url(kwargs.get("url", "")),
    "play_youtube": lambda kwargs: play_youtube(kwargs.get("query", "")),
    "list_tailscale_devices": lambda kwargs: list_tailscale_devices(),
    "run_remote_command": lambda kwargs: run_remote_command(kwargs.get("target", ""), kwargs.get("cmd", ""), kwargs.get("user", "rossini")),
    "fetch_remote_file": lambda kwargs: fetch_remote_file(kwargs.get("target", ""), kwargs.get("remote_file_path", ""), kwargs.get("local_destination", "/tmp/"), kwargs.get("user", "rossini")),
    "get_weather": lambda kwargs: get_weather(kwargs.get("city", "")),
    "read_latest_emails": lambda kwargs: read_latest_emails(kwargs.get("limit", 3)),
    "send_email": lambda kwargs: send_email(kwargs.get("to_email", ""), kwargs.get("subject", ""), kwargs.get("body", "")),
    "run_command": lambda kwargs: run_command(kwargs.get("cmd", "")),
    "trigger_n8n_workflow": lambda kwargs: trigger_n8n_workflow(kwargs.get("path", ""))
}
