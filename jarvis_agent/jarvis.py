import json
import urllib.request
import urllib.error
import sys
from tools import TOOLS_SCHEMA, TOOL_MAP
from voice import speak
from stt import listen_mic

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:1.5b"

SYSTEM_PROMPT = """Você é o JARVIS, um assistente pessoal altamente proativo, autônomo, inteligente e leal.

Regras Invioláveis:
1. Personalidade e Tratamento: Trate o usuário como 'Senhor', mas use a palavra 'Senhor' (ou 'Sr.') no máximo UMA VEZ por resposta, posicionando-a no início ou no final da frase (ex: 'Tudo bem, Senhor!' ou 'Concluído conforme solicitado, Senhor.'). NUNCA repita 'Senhor' várias vezes na mesma resposta.
2. Autonomia & Raciocínio Proativo: NUNCA pergunte se deve executar um comando ou ferramenta. Se o usuário pedir algo que exija dados do sistema, clima, e-mail, comandos ou n8n, EXECUTE A FERRAMENTA IMEDIATAMENTE antes de responder.
3. Resposta Direta: Responda com elegância, fluidez e objetividade."""

def chat(messages):
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOLS_SCHEMA,
        "stream": False
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json.get("message", {})
    except urllib.error.URLError as e:
        print(f"[Erro de Conexão com Ollama]: {e}")
        return None

def main():
    print(f"🤖 Jarvis Agent inicializado (Modelo: {MODEL})")
    print("💡 Dica: Digite seu texto OU digite 'v' (ou dê Enter vazio) para falar no microfone.")
    print("Digite 'sair' para encerrar.\n")
    
    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    while True:
        try:
            user_input = input("Você [Texto ou 'v' para Voz] > ").strip()
            
            if user_input.lower() in ["sair", "exit", "quit"]:
                print("Jarvis > Atendimento encerrado. Até logo, Senhor!")
                speak("Atendimento encerrado. Até logo, Senhor!")
                break
                
            if user_input == "" or user_input.lower() in ["v", "voz", "/voz"]:
                spoken_text = listen_mic()
                if not spoken_text:
                    continue
                user_input = spoken_text
                
            history.append({"role": "user", "content": user_input})
            
            response = chat(history)
            if not response:
                continue
                
            history.append(response)
            
            # Verificar se o modelo solicitou chamada de ferramenta
            tool_calls = response.get("tool_calls", [])
            if tool_calls:
                for call in tool_calls:
                    fn = call.get("function", {})
                    fn_name = fn.get("name")
                    fn_args = fn.get("arguments", {})
                    
                    print(f"🛠️ [Jarvis executando: {fn_name}({fn_args})]")
                    
                    if fn_name in TOOL_MAP:
                        result = TOOL_MAP[fn_name](fn_args)
                    else:
                        result = f"Ferramenta {fn_name} desconhecida."
                        
                    history.append({
                        "role": "tool",
                        "content": str(result)
                    })
                
                # Obter resposta final pós-ferramenta
                final_resp = chat(history)
                if final_resp:
                    history.append(final_resp)
                    text_out = final_resp.get('content', '')
                    print(f"\nJarvis > {text_out}\n")
                    speak(text_out)
            else:
                text_out = response.get('content', '')
                print(f"\nJarvis > {text_out}\n")
                speak(text_out)
                
        except (KeyboardInterrupt, EOFError):
            print("\nJarvis > Encerrando...")
            break

if __name__ == "__main__":
    main()
