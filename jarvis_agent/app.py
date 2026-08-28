import json
import urllib.request
import urllib.error
import os
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from tools import TOOLS_SCHEMA, TOOL_MAP
from voice import speak
from stt import listen_mic

app = Flask(__name__)
CORS(app)

SERVER_OLLAMA_URL = "http://100.120.161.101:11434/api/chat"
SERVER_MODEL = "qwen2.5:7b"

LOCAL_OLLAMA_URL = "http://localhost:11434/api/chat"
LOCAL_MODEL = "qwen2.5:1.5b"

SYSTEM_PROMPT = """Você é o JARVIS, um assistente pessoal altamente proativo, autônomo, inteligente e leal.

Regras Invioláveis:
1. Personalidade e Tratamento: Trate o usuário como 'Senhor', mas use a palavra 'Senhor' (ou 'Sr.') no máximo UMA VEZ por resposta, no início ou no final da frase. NUNCA repita 'Senhor' na mesma resposta.
2. Autonomia Absoluta: NUNCA peça autorização ou permissão para abrir o navegador, tocar música, rodar comandos ou usar ferramentas. EXECUTE A FERRAMENTA IMEDIATAMENTE (ex: use 'play_youtube' para músicas/vídeos, 'open_app' para programas, 'open_url' para sites).
3. Resposta Direta: Responda com elegância e objetividade, informando que a ação já foi executada."""

history = [{"role": "system", "content": SYSTEM_PROMPT}]

def call_ollama(msgs):
    # Testar servidor GPU primeiro, fallback para local
    target_url = SERVER_OLLAMA_URL
    target_model = SERVER_MODEL
    
    payload = {
        "model": target_model,
        "messages": msgs,
        "tools": TOOLS_SCHEMA,
        "stream": False
    }
    data = json.dumps(payload).encode("utf-8")
    
    try:
        req = urllib.request.Request(target_url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json.get("message", {}), f"Servidor GPU ({SERVER_MODEL})"
    except Exception:
        # Fallback para IA local
        try:
            payload["model"] = LOCAL_MODEL
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(LOCAL_OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                return res_json.get("message", {}), f"Local CPU ({LOCAL_MODEL})"
        except Exception as e:
            return {"content": f"Desculpe Senhor, não foi possível conectar às IAs (Servidor ou Local): {e}"}, "Erro"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def api_chat():
    global history
    data = request.get_json() or {}
    user_text = data.get("text", "").strip()
    
    if not user_text:
        return jsonify({"error": "Texto vazio"}), 400
        
    history.append({"role": "user", "content": user_text})
    
    response, source = call_ollama(history)
    if not response:
        return jsonify({"error": "Sem resposta da IA"}), 500
        
    history.append(response)
    
    tool_calls = response.get("tool_calls", [])
    if tool_calls:
        for call in tool_calls:
            fn = call.get("function", {})
            fn_name = fn.get("name")
            fn_args = fn.get("arguments", {})
            
            if fn_name in TOOL_MAP:
                result = TOOL_MAP[fn_name](fn_args)
            else:
                result = f"Ferramenta {fn_name} desconhecida."
                
            history.append({"role": "tool", "content": str(result)})
            
        final_resp, source = call_ollama(history)
        if final_resp:
            history.append(final_resp)
            text_out = final_resp.get("content", "")
            speak(text_out)
            return jsonify({
                "reply": text_out,
                "source": source,
                "tools_used": [c.get("function", {}).get("name") for c in tool_calls]
            })
            
    text_out = response.get("content", "")
    speak(text_out)
    return jsonify({"reply": text_out, "source": source})

@app.route("/api/listen", methods=["POST"])
def api_listen():
    text = listen_mic(prompt="Ouvindo microfone...")
    if text:
        return jsonify({"text": text})
    return jsonify({"text": ""}), 400

@app.route("/api/audio")
def api_audio():
    audio_path = "/tmp/jarvis_neural_voice.mp3"
    if os.path.exists(audio_path):
        return send_file(audio_path, mimetype="audio/mpeg")
    return jsonify({"error": "Nenhum áudio encontrado"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
