import subprocess
import threading
import shutil
import asyncio
import os
import edge_tts

# Voz realista estilo assistente masculino refinado em Português do Brasil
VOICE = "pt-BR-AntonioNeural"

async def _generate_audio(text: str, output_file: str):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)

def speak(text: str):
    """Fala o texto com voz neural ultra-realista (edge-tts / Antonio Neural)."""
    if not text:
        return
        
    def _speak_thread():
        clean_text = text.replace("*", "").replace("#", "").replace("`", "").replace("\n", " ").strip()
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
            return
        except Exception as e:
            print(f"[Voz Neural Edge-TTS Erro]: {e}. Usando sintetizador local...")
            
        # Fallback offline caso esteja sem conexão
        if shutil.which("espeak-ng"):
            subprocess.run(["espeak-ng", "-v", "pt-br", clean_text], stderr=subprocess.DEVNULL)
        elif shutil.which("spd-say"):
            subprocess.run(["spd-say", "-l", "pt", clean_text], stderr=subprocess.DEVNULL)

    threading.Thread(target=_speak_thread, daemon=True).start()
