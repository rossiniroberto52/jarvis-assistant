import os

# Suporte a credenciais locais (gmail_local.py) sem expor senhas no git
try:
    from gmail_local import (
        GMAIL_USER as LOCAL_USER,
        GMAIL_APP_PASSWORD as LOCAL_PASS,
        GMAIL_CREDENTIALS_FILE as LOCAL_CREDENTIALS_FILE,
        GMAIL_TOKEN_FILE as LOCAL_TOKEN_FILE,
    )
except ImportError:
    LOCAL_USER, LOCAL_PASS = None, None
    LOCAL_CREDENTIALS_FILE, LOCAL_TOKEN_FILE = None, None

GMAIL_USER = os.getenv("GMAIL_USER") or LOCAL_USER or "rossiniroberto52@gmail.com"
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD") or LOCAL_PASS or ""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GMAIL_CREDENTIALS_FILE = (
    os.getenv("GMAIL_CREDENTIALS_FILE")
    or LOCAL_CREDENTIALS_FILE
    or os.path.join(BASE_DIR, "credentials.json")
)
GMAIL_TOKEN_FILE = (
    os.getenv("GMAIL_TOKEN_FILE")
    or LOCAL_TOKEN_FILE
    or os.path.join(BASE_DIR, "token.json")
)
