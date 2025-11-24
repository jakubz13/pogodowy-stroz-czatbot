export function TypingIndicator() {
  return (
    <div className="flex w-full mb-4 justify-start">
      <div className="bg-card text-card-foreground max-w-[80%] rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-muted rounded-full animate-bounce [animation-delay:-0.3s]"></div>
            <div className="w-2 h-2 bg-muted rounded-full animate-bounce [animation-delay:-0.15s]"></div>
            <div className="w-2 h-2 bg-muted rounded-full animate-bounce"></div>
          </div>
          <span className="text-xs text-muted-foreground">Pisze...</span>
        </div>
      </div>
    </div>
  );
}
