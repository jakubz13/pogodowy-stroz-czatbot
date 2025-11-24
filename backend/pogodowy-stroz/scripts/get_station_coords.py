# scripts/get_station_coords.py
import json
import httpx
from geopy.geocoders import Nominatim
from pathlib import Path
import time

# Ustawiamy User-Agent
geolocator = Nominatim(user_agent="pogodowy_stroz_app_v2")

# Upewnij się, że ta ścieżka celuje w ten sam folder 'data', co Twój data_service.py
# Zakładając strukturę: backend/scripts/ten_plik.py -> backend/data/
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def main():
    # Upewnij się, że folder data istnieje
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("1. Pobieranie listy stacji z IMGW...")
    try:
        # Timeout zwiększony dla bezpieczeństwa
        resp = httpx.get("https://danepubliczne.imgw.pl/api/data/synop", timeout=20)
        resp.raise_for_status()
        stations = resp.json()
    except Exception as e:
        print(f"BŁĄD POBIERANIA IMGW: {e}")
        return

    station_coords = {}
    print(f"2. Przetwarzanie {len(stations)} stacji...")

    for i, stacja in enumerate(stations):
        name = stacja['stacja']
        stacja_id = stacja['id_stacji']
        
        # Domyślne wartości (gdyby geokodowanie zawiodło)
        entry = {
            "name": name,
            "lat": None,
            "lon": None
        }

        try:
            # Szukamy: "Nazwa, Polska"
            location = geolocator.geocode(f"{name}, Polska")
            
            if location:
                entry["lat"] = location.latitude
                entry["lon"] = location.longitude
                print(f"[{i+1}/{len(stations)}] ✅ {name}: {location.latitude:.4f}, {location.longitude:.4f}")
            else:
                print(f"[{i+1}/{len(stations)}] ⚠️  Nie znaleziono koordynatów: {name} (Zapisuję bez nich)")
        
        except Exception as e:
            print(f"[{i+1}/{len(stations)}] ❌ Błąd geokodowania dla {name}: {e}")

        # Zapisujemy stację do słownika (nawet jeśli nie ma koordynatów!)
        station_coords[stacja_id] = entry

        # Opóźnienie dla Nominatim (wymagane przez TOS)
        time.sleep(1.1)

    # Zapis do pliku
    save_path = DATA_DIR / "station_coords.json"
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(station_coords, f, indent=2, ensure_ascii=False)
        print(f"\n🎉 SUKCES! Zapisano {len(station_coords)} stacji w: {save_path}")
    except Exception as e:
        print(f"\n❌ Błąd zapisu pliku: {e}")

if __name__ == "__main__":
    main()