import os

# Suporte a credenciais locais (gmail_local.py) sem expor senhas no git
try:
    from gmail_local import GMAIL_USER as LOCAL_USER, GMAIL_APP_PASSWORD as LOCAL_PASS
except ImportError:
    LOCAL_USER, LOCAL_PASS = None, None

GMAIL_USER = os.getenv("GMAIL_USER") or LOCAL_USER or "seu_email@gmail.com"
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD") or LOCAL_PASS or ""
