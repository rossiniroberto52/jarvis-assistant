import os
import json
import requests
import msal

# Client ID público oficial da CLI Microsoft Graph / PowerShell
CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "14d82eec-204b-4c2f-b7e8-296a70dab67e")
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["User.Read", "ChatMessage.Send", "Chat.ReadWrite", "Team.ReadBasic.All"]

TOKEN_CACHE_FILE = os.path.join(os.path.dirname(__file__), "teams_token_cache.json")

def get_msal_app():
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_FILE):
        try:
            with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                cache.deserialize(f.read())
        except Exception:
            pass

    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache
    )
    return app, cache

def save_cache(cache):
    if cache.has_state_changed:
        with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(cache.serialize())

def get_access_token():
    """Obtém ou renova o token de acesso seguro via MSAL."""
    app, cache = get_msal_app()
    accounts = app.get_accounts()

    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            save_cache(cache)
            return result["access_token"], None

    # Iniciar Device Code Flow se não houver token válido
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        return None, f"Erro ao iniciar autenticação: {flow.get('error_description', 'Falha no device flow')}"

    msg = f"🔐 Conexão Segura Microsoft Teams:\n1. Acesse: {flow['verification_uri']}\n2. Digite o código: {flow['user_code']}\n3. Faça login com sua conta institucional."
    print(f"\n{msg}\n")

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        save_cache(cache)
        return result["access_token"], None
    else:
        return None, result.get("error_description", "Autenticação não concluída.")

def list_teams_chats():
    """Lista as conversas/chats recentes do Microsoft Teams."""
    token, err = get_access_token()
    if err:
        return err

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        res = requests.get("https://graph.microsoft.com/v1.0/me/chats", headers=headers, timeout=15)
        if res.status_code == 200:
            chats = res.json().get("value", [])
            if not chats:
                return "Nenhum chat recente encontrado no seu Microsoft Teams."
            summary = []
            for c in chats[:5]:
                topic = c.get("topic") or c.get("chatType")
                summary.append(f"- Chat ID: {c.get('id')} | Tipo/Tópico: {topic}")
            return "\n".join(summary)
        else:
            return f"Erro ao buscar chats no Teams ({res.status_code}): {res.text}"
    except Exception as e:
        return f"Erro na requisição ao Teams: {e}"

def send_teams_chat_message(chat_id: str, message: str):
    """Envia uma mensagem direta para um chat do Microsoft Teams."""
    token, err = get_access_token()
    if err:
        return err

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"body": {"content": message}}
    try:
        url = f"https://graph.microsoft.com/v1.0/me/chats/{chat_id}/messages"
        res = requests.post(url, headers=headers, json=body, timeout=15)
        if res.status_code in [200, 201]:
            return "Mensagem enviada com sucesso no Microsoft Teams, Senhor!"
        else:
            return f"Erro ao enviar mensagem no Teams ({res.status_code}): {res.text}"
    except Exception as e:
        return f"Erro ao enviar mensagem no Teams: {e}"
