# backend/app/logic/utils.py
from typing import Any

def format_line(label: str, value: Any, unit: str = "") -> str | None:
    """
    Tworzy linię tekstu (np. '- Temperatura: 10 C') TYLKO jeśli wartość istnieje.
    Jeśli wartość to None, 'None' lub pusty string - zwraca None (linia jest pomijana).
    """
    if value is None or value == "None" or value == "" or value == "brak danych":
        return None
    return f"- {label}: **{value} {unit}**".strip()

def get_weather_icon(data: dict) -> str:
    """
    Dobiera ikonę pogodową na podstawie temperatury i opadu.
    """
    try:
        temp = float(data.get('temperatura', 0) or 0)
        opad = float(data.get('suma_opadu', 0) or 0)
        
        if opad > 0: return "🌧️"     # Pada
        if temp > 25: return "☀️"    # Gorąco
        if temp < 0: return "❄️"     # Mróz
        return "🌥️"                 # Standard
    except (ValueError, TypeError):
        return "🌡️"

def format_hydro_status(code: str) -> str:
    """
    Tłumaczy kody IMGW na ludzki język.
    """
    mapping = {
        '0': 'Stabilny',
        '1': '⚠️ Ostrzegawczy',
        '2': '🚨 ALARMOWY',
        '3': 'Susza'
    }
    return mapping.get(str(code), 'Brak danych')