import requests
import os
import re  # Import do usuwania znaków specjalnych
from typing import List, Dict, Optional
from prompts import generate_prompt

GROK_API_KEY = os.getenv("GROK_API_KEY", "TWOJ_KLUCZ_API_GROK")
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
DEFAULT_GROK_MODEL = "grok-2-1212"

def analyze_titles_with_grok(
    titles: List[str],
    tag: str = "default",
    metadata: Optional[List[Dict]] = None,
    transcriptions: Optional[List[str]] = None,
    model: Optional[str] = None
) -> str:
    """
    Analizuje tytuły filmów za pomocą API Grok.

    Args:
        titles: Lista tytułów filmów.
        tag: Tag promptu do użycia.
        metadata: Lista metadanych filmów (opcjonalnie).
        transcriptions: Lista transkrypcji filmów (opcjonalnie).
        model: Model Grok do użycia (opcjonalnie).

    Returns:
        Wynik analizy jako string.
    """
    if not titles:
        return "Brak tytułów do analizy."
    if not GROK_API_KEY or GROK_API_KEY == "TWOJ_KLUCZ_API_GROK":
        return "Błąd: Brak klucza API Grok."

    prompt = generate_prompt(tag, titles, metadata, transcriptions)
    model_to_use = model or DEFAULT_GROK_MODEL

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model_to_use,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1500,
        "temperature": 0.5  # Dodano parametr temperatury, jak w OpenAI
    }

    try:
        response = requests.post(GROK_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Błąd Grok: {type(e).__name__} - {e}"

def sanitize_folder_name(name: str) -> str:
    """
    Usuwa znaki specjalne z nazwy folderu.

    Args:
        name: Nazwa folderu.

    Returns:
        Nazwa folderu bez znaków specjalnych.
    """
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

