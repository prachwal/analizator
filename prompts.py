from typing import List, Dict, Optional

# Zdefiniowane prompty na podstawie tagów
PROMPTS = {
    "default": {
        "description": "Domyślny prompt do analizy tytułów.",
        "template": (
            "Przeanalizuj poniższą listę tytułów filmów z kanału YouTube.\n"
            "1. Jaki jest ogólny sentyment (pozytywny, negatywny, neutralny)?\n"
            "2. Jakie są najczęstsze tematy?\n\n"
            "Lista tytułów:\n{titles}"
        ),
        "include_metadata": False,
        "include_transcription": False,
    },
    "detailed_analysis": {
        "description": "Szczegółowa analiza z metadanymi i transkrypcją.",
        "template": (
            "Przeanalizuj poniższe dane z kanału YouTube.\n"
            "1. Jaki jest ogólny sentyment (pozytywny, negatywny, neutralny)?\n"
            "2. Jakie są najczęstsze tematy?\n"
            "3. Jakie wnioski można wyciągnąć na podstawie transkrypcji?\n\n"
            "3. Jakie wnioski można wyciągnąć na podstawie metadanych?\n\n"
            "Lista tytułów:\n{titles}\n\n"
            "Metadane:\n{metadata}\n\n"
            "Transkrypcje:\n{transcriptions}"
        ),
        "include_metadata": True,
        "include_transcription": True,
    },
    "correlation_analysis": {
        "description": "Analiza korelacji między tytułami a parametrami (wyświetlenia, polubienia, komentarze).",
        "template": (
            "Przeanalizuj poniższe dane z kanału YouTube, aby znaleźć korelacje między tytułami filmów a ich parametrami:\n"
            "1. Jaki rodzaj treści ma najwięcej komentarzy?\n"
            "2. Jaki rodzaj treści najlepiej się ogląda (najwięcej wyświetleń)?\n"
            "3. Jaki rodzaj treści jest najczęściej polubiony?\n\n"
            "Lista tytułów i parametrów:\n"
            "{titles_and_parameters}\n\n"
            "Na podstawie powyższych danych wyciągnij wnioski dotyczące korelacji między tytułami a parametrami."
        ),
        "include_metadata": True,
        "include_transcription": False,
    },
    # Możesz dodać więcej promptów z różnymi tagami
}

def get_prompt_by_tag(tag: str) -> Optional[Dict]:
    """
    Pobiera prompt na podstawie tagu.

    Args:
        tag: Tag promptu.

    Returns:
        Słownik z danymi promptu lub None, jeśli tag nie istnieje.
    """
    return PROMPTS.get(tag)

def generate_prompt(
    tag: str,
    titles: List[str],
    metadata: Optional[List[Dict]] = None,
    transcriptions: Optional[List[str]] = None
) -> str:
    """
    Generuje treść promptu na podstawie tagu i danych wejściowych.

    Args:
        tag: Tag promptu.
        titles: Lista tytułów filmów.
        metadata: Lista metadanych filmów (opcjonalnie).
        transcriptions: Lista transkrypcji filmów (opcjonalnie).

    Returns:
        Wygenerowany prompt jako string.
    """
    prompt_data = get_prompt_by_tag(tag)
    if not prompt_data:
        raise ValueError(f"Nie znaleziono promptu dla tagu: {tag}")

    template = prompt_data["template"]
    include_metadata = prompt_data["include_metadata"]
    include_transcription = prompt_data["include_transcription"]

    # Przygotowanie danych dla korelacji, jeśli wymagane
    titles_and_parameters = ""
    if tag == "correlation_analysis" and metadata:
        titles_and_parameters = "\n".join(
            [
                f"- Tytuł: {meta['title']}, Wyświetlenia: {meta.get('view_count', 'Brak')}, "
                f"Polubienia: {meta.get('like_count', 'Brak')}, Komentarze: {meta.get('comment_count', 'Brak')}"
                for meta in metadata
            ]
        )

    return template.format(
        titles="\n".join([f"- {title}" for title in titles]),
        metadata="\n".join([str(meta) for meta in metadata]) if include_metadata and metadata else "Brak",
        transcriptions="\n".join(transcriptions) if include_transcription and transcriptions else "Brak",
        titles_and_parameters=titles_and_parameters
    )
