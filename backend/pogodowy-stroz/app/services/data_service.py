# backend/app/services/data_service.py
import json
import unicodedata
import difflib
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.distance import geodesic
from app.api.imgw_client import ImgwApiClient

# --- KONFIGURACJA ---

# FIX #5: Stopwords - słowa ignorowane przy szukaniu nazw geograficznych
STOPWORDS = {
    'dla', 'w', 'na', 'miasto', 'powiat', 'gmina', 'z', 'do', 'przy', 'koło',
    'jest', 'jaka', 'jaki', 'czy', 'prosze', 'podaj', 'sprawdz', 'teraz',
    'stan', 'wody', 'woda', 'poziom', 'rzeka', 'rzeki', 'potok', 'jezioro'
}

COMMON_SUFFIXES = ['ach', 'ami', 'iem', 'owi', 'om', 'ie', 'iu', 'y', 'a', 'e', 'u', 'i']

# FIX #3: Priorytety Intencji (Keywords)
STRONG_WARNING_KEYWORDS = {'ostrzeżenie', 'ostrzeżenia', 'alert', 'alerty', 'zagrożenie', 'rcb'}
STRONG_WEATHER_KEYWORDS = {'pogoda', 'pogodę', 'temperatura', 'wiatr', 'cisnienie', 'slonce', 'deszcz', 'prognoza', 'stopni', 'pada', 'zimno', 'cieplo'}
STRONG_HYDRO_KEYWORDS = {'stan', 'wody', 'poziom', 'rzeka', 'wodowskaz', 'hydrologiczny', 'wylewa'}

# --- HELPERY ---

def format_line(label: str, value: any, unit: str = "") -> str | None:
    if value is None or value == "None" or value == "" or value == "brak danych":
        return None
    return f"- {label}: **{value} {unit}**".strip()

def get_weather_icon(data: dict) -> str:
    try:
        temp = float(data.get('temperatura', 0) or 0)
        opad = float(data.get('suma_opadu', 0) or 0)
        if opad > 0: return "🌧️"
        if temp > 25: return "☀️"
        if temp < 0: return "❄️"
        return "🌥️"
    except: return "🌡️"

def format_hydro_status(code: str) -> str | None:
    mapping = {'0': 'Stan w normie', '1': '⚠️ Ostrzegawczy', '2': '🚨 ALARMOWY', '3': 'Susza'}
    return mapping.get(str(code))

def format_trend(trend_val) -> str | None:
    return str(trend_val) if trend_val else None

# --- GŁÓWNA KLASA ---

class DataService:
    def __init__(self):
        self.imgw_client = ImgwApiClient()
        self.geolocator = Nominatim(user_agent="pogodowy_stroz_bot_final_fix", timeout=5)
        self._initialize_data()

    def _initialize_data(self):
        try:
            BASE_DIR = Path(__file__).resolve().parent.parent
            DATA_DIR = BASE_DIR / "data"

            self.terc_dict = self._load_and_normalize_keys(DATA_DIR / "terc_dict.json")
            self.simc_dict = self._load_and_normalize_keys(DATA_DIR / "simc_dict.json")
            self.map_simc_to_synop = self._load_json(DATA_DIR / "map_simc_to_imgw_synop.json")
            self.map_hydro = self._load_and_normalize_keys(DATA_DIR / "map_hydro.json")
            self.station_coords = self._load_json(DATA_DIR / "station_coords.json")
            
            self.synop_names_map = {}
            for sid, data in self.station_coords.items():
                self.synop_names_map[self._normalize(data['name'])] = sid
            
            self.terc_id_to_name = {v: k.title() for k, v in self.terc_dict.items()}
            
            self.known_rivers = set()
            for key in self.map_hydro.keys():
                parts = key.split()
                if parts: self.known_rivers.add(parts[0])

            print("SUKCES: Dane załadowane.")
        except Exception as e:
            print(f"BŁĄD DANYCH: {e}")
            self.station_coords = {}
            self.synop_names_map = {}
            self.terc_dict = {}
            self.map_hydro = {}
            self.known_rivers = set()

    def _load_json(self, path):
        if not path.exists(): return {}
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)

    def _load_and_normalize_keys(self, path):
        data = self._load_json(path)
        return {self._normalize(k): v for k, v in data.items()}

    def _normalize(self, text: str, stemming=False):
        if not text: return ""
        text = text.lower()
        replacements = {'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'}
        for k, v in replacements.items(): text = text.replace(k, v)
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        text = text.strip()
        if stemming and len(text) > 4:
            for suffix in COMMON_SUFFIXES:
                if text.endswith(suffix): return text[:-len(suffix)]
        return text

    def _smart_find_key(self, candidate: str, dictionary: dict, threshold=0.9) -> tuple[str, str] | None:
        norm_cand = self._normalize(candidate)
        
        # FIX #5: EXACT MATCH FIRST (Kołobrzeg != Koło)
        if norm_cand in dictionary: return dictionary[norm_cand], norm_cand
        
        # Substring check (Reverse lookup dla nazw wieloczłonowych)
        for key in dictionary.keys():
            if key == norm_cand: return dictionary[key], key
            # Sprawdzamy czy kandydat zawiera się w kluczu LUB klucz w kandydacie
            if len(key) > 3 and len(norm_cand) > 3:
                if key in norm_cand or norm_cand in key:
                     return dictionary[key], key
                 
        matches = difflib.get_close_matches(norm_cand, dictionary.keys(), n=1, cutoff=threshold)
        if matches: return dictionary[matches[0]], matches[0]
        return None

    # --- FEATURE: NEAREST NEIGHBOR ---
    def find_nearest_station(self, user_location_name: str):
        try:
            print(f"DEBUG GEO: Szukam '{user_location_name}'")
            location = self.geolocator.geocode(
                f"{user_location_name}", 
                country_codes="pl",
                language="pl",
                addressdetails=True
            )
            
            if not location: return None, None, None

            # Filtracja typów (sklepy out)
            raw = location.raw
            obj_class = raw.get('class', '')
            valid_classes = ['place', 'boundary']
            if obj_class not in valid_classes: return None, None, None
            if obj_class == 'boundary' and raw.get('type') != 'administrative': return None, None, None

            # FIX #2: COORDINATE ORDER
            # Geopy geodesic wymaga (LATITUDE, LONGITUDE)
            user_coords = (location.latitude, location.longitude)
            
            nearest_sid = None
            min_dist = float('inf')
            nearest_name = ""

            for sid, data in self.station_coords.items():
                if data.get('lat') is None: continue
                
                # Upewniamy się, że dane stacji też są (LAT, LON)
                st_coords = (float(data['lat']), float(data['lon']))
                
                dist = geodesic(user_coords, st_coords).km
                
                if dist < min_dist:
                    min_dist = dist
                    nearest_sid = sid
                    nearest_name = data['name']
            
            if nearest_sid and min_dist < 100:
                return nearest_sid, nearest_name, round(min_dist, 1)
                
        except Exception as e:
            print(f"DEBUG GEO ERROR: {e}")
        
        return None, None, None

    def validate_and_get_id(self, entities: dict, intent: str, original_text: str = "", city_context: str = None):
        clean_text_lower = self._normalize(original_text)
        
        # FIX #3: Wyliczanie priorytetów na podstawie słów kluczowych
        has_warning_kw = any(kw in clean_text_lower for kw in STRONG_WARNING_KEYWORDS)
        has_weather_kw = any(kw in clean_text_lower for kw in STRONG_WEATHER_KEYWORDS)
        has_hydro_kw = any(kw in clean_text_lower for kw in STRONG_HYDRO_KEYWORDS)
        
        # Generowanie kandydatów
        candidates = []
        candidates.append(original_text)
        if entities.get('placeName'): candidates.extend(entities['placeName'])
        if entities.get('geogName'): candidates.extend(entities['geogName'])
        candidates.extend([w for w in clean_text_lower.split() if len(w) > 3 and w not in STOPWORDS])

        # === STRICT ROUTING LOGIC ===
        target_intent = intent

        if has_warning_kw:
            target_intent = 'ostrzeżenia'
        elif has_weather_kw:
            target_intent = 'pogoda'
        elif has_hydro_kw:
            target_intent = 'hydro'
        else:
            # Jeśli brak słów kluczowych, sprawdzamy czy tekst zawiera znaną rzekę
            for word in clean_text_lower.split():
                if word in self.known_rivers:
                    target_intent = 'hydro'
                    break
        
        # === HYDRO LOGIC (FIX #1 & #4) ===
        if target_intent == 'hydro':
            
            # 1. Intersection: Input + Context (Miasto)
            if city_context:
                norm_ctx = self._normalize(city_context)
                for cand in candidates:
                    norm_cand = self._normalize(cand)
                    # Szukamy klucza zawierającego oba słowa
                    for key, val in self.map_hydro.items():
                        if norm_cand in key and norm_ctx in key:
                             return val, 'hydro', key

            # 2. Intersection: Input zawiera oba (np. "Odra we Wrocławiu")
            for cand in candidates:
                res = self._smart_find_key(cand, self.map_hydro, threshold=0.85)
                if res: return res[0], 'hydro', res[1]

            # 3. Brute Force łączenia słów z inputu
            words = [w for w in clean_text_lower.split() if len(w)>3 and w not in STOPWORDS]
            if len(words) >= 2:
                for i in range(len(words)):
                    for j in range(len(words)):
                        if i == j: continue
                        w1, w2 = words[i], words[j]
                        # Szukamy klucza z oboma słowami
                        for key, val in self.map_hydro.items():
                             if w1 in key and w2 in key:
                                  return val, 'hydro', key
            
            # FIX #1: MAMRY KILLER
            # Jeśli doszliśmy tutaj, to znaczy, że nie znaleźliśmy konkretnego dopasowania.
            # Nie zwracamy nic. Bot zapyta usera o szczegóły.
            return None, 'hydro', None

        # === POGODA LOGIC ===
        if target_intent == 'pogoda':
            # 1. Baza Synop/Simc
            for cand in candidates:
                res = self._smart_find_key(cand, self.synop_names_map, threshold=0.90)
                if res: return res[0], 'pogoda', res[1]
                
                res_simc = self._smart_find_key(cand, self.simc_dict, threshold=0.90)
                if res_simc:
                    simc_id, found_name = res_simc
                    if str(simc_id) in self.map_simc_to_synop:
                        return self.map_simc_to_synop[str(simc_id)], 'pogoda', found_name

            # 2. Nearest Neighbor
            search_query = entities.get('placeName', [original_text])[0]
            if self._normalize(search_query) in STRONG_WEATHER_KEYWORDS:
                 return None, 'pogoda', None

            sid, s_name, dist = self.find_nearest_station(search_query)
            if sid:
                return sid, 'pogoda', f"NEAREST|{search_query}|{s_name}|{dist}"

        # === OSTRZEŻENIA LOGIC ===
        if target_intent == 'ostrzeżenia':
            for cand in candidates:
                res = self._smart_find_key(cand, self.terc_dict, threshold=0.85)
                if res: return res[0], 'ostrzeżenia', res[1]
            if city_context:
                res = self._smart_find_key(city_context, self.terc_dict, threshold=0.85)
                if res: return res[0], 'ostrzeżenia', res[1]

        return None, target_intent, None

    async def fetch_data(self, intent: str, location_id: str, location_name: str = "") -> str:
        try:
            if intent == 'pogoda':
                data = await self.imgw_client.get_synop_data(location_id)
                return self._format_weather(data, location_name)
            elif intent == 'hydro':
                data = await self.imgw_client.get_hydro_data(location_id)
                return self._format_hydro(data)
            elif intent == 'ostrzeżenia':
                data = await self.imgw_client.get_meteo_warnings()
                return self._format_warnings(data, location_id, location_name)
        except Exception as e:
            return f"Błąd API: {str(e)}"
        return "Nieznana intencja."

    # --- FORMATOWANIE ---
    def _format_weather(self, data: dict, loc_name_meta: str) -> str:
        if not data: return "Brak danych."
        header = ""
        if loc_name_meta and "NEAREST|" in loc_name_meta:
            _, query, st_name, dist = loc_name_meta.split("|")
            header = f"📍 Brak stacji w: **{query.title()}**.\n📏 Najbliższa: **{st_name}** ({dist} km).\n\n"
        
        icon = get_weather_icon(data)
        lines = [
            format_line("Temp", data.get('temperatura'), "°C"),
            format_line("Wiatr", data.get('predkosc_wiatru'), "m/s"),
            format_line("Opad", data.get('suma_opadu'), "mm"),
            format_line("Ciśnienie", data.get('cisnienie'), "hPa")
        ]
        return f"{header}{icon} **Pogoda: {data.get('stacja')}**\n" + "\n".join(filter(None, lines))

    def _format_hydro(self, data):
        station = data[0] if isinstance(data, list) and data else data
        if not station: return "Brak danych hydro."
        lines = [
            format_line("Poziom", station.get('stan_wody'), "cm"),
            format_line("Status", format_hydro_status(station.get('przekroczenia'))),
            format_line("Trend", format_trend(station.get('tendencja')))
        ]
        return f"🌊 **{station.get('rzeka')}** ({station.get('stacja')})\n" + "\n".join(filter(None, lines))

    def _format_warnings(self, all_warnings, loc_id, loc_name):
        pretty_name = self.terc_id_to_name.get(loc_id, loc_name.title())
        found = [f"⚠️ {w.get('zjawisko')} (st. {w.get('stopien')})" for w in all_warnings if loc_id in w.get('powiaty_kod', [])]
        if found: return f"🚨 **Ostrzeżenia: {pretty_name}**\n" + "\n".join(found)
        return f"✅ Brak ostrzeżeń dla: {pretty_name}."