import { useWeatherChat } from "@/hooks/useWeatherChat";
import { MessageList } from "@/components/chat/MessageList";
import { ChatInput } from "@/components/chat/ChatInput";
import { QuickActions } from "@/components/chat/QuickActions";
import { Card } from "@/components/ui/card";
import { Shield } from "lucide-react";
import weatherShield from "@/assets/weather-shield.png";

const Index = () => {
  const { messages, isLoading, sendMessage, messagesEndRef } = useWeatherChat();

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-b from-background to-accent/20">
      <div className="w-full max-w-2xl flex flex-col h-[90vh] max-h-[800px]">
        {/* Header */}
        <header className="text-center py-6 px-4">
          <div className="flex items-center justify-center gap-3 mb-2">
            <img 
              src={weatherShield} 
              alt="Weather Shield" 
              className="w-12 h-12 drop-shadow-lg"
            />
            <h1 className="text-3xl font-bold text-foreground">
              Pogodowy Stróż
            </h1>
          </div>
          <p className="text-sm text-muted-foreground">
            Twoje centrum informacji meteo i hydro
          </p>
        </header>

        {/* Chat Container */}
        <Card className="flex-1 flex flex-col overflow-hidden shadow-xl border-border/50">
          <MessageList 
            messages={messages} 
            isLoading={isLoading} 
            messagesEndRef={messagesEndRef}
          />
          <QuickActions 
            onQuickAction={sendMessage} 
            disabled={isLoading}
          />
          <ChatInput 
            onSend={sendMessage} 
            disabled={isLoading}
          />
        </Card>

        {/* Footer hint */}
        <p className="text-xs text-center text-muted-foreground/60 mt-4">
          Interfejs gotowy do połączenia z backendem Python
        </p>
      </div>
    </div>
  );
};

export default Index;
