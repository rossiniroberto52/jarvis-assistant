import os
import subprocess
import tempfile
import httpx
import speech_recognition as sr

from app.core.config import settings


async def _download_audio(url: str, dest_path: str) -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(r.content)


def _convert_to_wav(src: str, dst: str) -> bool:
    try:
        res = subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-ar", "16000", "-ac", "1", dst],
            capture_output=True,
        )
        return res.returncode == 0 and os.path.exists(dst)
    except FileNotFoundError:
        return False


def _recognize(wav_path: str, language: str) -> str:
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio_data, language=language).strip()
    except sr.UnknownValueError:
        return ""


async def transcribe_url(audio_url: str) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = os.path.join(tmpdir, "audio_raw")
        wav_path = os.path.join(tmpdir, "audio.wav")

        await _download_audio(audio_url, raw_path)

        if not _convert_to_wav(raw_path, wav_path):
            wav_path = raw_path

        return _recognize(wav_path, settings.stt_language)


async def transcribe_bytes(data: bytes, mime_type: str = "audio/ogg") -> str:
    suffix = ".ogg" if "ogg" in mime_type else ".webm"
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = os.path.join(tmpdir, f"audio_raw{suffix}")
        wav_path = os.path.join(tmpdir, "audio.wav")

        with open(raw_path, "wb") as f:
            f.write(data)

        if not _convert_to_wav(raw_path, wav_path):
            wav_path = raw_path

        return _recognize(wav_path, settings.stt_language)
