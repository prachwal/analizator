import openai
import datetime
import os
import re  # Import do usuwania znaków specjalnych
from typing import List, Dict, Optional
from prompts import generate_prompt

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "TWOJ_KLUCZ_API_OPENAI")
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

def analyze_titles_with_openai(
    titles: List[str],
    tag: str = "default",
    metadata: Optional[List[Dict]] = None,
    transcriptions: Optional[List[str]] = None,
    model: Optional[str] = None
) -> str:
    """
    Analizuje tytuły filmów za pomocą API OpenAI.

    Args:
        titles: Lista tytułów filmów.
        tag: Tag promptu do użycia.
        metadata: Lista metadanych filmów (opcjonalnie).
        transcriptions: Lista transkrypcji filmów (opcjonalnie).
        model: Model OpenAI do użycia (opcjonalnie).

    Returns:
        Wynik analizy jako string.
    """
    if not titles:
        return "Brak tytułów do analizy."
    if not OPENAI_API_KEY or OPENAI_API_KEY == "TWOJ_KLUCZ_API_OPENAI":
        return "Błąd: Brak klucza API OpenAI."

    prompt = generate_prompt(tag, titles, metadata, transcriptions)
    model_to_use = model or DEFAULT_OPENAI_MODEL

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=model_to_use,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Błąd OpenAI: {type(e).__name__} - {e}"

def sanitize_folder_name(name: str) -> str:
    """
    Usuwa znaki specjalne z nazwy folderu.

    Args:
        name: Nazwa folderu.

    Returns:
        Nazwa folderu bez znaków specjalnych.
    """
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

def save_openai_analysis_to_file(channel_name: str, analysis: str, titles: List[str], channel_id: str, prompt_tag: str):
    """
    Zapisuje analizę OpenAI do pliku.

    Args:
        channel_name: Nazwa kanału.
        analysis: Wynik analizy.
        titles: Lista tytułów filmów.
        channel_id: ID kanału YouTube.
        prompt_tag: Tag użytego prompta.
    """
    sanitized_channel_name = sanitize_folder_name(channel_name)
    folder_name = os.path.join("analyses", sanitized_channel_name)
    os.makedirs(folder_name, exist_ok=True)

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    file_path = os.path.join(folder_name, f"openai_analysis_{prompt_tag}_{date_str}.md")
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(f"# Analiza OpenAI\n")
        file.write(f"## Prompt: {prompt_tag}\n")
        file.write(f"## Parametry wejściowe:\n")
        file.write(f"- Kanał: {channel_name}\n")
        file.write(f"- ID kanału: {channel_id}\n")
        file.write(f"- Liczba tytułów: {len(titles)}\n\n")
        file.write(f"## Wynik analizy:\n\n")
        file.write(f"{analysis}\n\n")
        file.write("## Tytuły wejściowe:\n")
        file.write("```\n")
        file.write("\n".join(titles))
        file.write("\n```\n")
    print(f"Zapisano analizę OpenAI w pliku: {file_path}")
