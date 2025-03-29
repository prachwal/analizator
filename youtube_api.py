import os
import json
from typing import List, Tuple, Optional
import googleapiclient.discovery
import googleapiclient.errors
from yt_dlp import YoutubeDL
from transcription import download_audio

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "TWOJ_KLUCZ_API_YOUTUBE")
CHANNEL_NAMES_CACHE = os.path.join("channels", "channel_names.json")  # Poprawiona ścieżka

def get_channel_name_from_cache(channel_id: str) -> Optional[str]:
    if os.path.exists(CHANNEL_NAMES_CACHE):
        with open(CHANNEL_NAMES_CACHE, "r", encoding="utf-8") as file:
            channel_names = json.load(file)
            return channel_names.get(channel_id)
    return None

def save_channel_name_to_cache(channel_id: str, channel_name: str):
    channel_names = {}
    if os.path.exists(CHANNEL_NAMES_CACHE):
        with open(CHANNEL_NAMES_CACHE, "r", encoding="utf-8") as file:
            channel_names = json.load(file)
    channel_names[channel_id] = channel_name
    with open(CHANNEL_NAMES_CACHE, "w", encoding="utf-8") as file:
        json.dump(channel_names, file, ensure_ascii=False, indent=4)

def get_channel_folder(channel_id: str) -> str:
    return os.path.join("channels", channel_id)

def clear_channel_folder(channel_id: str):
    """
    Usuwa wszystkie pliki i foldery w folderze kanału.

    Args:
        channel_id: ID kanału YouTube.
    """
    folder_name = get_channel_folder(channel_id)
    if os.path.exists(folder_name):
        print(f"Usuwanie zawartości folderu: {folder_name}")
        for item in os.listdir(folder_name):
            item_path = os.path.join(folder_name, item)
            if os.path.isdir(item_path):
                for sub_item in os.listdir(item_path):
                    os.remove(os.path.join(item_path, sub_item))
                os.rmdir(item_path)
            else:
                os.remove(item_path)

def get_youtube_video_titles(channel_id: str, max_results: int, force_refresh: bool = False) -> Tuple[Optional[str], List[dict]]:
    """
    Pobiera ostatnie `max_results` tytułów filmów, daty publikacji, ID wideo,
    opis i nazwę kanału z YouTube Data API lub cache.

    Args:
        channel_id: ID kanału YouTube.
        max_results: Maksymalna liczba filmów do pobrania (limit API to 50 na żądanie).
        force_refresh: Flaga wymuszająca odświeżenie cache.

    Returns:
        Krotka zawierająca (nazwa_kanału, lista_danych_wideo) lub (None, []) w przypadku błędu.
    """
    folder_name = get_channel_folder(channel_id)
    channel_name = get_channel_name_from_cache(channel_id)

    # Pobierz dane z cache, jeśli istnieją
    cached_video_ids = set()
    video_data = []
    if not force_refresh and os.path.exists(folder_name):
        print(f"Znaleziono dane w cache dla kanału ID: {channel_id}.")
        for file_name in os.listdir(folder_name):
            video_folder = os.path.join(folder_name, file_name)
            if os.path.isdir(video_folder):
                metadata_path = os.path.join(video_folder, "metadata.json")
                if os.path.exists(metadata_path):
                    with open(metadata_path, "r", encoding="utf-8") as file:
                        try:
                            data = json.load(file)
                            video_data.append(data)
                            cached_video_ids.add(data["video_id"])
                        except json.JSONDecodeError:
                            print(f"Błąd odczytu pliku JSON: {file_name}")

    # Jeśli wszystkie dane są w cache i nie wymuszono odświeżenia, zwróć dane
    if not force_refresh and len(video_data) >= max_results:
        return channel_name, video_data

    # Pobierz brakujące dane z API
    if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == "TWOJ_KLUCZ_API_YOUTUBE":
        print("Błąd krytyczny: Brak klucza API YouTube.")
        return None, []

    try:
        youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        channel_request = youtube.channels().list(part="snippet", id=channel_id)
        channel_response = channel_request.execute()

        if not channel_response.get("items"):
            print(f"Błąd: Nie znaleziono kanału o ID: {channel_id}")
            return None, []
        channel_name = channel_response["items"][0]["snippet"]["title"]
        save_channel_name_to_cache(channel_id, channel_name)

        # Pobierz listę filmów
        search_request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=min(max_results, 50),
            type="video",
            order="date"
        )
        search_response = search_request.execute()

        video_ids = [
            item["id"]["videoId"]
            for item in search_response.get("items", [])
            if item.get("id", {}).get("kind") == "youtube#video"
        ]

        # Filtruj brakujące filmy
        missing_video_ids = [video_id for video_id in video_ids if video_id not in cached_video_ids]

        # Pobierz szczegółowe informacje o brakujących filmach
        if missing_video_ids:
            videos_request = youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=",".join(missing_video_ids)
            )
            videos_response = videos_request.execute()

            for item in videos_response.get("items", []):
                video_data.append({
                    "title": item["snippet"]["title"],
                    "published_at": item["snippet"]["publishedAt"],
                    "video_id": item["id"],
                    "description": item["snippet"].get("description", ""),
                    "tags": item["snippet"].get("tags", []),
                    "category_id": item["snippet"].get("categoryId"),
                    "duration": item["contentDetails"].get("duration"),
                    "view_count": item["statistics"].get("viewCount"),
                    "like_count": item["statistics"].get("likeCount"),
                    "comment_count": item["statistics"].get("commentCount"),
                    "thumbnail_url": item["snippet"]["thumbnails"]["default"]["url"]
                })

        return channel_name, video_data

    except googleapiclient.errors.HttpError as e:
        print(f"Błąd API YouTube (HTTP {e.resp.status}): {e}")
        return None, []
    except Exception as e:
        print(f"Wystąpił nieoczekiwany błąd: {type(e).__name__} - {e}")
        return None, []

def cache_youtube_data(channel_id: str, channel_name: str, video_data: List[dict], download_audio_flag: bool, refresh_cache: bool = False):
    """
    Cache YouTube video data in a folder named after the channel ID.

    Args:
        channel_id: ID of the YouTube channel.
        channel_name: Nazwa kanału YouTube.
        video_data: Lista słowników zawierających szczegółowe dane o filmach.
        download_audio_flag: Flaga włączenia pobierania brakujących plików audio.
        refresh_cache: Flaga wymuszająca nadpisanie wszystkich danych.
    """
    folder_name = get_channel_folder(channel_id)
    os.makedirs(folder_name, exist_ok=True)

    for index, video in enumerate(video_data, start=1):
        video_id = video["video_id"]
        video_folder = os.path.join(folder_name, video_id)
        os.makedirs(video_folder, exist_ok=True)

        metadata_path = os.path.join(video_folder, "metadata.json")
        audio_path = os.path.join(video_folder, "audio.mp3")

        # Zmienna metadata musi być zawsze zdefiniowana
        metadata = None

        # Sprawdź, czy plik metadanych już istnieje
        if not refresh_cache and os.path.exists(metadata_path):
            print(f"Pominięto zapis metadanych, plik już istnieje: {metadata_path}")
            # Wczytaj istniejące metadane
            with open(metadata_path, "r", encoding="utf-8") as file:
                metadata = json.load(file)

            # Uzupełnij brakujące klucze w metadanych
            for key in ["channel_id", "channel_name", "title", "published_at", "video_id", "description", "tags", "category_id", "duration", "view_count", "like_count", "comment_count", "thumbnail_url", "video_url"]:
                if key not in metadata:
                    metadata[key] = video.get(key, None)
        else:
            print(f"Zapisywanie metadanych do pliku: {metadata_path}")
            metadata = {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "title": video["title"],
                "published_at": video["published_at"],
                "video_id": video["video_id"],
                "description": video.get("description", ""),
                "tags": video.get("tags", []),
                "category_id": video.get("category_id"),
                "duration": video.get("duration"),
                "view_count": video.get("view_count"),
                "like_count": video.get("like_count"),
                "comment_count": video.get("comment_count"),
                "thumbnail_url": video.get("thumbnail_url"),
                "video_url": f"https://www.youtube.com/watch?v={video_id}"
            }
            with open(metadata_path, "w", encoding="utf-8") as file:
                json.dump(metadata, file, ensure_ascii=False, indent=4)

        # Pobierz audio, jeśli flaga jest włączona
        if download_audio_flag and metadata and metadata.get("video_url") and (refresh_cache or not os.path.exists(audio_path)):
            print(f"Pobieranie pliku audio dla wideo: {video_id}")
            download_audio(video_id, metadata["video_url"], video_folder)
        elif not metadata.get("video_url"):
            print(f"Brak URL wideo dla {video_id}, pominięto pobieranie audio.")

def get_youtube_video_details(video_url: str) -> Tuple[Optional[dict], Optional[str], Optional[str]]:
    """
    Pobiera szczegóły filmu na podstawie URL YouTube.

    Args:
        video_url: URL filmu YouTube.

    Returns:
        Krotka zawierająca:
        - Szczegóły filmu jako słownik.
        - ID kanału.
        - Nazwę kanału.
    """
    video_id = video_url.split("v=")[-1]
    if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == "TWOJ_KLUCZ_API_YOUTUBE":
        print("Błąd krytyczny: Brak klucza API YouTube.")
        return None, None, None

    try:
        youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        video_request = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_id
        )
        video_response = video_request.execute()

        if not video_response.get("items"):
            print(f"Błąd: Nie znaleziono filmu o URL: {video_url}")
            return None, None, None

        video = video_response["items"][0]
        channel_id = video["snippet"]["channelId"]
        channel_name = video["snippet"]["channelTitle"]

        video_data = {
            "title": video["snippet"]["title"],
            "published_at": video["snippet"]["publishedAt"],
            "video_id": video_id,
            "description": video["snippet"].get("description", ""),
            "tags": video["snippet"].get("tags", []),
            "category_id": video["snippet"].get("categoryId"),
            "duration": video["contentDetails"].get("duration"),
            "view_count": video["statistics"].get("viewCount"),
            "like_count": video["statistics"].get("likeCount"),
            "comment_count": video["statistics"].get("commentCount"),
            "thumbnail_url": video["snippet"]["thumbnails"]["default"]["url"]
        }

        return video_data, channel_id, channel_name

    except googleapiclient.errors.HttpError as e:
        print(f"Błąd API YouTube (HTTP {e.resp.status}): {e}")
        return None, None, None
    except Exception as e:
        print(f"Wystąpił nieoczekiwany błąd: {type(e).__name__} - {e}")
        return None, None, None

def cache_youtube_video(channel_id: str, channel_name: str, video_data: dict):
    """
    Zapisuje dane filmu w cache i dodaje kanał do channel_names.json, jeśli nie istnieje.

    Args:
        channel_id: ID kanału YouTube.
        channel_name: Nazwa kanału YouTube.
        video_data: Szczegóły filmu jako słownik.
    """
    # Dodaj kanał do channel_names.json, jeśli nie istnieje
    os.makedirs("channels", exist_ok=True)  # Upewnij się, że folder channels istnieje

    if not os.path.exists(CHANNEL_NAMES_CACHE):
        with open(CHANNEL_NAMES_CACHE, "w", encoding="utf-8") as file:
            json.dump({}, file, ensure_ascii=False, indent=4)

    with open(CHANNEL_NAMES_CACHE, "r", encoding="utf-8") as file:
        channel_names = json.load(file)

    if channel_id not in channel_names:
        print(f"Dodawanie kanału do channel_names.json: {channel_name} ({channel_id})")
        channel_names[channel_id] = channel_name
        with open(CHANNEL_NAMES_CACHE, "w", encoding="utf-8") as file:
            json.dump(channel_names, file, ensure_ascii=False, indent=4)

    # Zapisz dane filmu w cache
    folder_name = get_channel_folder(channel_id)
    os.makedirs(folder_name, exist_ok=True)

    video_id = video_data["video_id"]
    video_folder = os.path.join(folder_name, video_id)
    os.makedirs(video_folder, exist_ok=True)

    print(f"Zapisywanie danych filmu w folderze: {video_folder}")
    metadata_path = os.path.join(video_folder, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as file:
        json.dump(video_data, file, ensure_ascii=False, indent=4)  # Poprawione wcięcie
