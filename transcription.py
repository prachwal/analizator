import os
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import whisper

def download_audio(video_id: str, video_url: str, output_folder: str):
    """
    Pobiera plik audio z YouTube, jeśli nie istnieje na dysku.

    Args:
        video_id: ID wideo.
        video_url: URL wideo.
        output_folder: Ścieżka do folderu wyjściowego.
    """
    os.makedirs(output_folder, exist_ok=True)

    # Ścieżka do pliku audio
    audio_path = os.path.join(output_folder, "audio.mp3")

    # Sprawdź, czy plik już istnieje
    if os.path.exists(audio_path):
        print(f"Pominięto pobieranie, plik audio już istnieje: {audio_path}")
        return

    # Pobierz plik audio
    print(f"Pobieranie audio dla wideo: {video_url} do {audio_path}")
    ydl_opts = {
        "format": "bestaudio/best",
        "extract_audio": True,
        "audio_format": "mp3",
        "audio_quality": "128",  # ustawienie bitrate na 128 kbps
        "outtmpl": audio_path,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        },
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        print(f"Pobrano audio do pliku: {audio_path}")
    except DownloadError as e:
        print(f"Błąd podczas pobierania audio dla wideo {video_id}: {e}")

def transcribe_audio(audio_path: str, output_path: str) -> str:
    """
    Tworzy transkrypcję pliku audio za pomocą modelu Whisper.

    Args:
        audio_path: Ścieżka do pliku audio.
        output_path: Ścieżka do pliku wyjściowego z transkrypcją.

    Returns:
        Transkrypcja jako string.
    """
    print(f"Rozpoczynanie transkrypcji pliku: {audio_path}")
    model = whisper.load_model("base")  # Użyj modelu Whisper
    result = model.transcribe(audio_path, language="pl")

    # Zapisz transkrypcję do pliku
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(result["text"])
    print(f"Zapisano transkrypcję do pliku: {output_path}")

    return result["text"]
