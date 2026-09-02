import os
import subprocess
import speech_recognition as sr
from ctypes import CFUNCTYPE, c_char_p, c_int, cdll

# Suprimir mensagens de aviso do ALSA no Linux/Arch
try:
    ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
    def py_error_handler(filename, line, function, err, fmt):
        pass
    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
    asound = cdll.LoadLibrary('libasound.so.2')
    asound.snd_lib_error_set_handler(c_error_handler)
except Exception:
    pass

def transcribe_audio_file(audio_path: str, language: str = "pt-BR") -> str:
    """
    Recebe o caminho de um arquivo de áudio (webm, ogg, wav, mp3),
    converte para WAV 16kHz mono via ffmpeg se necessário e transcreve com SpeechRecognition.
    """
    wav_path = audio_path
    temp_wav = None

    if not audio_path.endswith(".wav"):
        temp_wav = audio_path + "_conv.wav"
        try:
            cmd = f'ffmpeg -y -i "{audio_path}" -ar 16000 -ac 1 "{temp_wav}"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0 and os.path.exists(temp_wav):
                wav_path = temp_wav
        except Exception as e:
            print(f"[STT] Falha ao converter via ffmpeg: {e}")
            wav_path = audio_path

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language=language)
            return text.strip()
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        print(f"[STT] Erro no reconhecimento de áudio: {e}")
        return ""
    finally:
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except Exception:
                pass

def listen_mic(prompt="Ouvindo... Fale agora, Senhor:"):
    """Captura áudio do microfone e converte em texto (em Português)."""
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    
    with sr.Microphone() as source:
        print(f"\n🎙️  [{prompt}]")
        try:
            recognizer.adjust_for_ambient_noise(source, duration=0.8)
            audio = recognizer.listen(source, timeout=6, phrase_time_limit=12)
            print("⏳ Processando voz...")
            text = recognizer.recognize_google(audio, language="pt-BR")
            print(f"🗣️  Você disse: \"{text}\"")
            return text
        except sr.WaitTimeoutError:
            print("⚠️ Tempo esgotado (nenhuma fala detectada).")
            return None
        except sr.UnknownValueError:
            print("⚠️ Não consegui entender o áudio.")
            return None
        except Exception as e:
            print(f"⚠️ Erro ao capturar áudio: {e}")
            return None

def listen_for_wake_word(wake_word="jarvis"):
    """Escuta continuamente até detectar a palavra de ativação 'Jarvis'."""
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    
    with sr.Microphone() as source:
        print(f"👂 [Modo Escuta Contínua Ativo: Diga '{wake_word.capitalize()}' para ativar...]")
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
        
        while True:
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
                text = recognizer.recognize_google(audio, language="pt-BR").lower()
                
                if wake_word in text:
                    print(f"⚡ [Palavra-chave detectada: '{text}']")
                    # Se o usuário disse "Jarvis qual a hora", pega o comando junto
                    command = text.split(wake_word, 1)[-1].strip()
                    if command:
                        return command
                    else:
                        # Diga o comando em seguida
                        return listen_mic(prompt="Pois não, Senhor? Pode falar o comando:")
            except (sr.WaitTimeoutError, sr.UnknownValueError):
                continue
            except Exception as e:
                print(f"Erro na escuta de wake-word: {e}")
                continue
