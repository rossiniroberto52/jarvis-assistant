import datetime
import os
import platform
import subprocess
import shutil
import urllib.request
import urllib.parse
import json
import re
import yaml
import psutil
import imaplib
import smtplib
import email
import webbrowser
import base64
import html
from email.header import decode_header
from email.mime.text import MIMEText
from gmail_config import GMAIL_USER, GMAIL_APP_PASSWORD, GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE

WAHA_SERVER_URL = os.getenv("WAHA_SERVER_URL", "http://100.78.249.41:3000")
N8N_SERVER_URL = os.getenv("N8N_SERVER_URL", "http://100.120.161.101:5678")

LAST_ACCESS_FILE = os.path.join(os.path.dirname(__file__), ".last_access_date")

def get_time():
    """Retorna a data e hora atuais exatas do sistema do Senhor."""
    now = datetime.datetime.now()
    dias = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    dia_semana = dias[now.weekday()]
    mes = meses[now.month - 1]
    return f"{dia_semana}, {now.day} de {mes} de {now.year}, às {now.strftime('%H:%M:%S')}."

def _get_last_access_date():
    """Lê a data do último acesso do arquivo persistente."""
    try:
        if os.path.exists(LAST_ACCESS_FILE):
            with open(LAST_ACCESS_FILE, 'r') as f:
                return f.read().strip()
    except Exception:
        pass
    return None

def _save_last_access_date():
    """Salva a data atual como último acesso."""
    try:
        with open(LAST_ACCESS_FILE, 'w') as f:
            f.write(datetime.date.today().isoformat())
    except Exception:
        pass

def is_first_use_today():
    """Verifica se é a primeira vez que o usuário usa o JARVIS hoje."""
    today = datetime.date.today().isoformat()
    last_access = _get_last_access_date()
    return last_access != today

def generate_morning_briefing():
    """Gera um resumo matinal completo: clima, emails, calendário, tarefas, notícias."""
    now = datetime.datetime.now()
    dias = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    dia_semana = dias[now.weekday()]
    mes = meses[now.month - 1]
    
    briefing_parts = []
    
    # Header
    briefing_parts.append(f"BOM DIA! Hoje é {dia_semana}, {now.day} de {mes} de {now.year}.")
    briefing_parts.append("")
    
    # 1. Clima
    try:
        weather = get_weather("São Paulo")
        briefing_parts.append(f"🌤️ CLIMA: {weather}")
        briefing_parts.append("")
    except Exception as e:
        briefing_parts.append(f"🌤️ CLIMA: Não consegui puxar o tempo. Erro: {str(e)[:50]}")
        briefing_parts.append("")
    
    # 2. Emails recentes
    try:
        emails = read_latest_emails(3)
        if emails:
            briefing_parts.append("📧 EMAILS RECENTES:")
            briefing_parts.append(emails)
        else:
            briefing_parts.append("📧 EMAILS: Nenhum email novo.")
        briefing_parts.append("")
    except Exception as e:
        briefing_parts.append(f"📧 EMAILS: Erro ao buscar. {str(e)[:50]}")
        briefing_parts.append("")
    
    # 3. Calendário (Google Calendar)
    try:
        calendar = google_calendar_read("today", "today", 5)
        if calendar:
            briefing_parts.append("📅 AGENDA DE HOJE:")
            briefing_parts.append(calendar)
        else:
            briefing_parts.append("📅 AGENDA: Nenhum compromisso hoje.")
        briefing_parts.append("")
    except Exception as e:
        briefing_parts.append(f"📅 AGENDA: Erro ao buscar. {str(e)[:50]}")
        briefing_parts.append("")
    
    # 4. Tarefas (Google Tasks)
    try:
        tasks = google_tasks_read("today", 5)
        if tasks:
            briefing_parts.append("✅ TAREFAS PENDENTES:")
            briefing_parts.append(tasks)
        else:
            briefing_parts.append("✅ TAREFAS: Nenhuma tarefa pendente.")
        briefing_parts.append("")
    except Exception as e:
        briefing_parts.append(f"✅ TAREFAS: Erro ao buscar. {str(e)[:50]}")
        briefing_parts.append("")
    
    # 5. Resumo de notícias
    try:
        news = get_news_summary()
        if news:
            briefing_parts.append("📰 NOTÍCIAS DE HOJE:")
            briefing_parts.append(news)
        else:
            briefing_parts.append("📰 NOTÍCIAS: Sem resumo disponível.")
        briefing_parts.append("")
    except Exception as e:
        briefing_parts.append(f"📰 NOTÍCIAS: Erro ao buscar. {str(e)[:50]}")
        briefing_parts.append("")
    
    # 6. Status do sistema
    try:
        sys_info = get_system_info()
        briefing_parts.append(f"💻 SISTEMA: {sys_info}")
    except Exception:
        pass
    
    # Salvar último acesso
    _save_last_access_date()
    
    return "\n".join(briefing_parts)

def get_news_summary():
    """Busca um resumo de notícias de hoje via RSS feeds."""
    try:
        rss_feeds = [
            "https://rss.uol.com.br/feed/noticias.xml",
            "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml",
        ]
        
        headlines = []
        for feed_url in rss_feeds[:2]:
            try:
                req = urllib.request.Request(feed_url, headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) JARVIS/1.0'
                })
                with urllib.request.urlopen(req, timeout=5) as response:
                    content = response.read().decode('utf-8', errors='ignore')
                    
                    # Parse simples de RSS
                    title_pattern = re.compile(r'<title[^>]*>(.*?)</title>', re.DOTALL | re.IGNORECASE)
                    matches = title_pattern.findall(content)
                    
                    for match in matches[:3]:
                        clean = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', match)
                        clean = re.sub(r'<[^>]+>', '', clean).strip()
                        if clean and len(clean) > 10 and clean not in headlines:
                            headlines.append(clean)
            except Exception:
                continue
        
        if headlines:
            return "\n".join(f"• {h}" for h in headlines[:5])
        return None
        
    except Exception:
        return None

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
        webbrowser.open(url, new=0, autoraise=True)
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


def load_contacts():
    contacts_file = os.path.join(os.path.dirname(__file__), "contacts.json")
    if os.path.exists(contacts_file):
        try:
            with open(contacts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                normalized = {}
                for k, v in data.items():
                    if isinstance(v, str):
                        normalized[k] = {"number": v, "important": False}
                    elif isinstance(v, dict):
                        normalized[k] = {"number": v.get("number", ""), "important": bool(v.get("important", False))}
                return normalized
        except Exception:
            return {}
    return {}

def save_contacts(contacts_data):
    contacts_file = os.path.join(os.path.dirname(__file__), "contacts.json")
    with open(contacts_file, "w", encoding="utf-8") as f:
        json.dump(contacts_data, f, ensure_ascii=False, indent=4)

def mark_contact_important(name: str, is_important: bool = True):
    """Marca ou desmarca um contato da agenda como VIP/Importante."""
    contacts = load_contacts()
    target_key = None
    for k in contacts:
        if k.lower() == name.strip().lower() or name.strip().lower() in k.lower():
            target_key = k
            break
            
    if not target_key:
        return f"Contato '{name}' não encontrado na sua agenda, Senhor."
        
    contacts[target_key]["important"] = is_important
    save_contacts(contacts)
    status = "IMPORTANTE/VIP" if is_important else "comum"
    return f"O contato '{target_key}' foi atualizado como {status}, Senhor!"

_LAST_WHATSAPP_OPEN = 0

def check_whatsapp_messages(only_important: bool = True):
    """Abre ou foca o WhatsApp Web na tela do usuário para leitura manual."""
    global _LAST_WHATSAPP_OPEN
    import time

    contacts = load_contacts()
    important_list = [k for k, v in contacts.items() if v.get("important")]

    if only_important and not important_list:
        return "Senhor, nenhum contato foi marcado como importante/VIP ainda. O WhatsApp Web foi focado para leitura na tela."

    names_str = ", ".join(important_list) if important_list else "todos os contatos"
    now = time.time()

    if now - _LAST_WHATSAPP_OPEN < 180:
        return (f"A aba do WhatsApp Web já está aberta e ativa na tela do Senhor (contatos VIP: {names_str}). "
                f"IMPORTANTE: O JARVIS apenas foca o WhatsApp na tela para o Senhor ler. "
                f"O assistente NÃO tem acesso ao texto das mensagens e não pode ler o conteúdo em voz alta.")

    try:
        if important_list:
            num = contacts[important_list[0]]["number"]
            url = f"https://web.whatsapp.com/send?phone={num}"
        else:
            url = "https://web.whatsapp.com/"

        webbrowser.open(url, new=0, autoraise=True)
        _LAST_WHATSAPP_OPEN = now
        return (f"WhatsApp Web aberto com sucesso na tela do Senhor para os contatos prioritários ({names_str}). "
                f"IMPORTANTE: O JARVIS apenas abre o WhatsApp na tela para o Senhor ler diretamente. "
                f"O assistente NÃO tem acesso ao texto das mensagens e não lê o conteúdo.")
    except Exception as e:
        return f"Erro ao abrir WhatsApp Web: {e}"

def add_contact(name: str, phone_number: str, is_important: bool = False):
    """Salva/adiciona um novo contato de agenda no arquivo contacts.json do Jarvis."""
    try:
        contacts = load_contacts()
        phone_clean = re.sub(r"\D", "", phone_number)
        name_clean = name.strip()
        contacts[name_clean] = {
            "number": phone_clean or phone_number.strip(),
            "important": is_important
        }
        save_contacts(contacts)
        tag = "marcado como IMPORTANTE/VIP" if is_important else "salvo na sua agenda"
        return f"Contato '{name_clean}' ({phone_clean}) {tag} com sucesso, Senhor!"
    except Exception as e:
        return f"Erro ao salvar contato: {e}"

def send_whatsapp_via_waha(phone_or_chatid: str, message: str, session: str = "default"):
    """Envia mensagem de texto utilizando a API HTTP do WAHA no PC Principal (100.78.249.41:3000)."""
    url = f"{WAHA_SERVER_URL.rstrip('/')}/api/sendText"
    chat_id = phone_or_chatid if "@" in phone_or_chatid else f"{phone_or_chatid}@c.us"
    payload = json.dumps({
        "chatId": chat_id,
        "text": message,
        "session": session
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        if resp.status in (200, 201):
            return True, f"Mensagem enviada com sucesso via WAHA no PC Principal para {phone_or_chatid}, Senhor!"
        return False, f"WAHA respondeu com status {resp.status}"

def send_whatsapp_message(contact_or_phone: str = "", message: str = ""):
    """Envia mensagem no WhatsApp por nome de contato ou número de telefone (via WAHA no PC Principal com fallbacks)."""
    target = contact_or_phone.strip()
    msg_text = message.strip() if message and message.strip() else "Olá! Esta é uma mensagem do assistente Jarvis."

    contacts = load_contacts()
    for name, info in contacts.items():
        if name.lower() == target.lower() or target.lower() in name.lower():
            target = info.get("number", target)
            break

    phone_clean = re.sub(r'\D', '', target) if isinstance(target, str) else ""
    if phone_clean and not phone_clean.startswith("55") and len(phone_clean) in [10, 11]:
        phone_clean = "55" + phone_clean

    recipient = phone_clean or target

    # 1. Tentativa via WAHA (PC Principal)
    try:
        ok, res_waha = send_whatsapp_via_waha(recipient, msg_text)
        if ok:
            return res_waha
    except Exception as e:
        print(f"[WAHA] Tentativa via WAHA falhou ({e}), tentando fallback...")

    # 2. Fallback via n8n
    try:
        url = f"{N8N_SERVER_URL}/webhook/whatsapp"
        payload = json.dumps({"phone": recipient, "message": msg_text}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return f"Mensagem enviada com sucesso via n8n para {target}, Senhor!"
    except Exception:
        pass

    # 3. Fallback via WhatsApp Web local no navegador
    try:
        focused = False
        for cmd in [["wmctrl", "-a", "WhatsApp"], ["xdotool", "search", "--name", "WhatsApp", "windowactivate"]]:
            if shutil.which(cmd[0]):
                res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if res.returncode == 0:
                    focused = True
                    break

        msg_encoded = urllib.parse.quote(msg_text)
        wa_url = f"https://web.whatsapp.com/send?phone={recipient}&text={msg_encoded}" if recipient else "https://web.whatsapp.com/"
        webbrowser.open(wa_url)

        return f"Sucesso: WhatsApp Web aberto no navegador para {recipient} com a mensagem '{msg_text}', Senhor!"
    except Exception as e:
        return f"Erro ao enviar mensagem via WhatsApp: {e}"

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

def send_email(to_email: str = "", subject: str = "Mensagem do Jarvis", body: str = ""):
    """Envia um e-mail usando a conta do Gmail cadastrada (via OAuth2 Gmail API ou SMTP)."""
    target_email = to_email.strip() if to_email and to_email.strip() else GMAIL_USER

    # Tenta enviar via Gmail API (OAuth2)
    service = get_gmail_service()
    if service:
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = GMAIL_USER
            msg["To"] = target_email

            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
            service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
            return f"E-mail enviado com sucesso para {target_email}!"
        except Exception as e:
            err_msg = str(e)
            if len(err_msg) > 200:
                err_msg = err_msg[:200] + "..."
            return f"Erro ao enviar e-mail via Gmail API: {err_msg}"

    # Fallback para SMTP se GMAIL_APP_PASSWORD estiver configurado
    if GMAIL_USER and GMAIL_USER != "seu_email@gmail.com" and GMAIL_APP_PASSWORD:
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = GMAIL_USER
            msg["To"] = target_email

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                server.sendmail(GMAIL_USER, [target_email], msg.as_string())
            return f"E-mail enviado com sucesso para {target_email}!"
        except Exception as e:
            err_msg = str(e)
            if len(err_msg) > 200:
                err_msg = err_msg[:200] + "..."
            return f"Erro ao enviar e-mail via SMTP: {err_msg}"

    return "Erro: Credenciais do Gmail não configuradas (credentials.json/token.json do OAuth2 ou GMAIL_APP_PASSWORD no gmail_config.py)."

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_TOKEN_FILE = os.path.join(os.path.dirname(__file__), "calendar_token.json")

def get_calendar_service():
    """Autentica e retorna a instância do serviço da API do Google Calendar via OAuth2."""
    creds = None
    token_file = CALENDAR_TOKEN_FILE if os.path.exists(CALENDAR_TOKEN_FILE) else GMAIL_TOKEN_FILE

    if os.path.exists(token_file):
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(token_file, CALENDAR_SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                save_path = CALENDAR_TOKEN_FILE if os.path.exists(CALENDAR_TOKEN_FILE) else token_file
                with open(save_path, "w") as tf:
                    tf.write(creds.to_json())
            except Exception:
                creds = None

        if not creds:
            if not os.path.exists(GMAIL_CREDENTIALS_FILE):
                return None
            try:
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, CALENDAR_SCOPES)
                creds = flow.run_local_server(port=0)
                with open(CALENDAR_TOKEN_FILE, "w") as tf:
                    tf.write(creds.to_json())
            except Exception:
                return None

    try:
        from googleapiclient.discovery import build
        return build("calendar", "v3", credentials=creds)
    except Exception:
        return None

def _parse_event_datetime(time_str: str, default_date=None):
    """
    Converte strings flexíveis de data/hora (ex: '2026-09-02T15:00', '15:00', 'amanhã 10:00')
    para o formato ISO-8601 exigido pela API do Google Calendar (com fuso horário -03:00).
    """
    now = datetime.datetime.now()
    base_date = default_date or now
    time_str = time_str.strip().lower()

    if "amanhã" in time_str or "amanha" in time_str:
        base_date = (default_date or now) + datetime.timedelta(days=1)
        time_str = re.sub(r'amanhã|amanha', '', time_str).strip()
    elif "hoje" in time_str:
        base_date = default_date or now
        time_str = re.sub(r'hoje', '', time_str).strip()

    date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', time_str)
    if date_match:
        year, month, day = map(int, date_match.groups())
        base_date = base_date.replace(year=year, month=month, day=day)
    else:
        br_date_match = re.search(r'(\d{1,2})/(\d{1,2})(?:/(\d{4}))?', time_str)
        if br_date_match:
            day = int(br_date_match.group(1))
            month = int(br_date_match.group(2))
            year = int(br_date_match.group(3)) if br_date_match.group(3) else base_date.year
            base_date = base_date.replace(year=year, month=month, day=day)

    time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
    if time_match:
        hour, minute = map(int, time_match.groups())
        dt = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    else:
        dt = base_date.replace(hour=12, minute=0, second=0, microsecond=0)

    return dt.strftime("%Y-%m-%dT%H:%M:%S-03:00"), dt

def list_calendar_events(limit: int = 5):
    """Lista os próximos compromissos/eventos no Google Agenda a partir do horário atual."""
    service = get_calendar_service()
    if not service:
        return "Erro: Credenciais do Google Agenda não configuradas ou acesso pendente."

    try:
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now_iso,
            maxResults=limit,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return "Nenhum compromisso próximo encontrado no Google Agenda."

        event_list = ["Próximos compromissos no Google Agenda:"]
        for event in events:
            summary = event.get("summary", "Sem título")
            start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
            location = event.get("location", "")

            if "T" in str(start):
                try:
                    dt_part = start.split("T")
                    d_str = "/".join(dt_part[0].split("-")[::-1])
                    t_str = dt_part[1][:5]
                    time_display = f"{d_str} às {t_str}"
                except Exception:
                    time_display = start
            else:
                time_display = start

            if location:
                event_list.append(f"- {summary} ({time_display}) - Local: {location}")
            else:
                event_list.append(f"- {summary} ({time_display})")

        return "\n".join(event_list)
    except Exception as e:
        return f"Erro ao listar eventos do Google Agenda: {e}"

def create_calendar_event(summary: str, start_time: str, end_time: str = None, description: str = "", location: str = ""):
    """Cria um novo evento no Google Agenda (Google Calendar)."""
    service = get_calendar_service()
    if not service:
        return "Erro: Credenciais do Google Agenda não configuradas ou acesso pendente."

    try:
        start_iso, start_dt = _parse_event_datetime(start_time)
        if end_time:
            end_iso, _ = _parse_event_datetime(end_time, default_date=start_dt)
        else:
            end_dt = start_dt + datetime.timedelta(hours=1)
            end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%S-03:00")

        event_body = {
            "summary": summary.strip(),
            "description": description.strip() if description else "Evento criado pelo assistente Jarvis.",
            "start": {"dateTime": start_iso, "timeZone": "America/Fortaleza"},
            "end": {"dateTime": end_iso, "timeZone": "America/Fortaleza"}
        }

        if location and location.strip():
            event_body["location"] = location.strip()

        created_event = service.events().insert(calendarId="primary", body=event_body).execute()
        html_link = created_event.get("htmlLink", "")

        return f"Evento '{summary}' criado com sucesso no Google Agenda para {start_dt.strftime('%d/%m/%Y às %H:%M')}! (Link: {html_link})"
    except Exception as e:
        return f"Erro ao criar evento no Google Agenda: {e}"

def get_gmail_service():
    """Autentica e retorna a instância do serviço da API do Gmail via OAuth2."""
    creds = None
    if os.path.exists(GMAIL_TOKEN_FILE):
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, GMAIL_SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                with open(GMAIL_TOKEN_FILE, "w") as token_file:
                    token_file.write(creds.to_json())
            except Exception:
                creds = None

        if not creds:
            if not os.path.exists(GMAIL_CREDENTIALS_FILE):
                return None
            try:
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
                with open(GMAIL_TOKEN_FILE, "w") as token_file:
                    token_file.write(creds.to_json())
            except Exception:
                return None

    try:
        from googleapiclient.discovery import build
        return build("gmail", "v1", credentials=creds)
    except Exception:
        return None

def read_latest_emails(limit: int = 3):
    """Lê os últimos e-mails da caixa de entrada via Gmail API direta (OAuth2)."""
    try:
        service = get_gmail_service()
        if not service:
            return "Erro: Credenciais da API do Gmail não configuradas (credentials.json ou token.json ausente/inválido)."

        results = service.users().messages().list(userId="me", maxResults=limit, q="in:inbox").execute()
        messages = results.get("messages", [])

        if not messages:
            return "Nenhum e-mail encontrado na caixa de entrada."

        email_list = []
        for msg_info in messages:
            msg = service.users().messages().get(userId="me", id=msg_info["id"], format="full").execute()
            payload = msg.get("payload", {})
            headers = payload.get("headers", [])

            subject = "Sem assunto"
            from_email = "Desconhecido"
            for header in headers:
                name = header.get("name", "").lower()
                if name == "subject":
                    subject = header.get("value", "Sem assunto")
                elif name == "from":
                    from_email = header.get("value", "Desconhecido")

            snippet = msg.get("snippet", "")
            if snippet:
                email_list.append(f"- De: {from_email} | Assunto: {subject} | Trecho: {snippet}")
            else:
                email_list.append(f"- De: {from_email} | Assunto: {subject}")

        return "\n".join(email_list)
    except Exception as e:
        return f"Erro ao ler e-mails via Gmail API: {e}"

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

def _extract_json_objects(text: str):
    """Extrai partes do texto que são JSONs de objetos válidos (lidando com chaves aninhadas)."""
    objs = []
    stack = 0
    start = -1
    in_string = False
    escape = False

    for i, char in enumerate(text):
        if char == '"' and not escape:
            in_string = not in_string
        elif char == '\\' and in_string:
            escape = not escape
            continue

        if not in_string:
            if char == '{':
                if stack == 0:
                    start = i
                stack += 1
            elif char == '}':
                if stack > 0:
                    stack -= 1
                    if stack == 0 and start != -1:
                        objs.append((start, i + 1, text[start:i + 1]))
                        start = -1

        escape = False

    return objs

def extract_tool_calls_from_text(content: str):
    """
    Detecta e extrai chamadas de ferramentas vazadas em texto corrido (ex: 'R: ... C: {"name": ...}').
    Retorna uma tupla (tool_calls, cleaned_content):
    - tool_calls: lista de dicts no formato Ollama [{'function': {'name': ..., 'arguments': ...}}]
    - cleaned_content: o texto sem as chamadas de ferramenta vazadas
    """
    if not content:
        return [], content

    extracted_calls = []
    cleaned_content = content

    json_blocks = _extract_json_objects(content)
    for start_idx, end_idx, json_str in json_blocks:
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                fn_name = parsed.get("name") or parsed.get("function")
                if fn_name and fn_name in TOOL_MAP:
                    fn_args = parsed.get("arguments") or parsed.get("parameters") or parsed.get("args") or {}
                    if isinstance(fn_args, str):
                        try:
                            fn_args = json.loads(fn_args)
                        except Exception:
                            fn_args = {}
                    extracted_calls.append({"function": {"name": fn_name, "arguments": fn_args}})

                    prefix_match = re.search(r'C:\s*$', content[:start_idx])
                    remove_start = prefix_match.start() if prefix_match else start_idx
                    cleaned_content = cleaned_content.replace(content[remove_start:end_idx], "").strip()
        except Exception:
            pass

    cleaned_content = re.sub(r'^R:\s*', '', cleaned_content).strip()
    return extracted_calls, cleaned_content

def is_whatsapp_action_request(user_text: str, history: list = None) -> bool:
    """
    Verifica se o usuário pediu para enviar mensagem via WhatsApp,
    analisando o turno atual e o histórico recente da conversa.
    """
    texts = [user_text] if user_text else []
    if history:
        for msg in reversed(history):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if content and content not in texts:
                    texts.append(content)
            if len(texts) >= 4:
                break

    combined_text = " ".join(texts).lower()
    wa_keywords = ["whatsapp", "zap", "zapzap", "mensagem", "msg", "wa", "contato"]
    action_verbs = ["envia", "enviar", "manda", "mandar", "mande", "diz", "dizer", "diga", "escreve", "escrever", "notifica", "notificar", "fala", "falar", "transmite", "transmitir"]

    has_wa_keyword = any(re.search(r"\b" + re.escape(w) + r"\b", combined_text) for w in wa_keywords)
    has_action_verb = any(re.search(r"\b" + re.escape(v) + r"\b", combined_text) for v in action_verbs)

    return has_wa_keyword and has_action_verb

def is_hallucinated_send_claim(reply_text: str) -> bool:
    """Verifica se a resposta afirma ter enviado a mensagem sem ter rodado a ferramenta."""
    if not reply_text:
        return False
    text = reply_text.lower()
    claim_keywords = [
        "enviei", "enviada", "mandei", "enviando", "disparei", "encaminhei",
        "mensagem enviada", "já mandei", "pronto, mandei", "enviei a mensagem",
        "mandei a mensagem", "enviado com sucesso", "mensagem foi enviada",
        "enviei o whatsapp", "mandei o whatsapp", "mandei no zap", "enviei no zap",
        "transmiti", "mandei pra ele", "mandei para ele", "enviei para ele"
    ]
    return any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in claim_keywords)

def execute_fallback_whatsapp_send(user_text: str, history: list = None) -> str:
    """
    Extrai contato e mensagem analisando o turno atual e mensagens anteriores no histórico.
    """
    contacts = load_contacts()
    target_contact = None
    target_number = None

    user_msgs = [user_text] if user_text else []
    if history:
        for msg in reversed(history):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if content and content not in user_msgs:
                    user_msgs.append(content)

    full_context_text = " ".join(user_msgs)

    for name, info in contacts.items():
        if name.lower() in full_context_text.lower():
            target_contact = name
            target_number = info.get("number")
            break

    if not target_contact:
        num_match = re.search(r'\b\d{10,13}\b', full_context_text)
        if num_match:
            target_number = num_match.group(0)
            target_contact = target_number

    if not target_contact and not target_number:
        return "Senhor, você pediu para enviar uma mensagem no WhatsApp, mas não identifiquei o contato ou número de destino."

    msg_text = None
    for um in user_msgs:
        msg_match = re.search(r'(?:dizendo|mensagem|texto|diga|com o texto|que)\s+["\']?([^"\']+)["\']?', um, re.IGNORECASE)
        if msg_match:
            msg_text = msg_match.group(1).strip()
            break

    if not msg_text:
        first_turn = user_msgs[0] if user_msgs else ""
        msg_text = first_turn.strip() if first_turn and not any(w in first_turn.lower() for w in ["whatsapp", "zap"]) else "Olá! Esta é uma mensagem do assistente Jarvis."

    recipient = target_number or target_contact
    print(f"🛠️ [Anti-Hallucination Multi-Turn JARVIS] Executando envio real de WhatsApp para '{recipient}' com mensagem '{msg_text}'")
    return send_whatsapp_message(recipient, msg_text)

def update_knowledge(file_name: str, key: str = "", value: str = "", action: str = "update"):
    """
    Atualiza ou adiciona informações nos arquivos de conhecimento do sistema (ex: rotina, perfil, preferencias, dispositivos, contacts).
    Ações disponíveis: 'add', 'update' (ou 'set'), 'delete'.
    """
    try:
        file_name = file_name.strip()
        knowledge_dir = os.path.join(os.path.dirname(__file__), "knowledge")

        if file_name.lower() in ["contacts", "contacts.json"]:
            target_file = os.path.join(os.path.dirname(__file__), "contacts.json")
        else:
            if not file_name.endswith((".yaml", ".yml", ".json")):
                file_name_yaml = f"{file_name}.yaml"
            else:
                file_name_yaml = file_name
            target_file = os.path.join(knowledge_dir, os.path.basename(file_name_yaml))

        abs_target = os.path.abspath(target_file)
        abs_knowledge = os.path.abspath(knowledge_dir)
        abs_contacts = os.path.abspath(os.path.join(os.path.dirname(__file__), "contacts.json"))

        if not (abs_target.startswith(abs_knowledge) or abs_target == abs_contacts):
            return "Erro: Acesso não permitido a este arquivo."

        is_json = abs_target.endswith(".json")
        data = {}

        if os.path.exists(abs_target):
            try:
                with open(abs_target, "r", encoding="utf-8") as f:
                    if is_json:
                        data = json.load(f) or {}
                    else:
                        data = yaml.safe_load(f) or {}
            except Exception as e:
                return f"Erro ao ler arquivo {os.path.basename(abs_target)}: {e}"

        if not isinstance(data, dict):
            data = {}

        parsed_value = value
        if isinstance(value, str):
            val_lower = value.strip().lower()
            if val_lower == "true":
                parsed_value = True
            elif val_lower == "false":
                parsed_value = False
            else:
                try:
                    if (value.strip().startswith("{") and value.strip().endswith("}")) or (value.strip().startswith("[") and value.strip().endswith("]")):
                        parsed_value = json.loads(value)
                except Exception:
                    pass

        action = (action or "update").lower()
        keys = [k for k in key.split(".") if k] if key else []

        if not keys:
            if action in ["update", "set"] and isinstance(parsed_value, dict):
                data.update(parsed_value)
            else:
                return "Erro: Nenhuma chave especificada para alteração."
        else:
            curr = data
            for k in keys[:-1]:
                if k not in curr or not isinstance(curr[k], dict):
                    curr[k] = {}
                curr = curr[k]

            last_key = keys[-1]

            if action == "add":
                if last_key not in curr or curr[last_key] is None:
                    curr[last_key] = [parsed_value]
                elif isinstance(curr[last_key], list):
                    if parsed_value not in curr[last_key]:
                        curr[last_key].append(parsed_value)
                elif isinstance(curr[last_key], dict) and isinstance(parsed_value, dict):
                    curr[last_key].update(parsed_value)
                else:
                    if curr[last_key] != parsed_value:
                        curr[last_key] = [curr[last_key], parsed_value]
            elif action in ["update", "set"]:
                curr[last_key] = parsed_value
            elif action in ["delete", "remove"]:
                if last_key in curr:
                    if isinstance(curr[last_key], list) and parsed_value and parsed_value != "":
                        if parsed_value in curr[last_key]:
                            curr[last_key].remove(parsed_value)
                        else:
                            return f"Item '{parsed_value}' não encontrado na lista '{key}' em {os.path.basename(abs_target)}."
                    else:
                        del curr[last_key]
                else:
                    return f"Chave '{key}' não encontrada no arquivo {os.path.basename(abs_target)}."

        os.makedirs(os.path.dirname(abs_target), exist_ok=True)
        with open(abs_target, "w", encoding="utf-8") as f:
            if is_json:
                json.dump(data, f, ensure_ascii=False, indent=4)
            else:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)

        return f"Conhecimento '{os.path.basename(abs_target)}' atualizado com sucesso! Chave: '{key}'."
    except Exception as e:
        return f"Erro ao atualizar conhecimento: {e}"

def web_search(query: str, max_results: int = 5) -> str:
    """Pesquisa informações na internet usando DuckDuckGo sem necessidade de API key."""
    if not query or not str(query).strip():
        return "Erro: A consulta de pesquisa (query) não pode estar vazia."

    query_str = str(query).strip()
    try:
        max_res = int(max_results)
    except (ValueError, TypeError):
        max_res = 5

    max_res = max(1, min(max_res, 15))
    results = []

    # Estratégia 1: Tentar a biblioteca duckduckgo_search se instalada
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            ddg_results = list(ddgs.text(query_str, max_results=max_res))
            for item in ddg_results:
                title = str(item.get("title", "")).strip()
                snippet = str(item.get("body", "")).strip()
                url = str(item.get("href", "")).strip()
                if title and url:
                    results.append({"title": title, "snippet": snippet, "url": url})
    except Exception:
        pass

    # Estratégia 2: Fallback via HTTP request no DuckDuckGo HTML
    if not results:
        try:
            url = "https://html.duckduckgo.com/html/"
            data = urllib.parse.urlencode({"q": query_str}).encode("utf-8")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw_html = resp.read().decode("utf-8", errors="ignore")

            blocks = raw_html.split("web-result")
            for block in blocks[1:]:
                if "result--ad" in block or "duckduckgo.com/y.js" in block:
                    continue
                title_match = re.search(r'class="result__a"[^">]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.DOTALL)
                snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)

                if title_match:
                    href = title_match.group(1)
                    if "duckduckgo.com/y.js" in href:
                        continue
                    url_parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg")
                    actual_url = url_parsed[0] if url_parsed else href
                    if actual_url.startswith("//"):
                        actual_url = "https:" + actual_url
                    elif actual_url.startswith("/"):
                        actual_url = "https://duckduckgo.com" + actual_url

                    title = html.unescape(re.sub(r"<[^>]+>", "", title_match.group(2))).strip()
                    snippet_raw = snippet_match.group(1) if snippet_match else ""
                    snippet = html.unescape(re.sub(r"<[^>]+>", "", snippet_raw)).strip()

                    if title and actual_url:
                        results.append({"title": title, "snippet": snippet, "url": actual_url})
                    if len(results) >= max_res:
                        break
        except Exception as e:
            if not results:
                return f"Erro ao realizar busca web para '{query_str}': {e}"

    if not results:
        return f"Nenhum resultado encontrado na web para: '{query_str}'."

    output_lines = [f"Resultados da pesquisa na web para '{query_str}':\n"]
    for i, res in enumerate(results[:max_res], 1):
        output_lines.append(f"[{i}] {res['title']}")
        if res['snippet']:
            output_lines.append(f"    Resumo: {res['snippet']}")
        output_lines.append(f"    URL: {res['url']}\n")

    return "\n".join(output_lines).strip()

def search_products(query: str, max_results: int = 5) -> str:
    """Pesquisa produtos, ofertas, especificações e comparativos de preços para compra na internet."""
    if not query or not str(query).strip():
        return "Erro: O termo de pesquisa do produto não pode estar vazio."
    query_clean = str(query).strip()
    search_term = f"{query_clean} comprar preço oferta loja"
    search_res = web_search(query=search_term, max_results=max_results)
    if "Nenhum resultado" in search_res or "Erro ao realizar" in search_res:
        search_res = web_search(query=query_clean, max_results=max_results)
    return f"Pesquisa de produtos e ofertas para '{query_clean}':\n\n{search_res}"

def read_context_buffer() -> str:
    """Lê o buffer de contexto histórico salvo em arquivo Markdown (context_buffer.md)."""
    try:
        import context_buffer
        return context_buffer.get_context_buffer()
    except Exception as e:
        return f"Erro ao ler o buffer de contexto em disco: {e}"

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
            "name": "add_contact",
            "description": "Adiciona/salva um novo contato com nome e telefone na agenda do Jarvis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nome do contato (ex: 'Mãe', 'Pedro', 'Trabalho')"},
                    "phone_number": {"type": "string", "description": "Número de telefone com DDD (ex: '5521999999999')"}
                },
                "required": ["name", "phone_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_whatsapp_message",
            "description": "Envia mensagem no WhatsApp por nome de contato (ex: 'Mãe', 'Pedro') ou por número de telefone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_or_phone": {"type": "string", "description": "Nome do contato (ex: 'Mãe') ou número de telefone com DDD"},
                    "message": {"type": "string", "description": "Texto da mensagem a ser enviada"}
                },
                "required": ["contact_or_phone", "message"]
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
            "description": "Envia um e-mail para um destinatário (se não especificado destinatário, envia para o próprio e-mail do usuário).",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_email": {"type": "string", "description": "E-mail do destinatário (opcional, padrão e-mail do Senhor)"},
                    "subject": {"type": "string", "description": "Assunto do e-mail"},
                    "body": {"type": "string", "description": "Conteúdo do e-mail"}
                },
                "required": ["body"]
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
,
    {
        "type": "function",
        "function": {
            "name": "mark_contact_important",
            "description": "Marca ou desmarca um contato da agenda como VIP / Importante para monitoramento de mensagens.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nome do contato (ex: Pedro, Mãe)"},
                    "is_important": {"type": "boolean", "description": "True para marcar como importante/VIP, False para desmarcar"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_whatsapp_messages",
            "description": "Abre ou foca o WhatsApp Web no navegador para leitura na tela pelo Senhor. ATENÇÃO: Esta ferramenta apenas abre/foca a janela na tela, ela NÃO lê nem retorna o conteúdo textual das mensagens.",
            "parameters": {
                "type": "object",
                "properties": {
                    "only_important": {"type": "boolean", "description": "Filtrar apenas mensagens de contatos VIP/importantes (padrão true)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_knowledge",
            "description": "Atualiza ou adiciona informações nos arquivos de conhecimento do sistema (ex: rotina, perfil, preferencias, dispositivos, contacts).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_name": {
                        "type": "string",
                        "description": "Nome do arquivo de conhecimento a editar (ex: rotina.yaml, perfil.yaml, preferencias.yaml, dispositivos.yaml, contacts.json)"
                    },
                    "key": {
                        "type": "string",
                        "description": "Chave ou caminho da propriedade a ser alterada/adicionada (ex: 'regras', 'horarios.noite', 'tom_resposta', 'Pedro')"
                    },
                    "value": {
                        "type": "string",
                        "description": "Valor a ser salvo ou adicionado (pode ser texto, número, booleano ou JSON)"
                    },
                    "action": {
                        "type": "string",
                        "description": "Ação a executar: 'add' (para adicionar a listas/dicts), 'update' ou 'set' (para sobrescrever), ou 'delete' (para remover)",
                        "enum": ["add", "update", "set", "delete"]
                    }
                },
                "required": ["file_name", "key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_calendar_events",
            "description": "Lista os próximos compromissos e eventos agendados no Google Agenda (Google Calendar).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Número máximo de eventos a listar (padrão 5)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Cria um novo compromisso ou evento no Google Agenda (Google Calendar).",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Título/resumo do evento (ex: 'Reunião com Pedro', 'Consulta médica')"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Data e hora de início (ex: '15:00', 'amanhã 10:30', '2026-09-05 14:00')"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Data e hora de término (opcional, se não informado terá duração de 1 hora)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Descrição detalhada do evento (opcional)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Localização ou link do evento (opcional)"
                    }
                },
                "required": ["summary", "start_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Pesquisa informações atuais na internet usando o mecanismo de busca DuckDuckGo e retorna os principais resultados (título, resumo e URL).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Termo ou frase de pesquisa para buscar na internet (ex: 'últimas notícias sobre IA', 'cotação do dólar hoje')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Número máximo de resultados a retornar (padrão 5, máximo recomendado 10)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Pesquisa produtos, ofertas, preços e especificações técnicas em lojas online para comparar e recomendar opções de compra.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Nome do produto ou especificação para buscar ofertas (ex: 'notebook i7 16gb ram', 'fone bluetooth sony')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Número máximo de ofertas/produtos a retornar (padrão 5)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_context_buffer",
            "description": "Lê o arquivo Markdown de buffer de contexto (context_buffer.md) com o histórico recente arquivado em disco.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }]

TOOL_MAP = {
    "get_time": lambda **kwargs: get_time(),
    "get_system_info": lambda **kwargs: get_system_info(),
    "open_app": lambda **kwargs: open_app(kwargs.get("app_name", "")),
    "open_url": lambda **kwargs: open_url(kwargs.get("url", "")),
    "play_youtube": lambda **kwargs: play_youtube(kwargs.get("query", "")),
    "add_contact": lambda **kwargs: add_contact(kwargs.get("name", ""), kwargs.get("phone_number", "")),
    "send_whatsapp_message": lambda **kwargs: send_whatsapp_message(kwargs.get("contact_or_phone", ""), kwargs.get("message", "")),
    "list_tailscale_devices": lambda **kwargs: list_tailscale_devices(),
    "run_remote_command": lambda **kwargs: run_remote_command(kwargs.get("target", ""), kwargs.get("cmd", ""), kwargs.get("user", "rossini")),
    "fetch_remote_file": lambda **kwargs: fetch_remote_file(kwargs.get("target", ""), kwargs.get("remote_file_path", ""), kwargs.get("local_destination", "/tmp/"), kwargs.get("user", "rossini")),
    "get_weather": lambda **kwargs: get_weather(kwargs.get("city", "")),
    "read_latest_emails": lambda **kwargs: read_latest_emails(int(kwargs.get("limit", 3))),
    "send_email": lambda **kwargs: send_email(kwargs.get("to_email", ""), kwargs.get("subject", ""), kwargs.get("body", "")),
    "run_command": lambda **kwargs: run_command(kwargs.get("cmd", "")),
    "trigger_n8n_workflow": lambda **kwargs: trigger_n8n_workflow(kwargs.get("path", "")),
    "mark_contact_important": lambda **kwargs: mark_contact_important(kwargs.get("name", ""), kwargs.get("is_important", True)),
    "check_whatsapp_messages": lambda **kwargs: check_whatsapp_messages(kwargs.get("only_important", True)),
    "morning_briefing": lambda **kwargs: generate_morning_briefing(),
    "update_knowledge": lambda **kwargs: update_knowledge(kwargs.get("file_name", ""), kwargs.get("key", ""), kwargs.get("value", ""), kwargs.get("action", "update")),
    "list_calendar_events": lambda **kwargs: list_calendar_events(int(kwargs.get("limit", 5))),
    "create_calendar_event": lambda **kwargs: create_calendar_event(
        kwargs.get("summary", ""),
        kwargs.get("start_time", ""),
        kwargs.get("end_time"),
        kwargs.get("description", ""),
        kwargs.get("location", "")
    ),
    "web_search": lambda **kwargs: web_search(
        kwargs.get("query", ""),
        int(kwargs.get("max_results", 5))
    ),
    "search_products": lambda **kwargs: search_products(
        kwargs.get("query", ""),
        int(kwargs.get("max_results", 5))
    ),
    "read_context_buffer": lambda **kwargs: read_context_buffer()
}
