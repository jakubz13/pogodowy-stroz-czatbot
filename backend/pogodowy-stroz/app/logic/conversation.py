# backend/app/logic/conversation.py
from transitions.extensions.asyncio import AsyncMachine
from app.logic.nlp import recognize_intent, extract_entities, sanitize_text
from app.services.data_service import DataService

try:
    GLOBAL_DATA_SERVICE = DataService()
except:
    GLOBAL_DATA_SERVICE = None

class ChatbotLogic:
    def __init__(self, session_id):
        self.session_id = session_id
        self.data_service = GLOBAL_DATA_SERVICE
        self.current_intent = None
        self.current_location_id = None
        self.last_city_context = None 
        self.resolved_loc_name = None 
        self.retry_count = 0 
        self.max_retries = 2
        self.response = ""
        self.processing_result = None

        states = ['initial', 'awaiting_location', 'processing']
        self.machine = AsyncMachine(model=self, states=states, initial='initial')

        self.machine.add_transition('trigger_intent', 'initial', 'processing', conditions='_has_valid_location', after='_trigger_data_processing')
        self.machine.add_transition('trigger_intent', 'initial', 'awaiting_location', conditions='_is_location_missing', after='_ask_for_location')
        self.machine.add_transition('trigger_location', 'awaiting_location', 'processing', conditions='_has_valid_location', after='_trigger_data_processing')
        self.machine.add_transition('trigger_location', 'awaiting_location', 'awaiting_location', conditions='_is_location_missing', after='_handle_invalid_location')
        self.machine.add_transition('data_processed', 'processing', 'initial', after='_format_response')
        self.machine.add_transition('error_occurred', 'processing', 'initial', after='_format_error')

    async def process_message(self, text: str) -> str:
        if not self.data_service: return "Błąd serwisu."
        clean_text = sanitize_text(text)
        entities = extract_entities(clean_text)
        new_intent = recognize_intent(clean_text)
        
        if new_intent: self.current_intent = new_intent
        
        if not self.current_intent and self.state == 'initial':
             return "W czym pomóc? (Pogoda, Hydro, Ostrzeżenia)"

        # Walidacja
        loc_id, final_intent, loc_name = self.data_service.validate_and_get_id(
            entities, 
            self.current_intent, 
            original_text=clean_text,
            city_context=self.last_city_context 
        )

        if final_intent: self.current_intent = final_intent
        
        if loc_id:
            # SUKCES
            self.retry_count = 0 
            self.current_location_id = loc_id
            self.resolved_loc_name = loc_name
            
            # CONTEXT OVERRIDE: Zapisz miasto w sesji
            if self.current_intent in ['pogoda', 'ostrzeżenia']:
                if "NEAREST|" not in loc_name:
                    self.last_city_context = loc_name
            
            if self.state == 'initial': await self.trigger('trigger_intent')
            else: await self.trigger('trigger_location')
        else:
            if self.state == 'initial' and new_intent:
                await self.trigger('trigger_intent')
            elif self.state == 'awaiting_location':
                await self.trigger('trigger_location') 

        return self.response

    def _has_valid_location(self): return self.current_location_id is not None
    def _is_location_missing(self): return self.current_location_id is None

    def _ask_for_location(self):
        self.retry_count = 0
        if self.current_intent == 'pogoda': self.response = "Podaj miasto."
        elif self.current_intent == 'hydro': self.response = "Jaka rzeka i miasto?"
        elif self.current_intent == 'ostrzeżenia': self.response = "Podaj powiat."

    def _handle_invalid_location(self):
        self.retry_count += 1
        if self.retry_count > self.max_retries:
            self.response = "Nie rozumiem. Spróbuj: 'Pogoda w Warszawie'."
            self.to_initial()
            self.current_intent = None
            self.retry_count = 0
        else:
            self.response = "Nie znalazłem takiej lokalizacji."

    async def _trigger_data_processing(self):
        try:
            res = await self.data_service.fetch_data(self.current_intent, self.current_location_id, self.resolved_loc_name)
            self.processing_result = res
            await self.trigger('data_processed')
        except Exception as e:
            self.processing_error = str(e)
            await self.trigger('error_occurred')

    def _format_response(self): self.response = self.processing_result; self.current_location_id = None
    def _format_error(self): self.response = "Wystąpił błąd systemu."; self.current_location_id = None