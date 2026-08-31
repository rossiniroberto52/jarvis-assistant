import yaml
import os

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")

def load_knowledge():
    """Carrega todos os arquivos YAML da pasta knowledge/ e retorna um dict."""
    knowledge = {}
    if not os.path.isdir(KNOWLEDGE_DIR):
        return knowledge

    for filename in os.listdir(KNOWLEDGE_DIR):
        if filename.endswith((".yaml", ".yml")):
            filepath = os.path.join(KNOWLEDGE_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    key = filename.replace(".yaml", "").replace(".yml", "")
                    knowledge[key] = yaml.safe_load(f)
            except Exception as e:
                print(f"[Knowledge] Erro ao carregar {filename}: {e}")

    return knowledge

def get_knowledge_context():
    """Retorna uma string formatada com o conhecimento do usuário pro prompt do sistema."""
    knowledge = load_knowledge()
    if not knowledge:
        return ""

    parts = []

    if "perfil" in knowledge:
        p = knowledge["perfil"]
        parts.append(f"Usuário: {p.get('nome', 'N/A')} (apelido: {p.get('apelido', 'N/A')})")
        parts.append(f"Fuso horário: {p.get('fuso_horario', 'N/A')}")
        parts.append(f"Idioma: {p.get('idioma', 'N/A')}")

    if "preferencias" in knowledge:
        pr = knowledge["preferencias"]
        parts.append(f"Tom de resposta: {pr.get('tom_resposta', 'informal')}")
        if pr.get("mostrar_hora"):
            parts.append("Sempre incluir horário quando relevante.")

    if "rotina" in knowledge:
        r = knowledge["rotina"]
        if "regras" in r:
            parts.append("Regras do usuário:")
            for rule in r["regras"]:
                parts.append(f"  - {rule}")

    if parts:
        return "\n\nConhecimento do Usuário:\n" + "\n".join(parts)
    return ""
