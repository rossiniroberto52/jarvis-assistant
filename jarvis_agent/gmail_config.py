import os

# Configurações do Gmail usando Senha de App (App Password)
# Defina as variáveis de ambiente GMAIL_USER e GMAIL_APP_PASSWORD ou edite localmente sem enviar secrets
GMAIL_USER = os.getenv("GMAIL_USER", "seu_email@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
