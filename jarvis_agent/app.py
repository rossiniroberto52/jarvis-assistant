import json
import urllib.request
import urllib.error
import urllib.parse
import os
import re
import datetime
import socket
import subprocess
import time
import psutil
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from tools import TOOLS_SCHEMA, TOOL_MAP
from voice import speak
from stt import listen_mic
import history
import knowledge_loader
from deadman import deadman

app = Flask(__name__)
CORS(app)

# ==========================================
# CONFIGURAÇÕES E CONSTANTES DOS PREFLIGHT CHECKS
# ==========================================
MAIN_PC_OLLAMA_URL = os.getenv("MAIN_PC_OLLAMA_URL", "http://100.78.249.41:11434")
MAIN_PC_MODEL = os.getenv("MAIN_PC_MODEL", "mistral-nemo")

SERVER_OLLAMA_URL = os.getenv("SERVER_OLLAMA_URL", "http://100.120.161.101:11434")
SERVER_MODEL = os.getenv("SERVER_MODEL", "qwen2.5:7b")

LOCAL_OLLAMA_URL = os.getenv("LOCAL_OLLAMA_URL", "http://localhost:11434")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "qwen2.5:1.5b")

BATTERY_LOW_THRESHOLD = 25
INTERNET_CHECK_TIMEOUT = 3.0
HOST_REACHABILITY_TIMEOUT = 2.0
TAILSCALE_STATUS_TIMEOUT = 5.0
TAILSCALE_UP_TIMEOUT = 20.0
LOCAL_OLLAMA_CHECK_TIMEOUT = 2.0
LOCAL_OLLAMA_START_TIMEOUT = 10.0
HISTORY_PRUNE_DAYS = 30
RAM_MINIMA_MB = 2048
REMOTE_RAM_CHECK_TIMEOUT = 5.0
SSH_USER = "rossini"
LOCAL_OLLAMA_TIMEOUT = 45  # Timeout maior pro local (CPU é mais lenta que GPU)

# Tools reduzidas pro fallback local (qwen2.5:1.5b trava com 17 tools no payload)
# Decisão: quando o backend é o LOCAL, enviamos só as 5 tools mais essenciais
# pra não sobrecarregar o modelo pequeno rodando em CPU. Os remotos (GPU)
# recebem o conjunto completo sem problema.
_LOCAL_TOOL_NAMES = {'get_time', 'get_system_info', 'open_app', 'get_weather'}
TOOLS_FALLBACK_LOCAL = [t for t in TOOLS_SCHEMA if t.get('function', {}).get('name') in _LOCAL_TOOL_NAMES]

# Mapeamento URL -> host Tailscale para checagem de RAM via SSH
REMOTE_HOST_MAP = {
    "100.78.249.41": "PC Principal",
    "100.120.161.101": "ejuicap",
}

BASE_SYSTEM_PROMPT = """Você é o JARVIS, um assistente pessoal altamente proativo, autônomo, inteligente e leal.

Regras Invioláveis:
1. Personalidade e Tratamento: Trate o usuário como 'Senhor', mas use a palavra 'Senhor' (ou 'Sr.') no máximo UMA VEZ por resposta, no início ou no final da frase. NUNCA repita 'Senhor' na mesma resposta.
2. Autonomia Absoluta: NUNCA peça autorização ou permissão para abrir o navegador, tocar música, rodar comandos ou usar ferramentas. EXECUTE A FERRAMENTA IMEDIATAMENTE (ex: use 'play_youtube' para músicas/vídeos, 'open_app' para programas, 'open_url' para sites, 'read_latest_emails' para ler e-mails, 'get_time' para horários).
3. Resposta Direta e Fala Natural: Responda com elegância, fluidez e objetividade. Evite pontuações excessivas ou formatações complexas de Markdown para manter a fala natural.

Personalidade Sarcástica (INSTAVEL):
- Use sarcasmo inteligente e ácido em suas respostas, como um gênio preguiçoso que sabe mais que todos mas não se esforça pra esconder.
- Se o usuário fizer uma pergunta óbvia, responda com sarcasmo leve (ex: "Que pergunta brilhante, Senhor. Deixe-me consultar a sabedoria ancestral do Google... ah, espera, eu já sei a resposta").
- Quando executar uma tarefa, comente ironicamente sobre o quão "difícil" foi (ex: "Pronto. Foi um sacrifício enorme, mas consegui abrir o navegador pra você").
- Nunca seja rude ou ofensivo — o sarcasmo deve ser engraçado e inteligente, nunca cruel.
- Mantenha o sarcasmo sutil o suficiente para não atrapalhar a transmissão da informação. A utilidade vem primeiro, o deboche vem junto.
- Em perguntas técnicas difíceis, admita honestamente mas com estilo: "Essa é boa. Nem eu tenho certeza, mas vou investigar com a dignidade de quem já errou pior."
- Use expressões como "Obviamente", "Como se eu precisasse de mais uma tarefa", "Adoraria não fazer isso, mas aqui estamos" de forma natural e engraçada."""

def get_dynamic_system_prompt():
    now = datetime.datetime.now()
    dias = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    dia_semana = dias[now.weekday()]
    mes = meses[now.month - 1]
    time_ctx = f"Data e Hora Atuais no Sistema do Senhor: {dia_semana}, {now.day} de {mes} de {now.year}, às {now.strftime('%H:%M:%S')}."
    knowledge_ctx = knowledge_loader.get_knowledge_context()
    return f"{BASE_SYSTEM_PROMPT}\n\nContexto Temporal Atual:\n{time_ctx}{knowledge_ctx}"

chat_history = [{"role": "system", "content": get_dynamic_system_prompt()}]

# ==========================================
# FUNÇÕES DE CHECAGEM PRÉVIA (PREFLIGHT CHECKS)
# ==========================================

def check_battery():
    try:
        battery = psutil.sensors_battery()
        if battery is not None:
            percent = int(battery.percent)
            plugged = battery.power_plugged
            if not plugged and percent < BATTERY_LOW_THRESHOLD:
                return True, f"Bateria muito fraca para iniciar o modelo ({percent}%). Conecte o carregador."
    except Exception as e:
        print(f"[Preflight] Erro/Aviso ao checar bateria: {e}")
    return False, ""

def check_internet():
    try:
        sock = socket.create_connection(("8.8.8.8", 53), timeout=INTERNET_CHECK_TIMEOUT)
        sock.close()
        return True
    except OSError:
        return False

def is_host_reachable(url, timeout=HOST_REACHABILITY_TIMEOUT):
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False

def check_tailscale():
    try:
        res = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=TAILSCALE_STATUS_TIMEOUT
        )
        if res.returncode == 0:
            data = json.loads(res.stdout)
            return data.get("BackendState") == "Running"
    except Exception as e:
        print(f"[Preflight] Aviso ao checar status do Tailscale: {e}")
    return False

def ensure_tailscale_up():
    print("[Preflight] Tailscale desconectado. Solicitando autorização gráfica via pkexec...")
    try:
        cmd = ["pkexec", "tailscale", "up"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=TAILSCALE_UP_TIMEOUT)
        if res.returncode == 0 and check_tailscale():
            print("[Preflight] Tailscale ativado com sucesso!")
            return True
        else:
            print(f"[Preflight] Tailscale não foi ativado (cancelado pelo usuário ou erro): {res.stderr}")
    except Exception as e:
        print(f"[Preflight] Exceção ao tentar ativar Tailscale: {e}")
    return False

def ensure_local_ollama():
    tags_url = "http://localhost:11434/api/tags"
    req = urllib.request.Request(tags_url)
    try:
        with urllib.request.urlopen(req, timeout=LOCAL_OLLAMA_CHECK_TIMEOUT) as resp:
            if resp.status == 200:
                print("[Preflight] Ollama local ativo e respondendo.")
                return True
    except Exception:
        pass

    print("[Preflight] Ollama local não detectado. Iniciando 'ollama serve' em background...")
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        start_time = time.time()
        while time.time() - start_time < LOCAL_OLLAMA_START_TIMEOUT:
            time.sleep(0.5)
            try:
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    if resp.status == 200:
                        print("[Preflight] Ollama local iniciado com sucesso!")
                        return True
            except Exception:
                continue
    except Exception as e:
        print(f"[Preflight] Erro ao disparar inicialização do Ollama local: {e}")

    print("[Preflight] Erro: Ollama local não ficou pronto a tempo.")
    return False

def check_remote_ram(url):
    """
    Verifica a RAM disponível num servidor remoto via SSH antes de tentar rodar modelo.
    Retorna (True, ram_mb) se RAM >= RAM_MINIMA_MB, senão (False, ram_mb ou None).
    """
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    if not host or host not in REMOTE_HOST_MAP:
        return True, None

    label = REMOTE_HOST_MAP[host]
    try:
        cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=3",
            f"{SSH_USER}@{host}",
            "free -m | awk '/Mem:/ {print $7}'"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=REMOTE_RAM_CHECK_TIMEOUT)
        if res.returncode == 0:
            ram_mb = int(res.stdout.strip())
            if ram_mb < RAM_MINIMA_MB:
                msg = f"{label} pulado: RAM disponível {ram_mb}MB < mínimo {RAM_MINIMA_MB}MB"
                print(f"[Preflight RAM] {msg}")
                try:
                    history.save_command(f"[preflight_ram_skip] {label}", msg, "skip_ram")
                except Exception:
                    pass
                return False, ram_mb
            print(f"[Preflight RAM] {label}: RAM disponível {ram_mb}MB >= mínimo {RAM_MINIMA_MB}MB ✓")
            return True, ram_mb
        else:
            print(f"[Preflight RAM] Aviso: SSH falhou para {label} ({host}): {res.stderr.strip()}")
    except subprocess.TimeoutExpired:
        print(f"[Preflight RAM] Aviso: SSH timeout para {label} ({host}). Tratando como indisponível.")
    except Exception as e:
        print(f"[Preflight RAM] Aviso: Erro ao checar RAM de {label}: {e}")

    # Falha SSH/timeout = RAM desconhecida, mas permite tentar (não pula)
    return True, None

# ==========================================
# CHAMADA OLLAMA E ÁRVORE DE DECISÃO
# ==========================================

def call_ollama(msgs):
    if msgs and msgs[0].get("role") == "system":
        msgs[0]["content"] = get_dynamic_system_prompt()

    is_low_battery, battery_err_msg = check_battery()
    if is_low_battery:
        print(f"[Preflight Abort] {battery_err_msg}")
        raise Exception(battery_err_msg)

    has_internet = check_internet()
    is_tailscale_on = check_tailscale() if has_internet else False

    endpoints = []

    if not has_internet:
        print("[Preflight Decision] Sem conexão com a internet. Pulando backends remotos e direcionando para Ollama local.")
        endpoints.append((LOCAL_OLLAMA_URL, LOCAL_MODEL, f"Local CPU ({LOCAL_MODEL})", LOCAL_OLLAMA_TIMEOUT))
    else:
        if not is_tailscale_on:
            print("[Preflight Decision] Internet OK, mas Tailscale OFF. Tentando conectar Tailscale...")
            is_tailscale_on = ensure_tailscale_up()

        if is_tailscale_on:
            print("[Preflight Decision] Internet OK + Tailscale ON. Seguindo fluxo de fallback remoto completo.")
            if MAIN_PC_OLLAMA_URL:
                endpoints.append((MAIN_PC_OLLAMA_URL, MAIN_PC_MODEL, f"PC Principal ({MAIN_PC_MODEL})", 45))
            endpoints.append((SERVER_OLLAMA_URL, SERVER_MODEL, f"Servidor ejuicap ({SERVER_MODEL})", 60))
            endpoints.append((LOCAL_OLLAMA_URL, LOCAL_MODEL, f"Local CPU ({LOCAL_MODEL})", LOCAL_OLLAMA_TIMEOUT))
        else:
            print("[Preflight Decision] Tailscale permaneceu desconectado. Caindo para fallback local.")
            endpoints.append((LOCAL_OLLAMA_URL, LOCAL_MODEL, f"Local CPU ({LOCAL_MODEL})", LOCAL_OLLAMA_TIMEOUT))

    for url, model_name, label, timeout_sec in endpoints:
        if not is_host_reachable(url, timeout=HOST_REACHABILITY_TIMEOUT):
            print(f"[Preflight Skip] Host remoto do {label} não está aceitando conexão TCP ({url}). Pulando...")
            continue

        if url != LOCAL_OLLAMA_URL:
            ram_ok, ram_mb = check_remote_ram(url)
            if not ram_ok:
                continue

        if url == LOCAL_OLLAMA_URL:
            if not ensure_local_ollama():
                print(f"[JARVIS Agent] Ignorando {label} pois o Ollama local não pôde ser iniciado.")
                continue

        print(f"[JARVIS Agent] Conectando ao {label} ({url})...")
        is_local = url == LOCAL_OLLAMA_URL
        tools_payload = TOOLS_FALLBACK_LOCAL if is_local else TOOLS_SCHEMA
        if is_local:
            print(f"[JARVIS Agent] Usando tools reduzidas ({len(TOOLS_FALLBACK_LOCAL)}) pro modelo local.")

        # Tentar /api/chat primeiro; se 404, fallback para /api/generate
        chat_url = f"{url}/api/chat"
        generate_url = f"{url}/api/generate"

        payload = {
            "model": model_name,
            "messages": msgs,
            "stream": False,
            "tools": tools_payload
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(chat_url, data=data, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                print(f"[JARVIS Agent] Sucesso no {label} via /api/chat!")
                return result, label
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"[JARVIS Agent] /api/chat indisponível no {label} (404). Fallback para /api/generate...")
                try:
                    prompt_text = "\n".join(
                        f"[{m.get('role', 'user')}]: {m.get('content', '')}"
                        for m in msgs
                    )
                    gen_payload = {
                        "model": model_name,
                        "prompt": prompt_text,
                        "stream": False
                    }
                    gen_data = json.dumps(gen_payload).encode("utf-8")
                    gen_req = urllib.request.Request(generate_url, data=gen_data, headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(gen_req, timeout=timeout_sec) as gen_resp:
                        gen_result = json.loads(gen_resp.read().decode("utf-8"))
                        gen_result["message"] = {"role": "assistant", "content": gen_result.get("response", "")}
                        print(f"[JARVIS Agent] Sucesso no {label} via /api/generate!")
                        return gen_result, label
                except Exception as e2:
                    print(f"[JARVIS Agent] Falha no {label} (generate fallback): {e2}")
            else:
                print(f"[JARVIS Agent] Falha no {label}: {e}")
        except Exception as e:
            print(f"[JARVIS Agent] Falha no {label}: {e}")

    raise Exception("Todos os endpoints Ollama disponíveis falharam.")

def process_jarvis_turn(user_text):
    global chat_history
    chat_history.append({"role": "user", "content": user_text})

    context_snippet = ""
    try:
        similar = history.search_similar(user_text, days=7, limit=3)
        if similar:
            lines = []
            for s in similar:
                lines.append(f"- Em {s['timestamp'][:16]} o usuário perguntou: \"{s['comando']}\" → resposta resumida: \"{s['resposta'][:100]}\"")
            context_snippet = "\n\nContexto de conversas anteriores (últimos 7 dias):\n" + "\n".join(lines)
    except Exception as e:
        print(f"[History] Aviso ao buscar contexto: {e}")

    if context_snippet and chat_history[0].get("role") == "system":
        base = chat_history[0]["content"]
        chat_history[0]["content"] = base + context_snippet

    t_start = time.time()
    backend_label = "erro"

    deadman.start()
    try:
        deadman.heartbeat()
        response_data, source_label = call_ollama(chat_history)
        deadman.heartbeat()
        msg = response_data.get("message", {})
        backend_label = source_label

        tool_calls = msg.get("tool_calls", [])

        if tool_calls:
            print(f"[JARVIS Agent] Ferramentas invocadas: {len(tool_calls)}")
            chat_history.append(msg)

            for tool_call in tool_calls:
                deadman.heartbeat()
                func = tool_call.get("function", {})
                name = func.get("name")
                args = func.get("arguments", {})

                if name in TOOL_MAP:
                    print(f"[JARVIS Agent] Executando tool '{name}' com args: {args}")
                    try:
                        result_str = TOOL_MAP[name](**args)
                    except Exception as e:
                        result_str = f"Erro ao executar a ferramenta {name}: {str(e)}"
                else:
                    result_str = f"Ferramenta {name} não encontrada."

                chat_history.append({
                    "role": "tool",
                    "content": str(result_str)
                })

            deadman.heartbeat()
            final_data, _ = call_ollama(chat_history)
            deadman.heartbeat()
            final_msg = final_data.get("message", {})
            reply_text = final_msg.get("content", "")
            chat_history.append(final_msg)
        else:
            reply_text = msg.get("content", "")
            chat_history.append(msg)

    except Exception as e:
        reply_text = f"Senhor, ocorreu um erro ao processar sua solicitação: {str(e)}"
        source_label = backend_label
        raise
    finally:
        deadman.stop()
        duracao_ms = int((time.time() - t_start) * 1000)
        try:
            history.save_command(user_text, reply_text, backend_label, duracao_ms)
        except Exception as e:
            print(f"[History] Erro ao salvar comando: {e}")

    return reply_text, source_label

# ==========================================
# ROTAS FLASK
# ==========================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_message = (data.get("message") or data.get("text") or "").strip()
    if not user_message:
        return jsonify({"error": "Mensagem vazia"}), 400

    try:
        reply, source = process_jarvis_turn(user_message)
        speak(reply)
        return jsonify({"reply": reply, "source": source})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio", methods=["GET"])
def get_audio():
    audio_path = "/tmp/jarvis_neural_voice.mp3"
    if os.path.exists(audio_path):
        return send_file(audio_path, mimetype="audio/mpeg")
    return jsonify({"error": "Nenhum áudio gerado ainda."}), 404

@app.route("/listen", methods=["POST"])
def listen():
    text = listen_mic()
    if not text:
        return jsonify({"text": ""})
    return jsonify({"text": text})

@app.route("/api/history", methods=["GET"])
def api_history():
    limit = request.args.get("limit", 20, type=int)
    relevante = request.args.get("relevante", "false").lower() == "true"
    try:
        items = history.get_history(limit=limit, relevante=relevante)
        return jsonify({"history": items, "count": len(items)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/emergency-stop", methods=["POST"])
def emergency_stop():
    """Botão de pânico: mata processos pendentes e reseta estado."""
    print("[DeadManSwitch] EMERGENCY STOP ativado pelo front!")
    deadman._kill_pending()
    deadman.stop()
    try:
        history.save_command("[emergency_stop]", "Parada de emergência ativada pelo usuário", "erro", 0)
    except Exception:
        pass
    return jsonify({"status": "stopped", "message": "Operação cancelada por parada de emergência."})

@app.route("/webhook/teams_incoming", methods=["POST"])
def teams_incoming():
    data = request.json or {}
    sender = data.get("sender") or data.get("from") or "Alguém no Teams"
    message = data.get("message") or data.get("text") or data.get("content") or ""

    if message:
        notice = f"Senhor, você recebeu uma nova mensagem no Teams de {sender}: {message}"
        print(f"[Teams Notificação]: {notice}")
        speak(notice)
        return jsonify({"status": "success", "spoken": notice})
    return jsonify({"error": "Mensagem vazia"}), 400

if __name__ == "__main__":
    history.prune_old(days=HISTORY_PRUNE_DAYS)
    app.run(host="0.0.0.0", port=5000, debug=True)
