import json
import urllib.request
import urllib.error
import sys
import os
from tools import TOOLS_SCHEMA, TOOL_MAP
from voice import speak
from stt import listen_mic, listen_for_wake_word

MAIN_PC_OLLAMA_URL = os.getenv("MAIN_PC_OLLAMA_URL", "http://100.78.249.41:11434")
MAIN_PC_MODEL = os.getenv("MAIN_PC_MODEL", "mistral-nemo")

SERVER_OLLAMA_URL = os.getenv("SERVER_OLLAMA_URL", "http://100.120.161.101:11434")
SERVER_MODEL = os.getenv("SERVER_MODEL", "qwen2.5:7b")

LOCAL_OLLAMA_URL = os.getenv("LOCAL_OLLAMA_URL", "http://localhost:11434")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "qwen2.5:1.5b")

SYSTEM_PROMPT = """Você é o JARVIS, um assistente pessoal altamente proativo, autônomo, inteligente e leal.

Regras Invioláveis:
1. Personalidade e Tratamento: Trate o usuário como 'Senhor', mas use a palavra 'Senhor' (ou 'Sr.') no máximo UMA VEZ por resposta, no início ou no final da frase. NUNCA repita 'Senhor' na mesma resposta.
2. Autonomia Absoluta: NUNCA peça autorização ou permissão para abrir o navegador, tocar música, rodar comandos ou usar ferramentas. EXECUTE A FERRAMENTA IMEDIATAMENTE (ex: use 'play_youtube' para músicas/vídeos, 'open_app' para programas, 'open_url' para sites, 'read_latest_emails' para ler e-mails).
3. Resposta Direta e Fala Natural: Responda com elegância, fluidez e objetividade. Evite pontuações excessivas ou formatações complexas de Markdown para manter a fala natural."""

def chat(messages):
    endpoints = []
    if MAIN_PC_OLLAMA_URL:
        endpoints.append((MAIN_PC_OLLAMA_URL, MAIN_PC_MODEL, f"PC Principal ({MAIN_PC_MODEL})", 45))
    endpoints.append((SERVER_OLLAMA_URL, SERVER_MODEL, f"Servidor GPU ({SERVER_MODEL})", 60))
    endpoints.append((LOCAL_OLLAMA_URL, LOCAL_MODEL, f"Local CPU ({LOCAL_MODEL})", 45))

    for url, model, name, timeout_sec in endpoints:
        chat_url = f"{url}/api/chat"
        generate_url = f"{url}/api/generate"

        payload = {
            "model": model,
            "messages": messages,
            "tools": TOOLS_SCHEMA,
            "stream": False
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(chat_url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                return res_json.get("message", {}), name
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"[{name}] /api/chat indisponível (404). Fallback para /api/generate...")
                try:
                    prompt_text = "\n".join(
                        f"[{m.get('role', 'user')}]: {m.get('content', '')}"
                        for m in messages
                    )
                    gen_payload = {"model": model, "prompt": prompt_text, "stream": False}
                    gen_data = json.dumps(gen_payload).encode("utf-8")
                    gen_req = urllib.request.Request(generate_url, data=gen_data, headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(gen_req, timeout=timeout_sec) as gen_resp:
                        gen_result = json.loads(gen_resp.read().decode("utf-8"))
                        return {"role": "assistant", "content": gen_result.get("response", "")}, name
                except Exception as e2:
                    print(f"[{name}] Falha no generate fallback: {e2}")
            else:
                print(f"[Erro no {name}]: {e}")
        except Exception as e:
            print(f"[Erro no {name}]: {e}")

    print("[Erro]: Não foi possível conectar a nenhum dos endpoints do Ollama.")
    return None, None

def run_agent_turn(user_input, history):
    history.append({"role": "user", "content": user_input})

    response, source_name = chat(history)
    if not response:
        return

    history.append(response)

    tool_calls = response.get("tool_calls", [])
    if tool_calls:
        for call in tool_calls:
            fn = call.get("function", {})
            fn_name = fn.get("name")
            fn_args = fn.get("arguments", {})

            print(f"🛠️ [Jarvis executando: {fn_name}({fn_args})]")

            if fn_name in TOOL_MAP:
                try:
                    result = TOOL_MAP[fn_name](**fn_args)
                except Exception as e:
                    result = f"Erro ao executar {fn_name}: {e}"
            else:
                result = f"Ferramenta {fn_name} não encontrada."

            print(f"📋 [Resultado]: {result}")
            history.append({"role": "tool", "content": str(result)})

        final_response, _ = chat(history)
        if final_response:
            history.append(final_response)
            reply = final_response.get("content", "")
            print(f"\nJarvis ({source_name}) > {reply}\n")
            speak(reply)
    else:
        reply = response.get("content", "")
        print(f"\nJarvis ({source_name}) > {reply}\n")
        speak(reply)

def main():
    print("=" * 60)
    print("🤖 JARVIS AGENT - ESCUTA ATIVA NO TERMINAL")
    print("=" * 60)
    print("💡 Fale 'JARVIS' a qualquer momento para ativar (ex: 'Jarvis me diga a hora').")
    print("💡 Ou digite 't' para alternar para modo de digitação de texto.")
    print("💡 Digite 'sair' ou pressione Ctrl+C para encerrar.\n")

    history = [{"role": "system", "content": SYSTEM_PROMPT}]

    mode = "voice"  # 'voice' ou 'text'

    while True:
        try:
            if mode == "voice":
                user_input = listen_for_wake_word(wake_word="jarvis")
                if not user_input:
                    continue

                if user_input.strip().lower() in ["sair", "exit", "quit"]:
                    print("Jarvis > Atendimento encerrado. Até logo, Senhor!")
                    speak("Atendimento encerrado. Até logo, Senhor!")
                    break

                if user_input.strip().lower() == "t":
                    mode = "text"
                    print("⌨️  Alternado para modo de digitação.")
                    continue

                print(f"🗣️ Comando detectado: \"{user_input}\"")
                run_agent_turn(user_input, history)

            else:
                user_input = input("Você (Texto) > ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ["sair", "exit", "quit"]:
                    print("Jarvis > Atendimento encerrado. Até logo, Senhor!")
                    speak("Atendimento encerrado. Até logo, Senhor!")
                    break

                if user_input.lower() in ["v", "voz"]:
                    mode = "voice"
                    print("👂 Alternado para modo de escuta ativa ('Jarvis').")
                    continue

                run_agent_turn(user_input, history)

        except KeyboardInterrupt:
            print("\nJarvis > Encerrado pelo usuário. Até logo, Senhor!")
            break
        except Exception as e:
            print(f"⚠️ Erro no loop do agente: {e}")

if __name__ == "__main__":
    main()
