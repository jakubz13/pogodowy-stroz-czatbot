# 🌤️ Pogodowy Stróż - Czatbot IMGW

Inteligentny asystent pogodowy łączący dane z IMGW (Python/FastAPI) z nowoczesnym interfejsem (React/Vite).

## 📂 Struktura Projektu

* **Backend:** Python (FastAPI, spaCy, Geopy) - folder `backend`
* **Frontend:** React + TypeScript + Vite - folder `frontend/pogodowy-str-chat`

---

## ⚙️ INSTRUKCJA URUCHOMIENIA (Backend)

Wymagany Python 3.10+.

1.  **Przygotowanie środowiska:**
    Wejdź do folderu backendu:
    ```bash
    cd backend
    ```
    
    Utwórz i aktywuj wirtualne środowisko:
    ```bash
    python -m venv venv
    # Windows:
    .\venv\Scripts\activate
    # Mac/Linux:
    source venv/bin/activate
    ```

2.  **Instalacja zależności:**
    Będąc w folderze `pogodowy-stroz` (tam gdzie jest requirements.txt):
    ```bash
    pip install -r requirements.txt
    python -m spacy download pl_core_news_sm
    ```

   

3.  **Uruchomienie serwera:**
    Upewnij się, że jesteś w folderze `backend/pogodowy-stroz`:
    ```bash
    uvicorn app.main:app --reload
    ```
    Backend ruszy pod adresem: `http://127.0.0.1:8000`

---

## 🖥️ INSTRUKCJA URUCHOMIENIA (Frontend)

Wymagany Node.js oraz npm.

1.  **Wejdź do folderu aplikacji frontendowej:**
    Z głównego katalogu projektu:
    ```bash
    cd frontend/pogodowy-str-chat
    ```

2.  **Zainstaluj biblioteki:**
    ```bash
    npm install
    ```

3.  **Uruchom aplikację:**
    ```bash
    npm run dev
    ```
    Kliknij w link w terminalu (np. `http://localhost:5173`), aby otworzyć czatbota.