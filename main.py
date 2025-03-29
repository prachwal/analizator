import sys
import json
import os
import shutil  # Dodaj import do obsługi usuwania folderów
from argparse import ArgumentParser
from typing import Optional  # Import Optional for type hints
from youtube_api import get_youtube_video_titles, cache_youtube_data, clear_channel_folder
from openai_analysis import analyze_titles_with_openai, save_openai_analysis_to_file
from grok_analysis import analyze_titles_with_grok, save_grok_analysis_to_file
from youtube_api import get_youtube_video_details, cache_youtube_video  # Import nowych funkcji
from transcription import download_audio as download_audio_file  # Zmieniono nazwę importowanej funkcji

DEFAULT_MAX_RESULTS = 50
CHANNEL_NAMES_FILE = os.path.join("channels", "channel_names.json")  # Poprawiona ścieżka do pliku

def parse_arguments():
    """
    Parsuje argumenty linii poleceń i zwraca ID kanału YouTube oraz opcje analizy AI.

    Returns:
        Argumenty przekazane do programu.
    """
    parser = ArgumentParser(description="Analizator kanałów YouTube.")
    parser.add_argument(
        "--channel_id",
        type=str,
        help="ID kanału YouTube, który ma zostać przeanalizowany. Jeśli nie podano, używany jest plik channel_names.json."
    )
    parser.add_argument(
        "--video_url",
        type=str,
        help="URL filmu YouTube, który ma zostać przeanalizowany."
    )
    parser.add_argument(
        "--enable_openai",
        action="store_true",
        help="Włącza analizę AI za pomocą OpenAI."
    )
    parser.add_argument(
        "--enable_grok",
        action="store_true",
        help="Włącza analizę AI za pomocą Grok."
    )
    parser.add_argument(
        "--refresh_cache",
        action="store_true",
        help="Wymusza odświeżenie cache dla wszystkich kanałów."
    )
    parser.add_argument(
        "--download_audio",
        action="store_true",
        help="Włącza pobieranie brakujących plików audio podczas odświeżania cache."
    )
    parser.add_argument(
        "--enable_transcription",
        action="store_true",
        help="Włącza transkrypcję audio na tekst."
    )
    parser.add_argument(
        "--include_metadata",
        type=bool,
        default=True,
        help="Włącza dołączanie metadanych do analizy (domyślnie: True)."
    )
    parser.add_argument(
        "--prompt_tag",
        type=str,
        default="default",
        help="Wybiera tag promptu do użycia w analizie (domyślnie: 'default')."
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Czyści folder `channels`, ale zachowuje plik channel_names.json."
    )
    return parser.parse_args()

def load_channel_ids_from_file() -> dict:
    """
    Wczytuje ID kanałów i ich nazwy z pliku channel_names.json.

    Returns:
        Słownik z ID kanałów jako klucze i nazwami kanałów jako wartości.
    """
    absolute_path = os.path.abspath(CHANNEL_NAMES_FILE)  # Pobierz ścieżkę bezwzględną
    print(f"Ścieżka do pliku channel_names.json (bezwzględna): {absolute_path}")  # Wydrukuj ścieżkę
    if not os.path.exists(CHANNEL_NAMES_FILE):
        print(f"Plik {CHANNEL_NAMES_FILE} nie istnieje.")
        return {}
    with open(CHANNEL_NAMES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

def process_channel(
    channel_id: str,
    enable_openai: bool,
    enable_grok: bool,
    refresh_cache: bool,
    download_audio: bool,
    openai_tag: str = "default",
    openai_model: Optional[str] = None
):
    """
    Przetwarza pojedynczy kanał YouTube.

    Args:
        channel_id: ID kanału YouTube.
        enable_openai: Flaga włączenia analizy OpenAI.
        enable_grok: Flaga włączenia analizy Grok.
        refresh_cache: Flaga wymuszająca odświeżenie cache.
        download_audio: Flaga włączenia pobierania brakujących plików audio.
        openai_tag: Tag promptu do użycia w OpenAI.
        openai_model: Model OpenAI do użycia (opcjonalnie).
    """
    print(f"\nRozpoczynanie pracy dla kanału ID: {channel_id}")
    channel_name, video_data = get_youtube_video_titles(channel_id, max_results=DEFAULT_MAX_RESULTS, force_refresh=refresh_cache)

    if not video_data:
        print(f"\nNie udało się pobrać danych o filmach dla kanału ID: {channel_id}.")
        return

    print(f"\nPrzetwarzanie kanału: {channel_name}")
    print(f"Pobrano {len(video_data)} tytułów.")

    # Zapisz dane do cache
    cache_youtube_data(channel_id, channel_name, video_data, download_audio, refresh_cache)

    titles = [video["title"] for video in video_data]

    # --- Analiza Tytułów ---
    print("\n--- Rozpoczynanie analizy tytułów ---")

    if enable_openai:
        print(f"Rozpoczynanie analizy OpenAI dla kanału: {channel_name}")
        openai_analysis = analyze_titles_with_openai(
            titles, tag=openai_tag, metadata=None, transcriptions=None, model=openai_model
        )
        save_openai_analysis_to_file(channel_name, openai_analysis, titles, channel_id, openai_tag)

    if enable_grok:
        print(f"Rozpoczynanie analizy Grok dla kanału: {channel_name}")
        grok_analysis = analyze_titles_with_grok(titles)
        save_grok_analysis_to_file(channel_name, grok_analysis, titles, channel_id, openai_tag)

    print(f"Zakończono przetwarzanie kanału: {channel_name}")

def process_video_url(
    video_url: str,
    enable_openai: bool,
    enable_grok: bool,
    download_audio: bool,
    enable_transcription: bool,
    include_metadata: bool = True,
    prompt_tag: str = "default",
    openai_model: Optional[str] = None
):
    """
    Przetwarza pojedynczy film na podstawie URL YouTube.

    Args:
        video_url: URL filmu YouTube.
        enable_openai: Flaga włączenia analizy OpenAI.
        enable_grok: Flaga włączenia analizy Grok.
        download_audio: Flaga włączenia pobierania audio.
        enable_transcription: Flaga włączenia transkrypcji audio.
        include_metadata: Flaga włączenia metadanych w analizie.
        prompt_tag: Tag promptu do użycia w analizie.
        openai_model: Model OpenAI do użycia (opcjonalnie).
    """
    print(f"\nRozpoczynanie pracy dla filmu: {video_url}")

    # Pobierz szczegóły filmu
    video_data, channel_id, channel_name = get_youtube_video_details(video_url)

    if not video_data:
        print(f"\nNie udało się pobrać danych o filmie: {video_url}.")
        return

    # Cache kanał i film
    print(f"Zapisywanie danych w cache dla kanału: {channel_name} ({channel_id})")
    cache_youtube_video(channel_id, channel_name, video_data)

    # Pobierz audio, jeśli flaga jest ustawiona
    video_folder = os.path.join("channels", channel_id, video_data["video_id"])
    if download_audio:
        print(f"Pobieranie audio dla filmu: {video_data['title']}")
        download_audio_file(video_data["video_id"], video_url, video_folder)

    # Wykonaj transkrypcję, jeśli flaga jest ustawiona
    transcriptions = []
    if enable_transcription:
        transcription_path = os.path.join(video_folder, "transcription.txt")
        if os.path.exists(transcription_path):
            print(f"Pominięto transkrypcję, plik już istnieje: {transcription_path}")
            with open(transcription_path, "r", encoding="utf-8") as file:
                transcriptions.append(file.read())
        else:
            print(f"Rozpoczynanie transkrypcji dla filmu: {video_data['title']}")
            from transcription import transcribe_audio  # Import funkcji transkrypcji
            transcription = transcribe_audio(os.path.join(video_folder, "audio.mp3"), transcription_path)
            transcriptions.append(transcription)

    titles = [video_data["title"]]
    metadata = [video_data] if include_metadata else None

    # --- Analiza Tytułów ---
    print("\n--- Rozpoczynanie analizy tytułów ---")

    if enable_openai:
        print(f"Rozpoczynanie analizy OpenAI dla filmu: {video_data['title']}")
        print(f"Użyty prompt: {prompt_tag}, Metadane: {'Włączone' if include_metadata else 'Wyłączone'}, "
              f"Transkrypcje: {'Włączone' if enable_transcription else 'Wyłączone'}, Model: {openai_model or 'Domyślny'}")
        openai_analysis = analyze_titles_with_openai(
            titles, tag=prompt_tag, metadata=metadata, transcriptions=transcriptions, model=openai_model
        )
        print("\nAnaliza OpenAI:")
        print(openai_analysis)

    if enable_grok:
        print(f"Rozpoczynanie analizy Grok dla filmu: {video_data['title']}")
        print(f"Użyty prompt: {prompt_tag}, Metadane: {'Włączone' if include_metadata else 'Wyłączone'}, "
              f"Transkrypcje: {'Włączone' if enable_transcription else 'Wyłączone'}")
        grok_analysis = analyze_titles_with_grok(titles)
        print("\nAnaliza Grok:")
        print(grok_analysis)

    print(f"Zakończono przetwarzanie filmu: {video_url}")

def clean_channels_folder():
    """
    Czyści folder `channels`, ale zachowuje plik `channel_names.json`.
    """
    channels_folder = os.path.join("channels")
    if not os.path.exists(channels_folder):
        print(f"Folder {channels_folder} nie istnieje.")
        return

    print(f"Czyszczenie folderu: {channels_folder}")
    for item in os.listdir(channels_folder):
        item_path = os.path.join(channels_folder, item)
        if os.path.isdir(item_path):
            try:
                print(f"Usuwanie folderu: {item_path}")
                shutil.rmtree(item_path)  # Użyj shutil.rmtree do usuwania folderów
            except PermissionError as e:
                print(f"Błąd: Odmowa dostępu podczas usuwania folderu {item_path}. Szczegóły: {e}")
        elif os.path.isfile(item_path) and os.path.basename(item_path) != "channel_names.json":
            try:
                print(f"Usuwanie pliku: {item_path}")
                os.remove(item_path)
            except PermissionError as e:
                print(f"Błąd: Odmowa dostępu podczas usuwania pliku {item_path}. Szczegóły: {e}")

def main():
    """Główna funkcja skryptu."""
    args = parse_arguments()

    if args.clean:
        clean_channels_folder()
        return

    if args.channel_id:
        process_channel(
            args.channel_id, args.enable_openai, args.enable_grok, args.refresh_cache, args.download_audio,
            openai_tag=args.prompt_tag, openai_model=None
        )
    elif args.video_url:
        process_video_url(
            args.video_url, args.enable_openai, args.enable_grok, args.download_audio, args.enable_transcription,
            args.include_metadata, args.prompt_tag, openai_model=None
        )
    else:
        channels = load_channel_ids_from_file()
        if not channels:
            print("Brak kanałów do przetworzenia.")
            return
        total_channels = len(channels)
        for index, (channel_id, channel_name) in enumerate(channels.items(), start=1):
            print(f"\nPrzetwarzanie kanału {index}/{total_channels}: {channel_name}")
            process_channel(
                channel_id, args.enable_openai, args.enable_grok, args.refresh_cache, args.download_audio,
                openai_tag=args.prompt_tag, openai_model=None
            )

if __name__ == "__main__":
    main()
