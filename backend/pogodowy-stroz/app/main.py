from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.models import ChatRequest, ChatResponse
from app.services.state_manager import get_or_create_fsm
# Opcjonalnie dla typowania:
# from app.logic.conversation import ChatbotLogic 

app = FastAPI(title="Pogodowy Stróż API")

# --- KONFIGURACJA CORS ---
# Niezbędne, aby frontend (Vite) mógł rozmawiać z backendem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ENDPOINTY ---

@app.get("/")
async def read_root_status():
    """Endpoint do sprawdzania statusu serwera."""
    return {"status": "Backend działa, CORS włączony"}

@app.post("/chat", response_model=ChatResponse)
async def handle_chat(request: ChatRequest):
    """
    Główny endpoint. Pobiera wiadomość i przekazuje ją do Maszyny Stanów (FSM).
    """
    
    # 1. Pobranie maszyny stanów dla danej sesji
    fsm = get_or_create_fsm(request.session_id)

    # 2. Przekazanie wiadomości do logiki konwersacyjnej
    # To wywołanie uruchamia NLP i (jeśli trzeba) pobiera dane z IMGW
    bot_response_text = await fsm.process_message(request.message)

    # 3. Zwrócenie odpowiedzi wygenerowanej przez bota
    return ChatResponse(
        response=bot_response_text,
        session_id=request.session_id
    )