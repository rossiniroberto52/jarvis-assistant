import subprocess
import threading
import shutil
import asyncio
import os
import re
import edge_tts

# Vozes disponíveis: pt-BR-AntonioNeural, pt-BR-ThalitaMultilingualNeural, pt-BR-FranciscaNeural
VOICE = os.getenv("JARVIS_VOICE", "pt-BR-AntonioNeural")
RATE = os.getenv("JARVIS_VOICE_RATE", "+8%")

# Mapeamento de siglas técnicas para pronúncia fonética precisa em PT-BR
ACRONYMS = {
    r"\bms\b": "milissegundos",
    r"\bMS\b": "milissegundos",
    r"\bGPU\b": "Gê-Pê-U",
    r"\bGPUs\b": "Gê-Pê-Us",
    r"\bCPU\b": "Cê-Pê-U",
    r"\bCPUs\b": "Cê-Pê-Us",
    r"\bVRAM\b": "Vê-Râm",
    r"\bRAM\b": "Râm",
    r"\bAPI\b": "A-Pê-I",
    r"\bAPIs\b": "A-Pê-Is",
    r"\bURL\b": "U-Erre-Ele",
    r"\bURLs\b": "U-Erre-Eles",
    r"\bLLM\b": "Ele-Ele-Eme",
    r"\bLLMs\b": "Ele-Ele-Emes",
    r"\bAI\b": "A-I",
    r"\bIA\b": "I-A",
    r"\bUI\b": "U-I",
    r"\bUX\b": "U-Xis",
    r"\bHTTP\b": "Aga-Tê-Tê-Pê",
    r"\bHTTPS\b": "Aga-Tê-Tê-Pê-Ese",
}

def clean_and_normalize_text(text: str) -> str:
    if not text:
        return ""

    # 1. Remover marcações de Markdown (asteriscos, cerquilhas, crases, etc.)
    text = re.sub(r'[\*\#\`\_\~]', '', text)

    # 2. Converter números acompanhados de ms para milissegundos (ex: 500ms -> 500 milissegundos)
    text = re.sub(r'(\d+)\s*ms\b', r'\1 milissegundos', text, flags=re.IGNORECASE)

    # 3. Substituir siglas técnicas por termos com pronúncia fonética precisa
    for pattern, replacement in ACRONYMS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # 4. Suavizar pausas excessivas de vírgula e múltiplos espaços
    text = re.sub(r'\s*,\s*', ', ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

async def _generate_audio(text: str, output_file: str):
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(output_file)

def speak(text: str):
    """Fala o texto com voz neural ultra-realista otimizada (Edge-TTS)."""
    if not text:
        return

    def _speak_thread():
        clean_text = clean_and_normalize_text(text)
        if not clean_text:
            return

        temp_file = "/tmp/jarvis_neural_voice.mp3"

        try:
            # Gerar voz neural via edge-tts
            asyncio.run(_generate_audio(clean_text, temp_file))

            # Reproduzir áudio
            if shutil.which("paplay"):
                subprocess.run(["paplay", temp_file], stderr=subprocess.DEVNULL)
            elif shutil.which("ffplay"):
                subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", temp_file], stderr=subprocess.DEVNULL)
            elif shutil.which("mpg123"):
                subprocess.run(["mpg123", "-q", temp_file], stderr=subprocess.DEVNULL)
            return
        except Exception as e:
            print(f"[Voz Neural Edge-TTS Erro]: {e}. Usando sintetizador local...")

        # Fallback offline caso esteja sem conexão
        if shutil.which("espeak-ng"):
            subprocess.run(["espeak-ng", "-v", "pt-br", clean_text], stderr=subprocess.DEVNULL)
        elif shutil.which("spd-say"):
            subprocess.run(["spd-say", "-l", "pt", clean_text], stderr=subprocess.DEVNULL)

    threading.Thread(target=_speak_thread, daemon=True).start()
