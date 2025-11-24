# backend/app/logic/nlp.py
import spacy
import re

# SŁOWA KLUCZOWE
STRONG_KEYWORDS = {
    'pogoda': ['pogoda', 'pogodę', 'pogody', 'temperatura', 'stopni', 'ciśnienie', 'wiatr', 'prognoza', 'zimno', 'ciepło', 'meteo'],
    'ostrzeżenia': ['ostrzeżenie', 'ostrzeżenia', 'alert', 'alerty', 'zagrożenie', 'burza', 'burze', 'grad', 'wiatry', 'rcb'],
    'hydro': ['woda', 'wody', 'rzeka', 'rzeki', 'stan', 'poziom', 'hydrologiczne', 'wyleje', 'powódź', 'wodowskaz', 'cm']
}

try:
    nlp = spacy.load("pl_core_news_sm")
except OSError:
    print("WARNING: Model spaCy nie znaleziony. Działam w trybie uproszczonym.")
    nlp = None

def sanitize_text(text: str) -> str:
    """
    Czyści tekst, ale ZOSTAWIA polskie znaki.
    Ważne dla Geocodera: 'Łódź' nie może stać się 'Lodz' na tym etapie.
    """
    if not text: return ""
    # Zostawiamy litery (w tym PL), cyfry i spacje. Reszta out.
    text = re.sub(r'[^\w\sęóąśłżźćńĘÓĄŚŁŻŹĆŃ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def recognize_intent(text: str) -> str | None:
    text_lower = text.lower()
    
    # 1. Proste słowa kluczowe
    for intent, keywords in STRONG_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return intent
    
    # 2. Lematyzacja (jeśli spaCy działa)
    if nlp:
        doc = nlp(text_lower)
        lemmas = {token.lemma_ for token in doc}
        for intent, keywords in STRONG_KEYWORDS.items():
            if any(kw in lemmas for kw in keywords):
                return intent
    return None

def extract_entities(text: str) -> dict[str, list[str]]:
    locations = {'placeName': [], 'geogName': []}
    if not nlp: return locations
    
    doc = nlp(text)
    
    # 1. Standardowe encje
    for ent in doc.ents:
        clean_lemma = ent.lemma_.replace('.', '').strip()
        if ent.label_ == 'placeName':
            locations['placeName'].append(clean_lemma)
        elif ent.label_ == 'geogName':
            locations['geogName'].append(clean_lemma)
            
    # 2. Fallback: Nazwy własne (PROPN)
    # To jest kluczowe dla "Skrzynic" i innych wiosek, których model nie zna jako "Miasto".
    existing = set(locations['placeName'] + locations['geogName'])
    for token in doc:
        if token.pos_ == 'PROPN' and len(token.text) > 2:
            lemma = token.lemma_.lower() # Tu normalizujemy do lower, DataService sobie poradzi
            if lemma not in existing:
                locations['placeName'].append(lemma)

    return locations