import { Button } from "@/components/ui/button";

interface QuickActionsProps {
  onQuickAction: (message: string) => void;
  disabled?: boolean;
}

const quickActions = [
  { label: "Pogoda w Warszawie", message: "Pogoda w Warszawie" },
  { label: "Ostrzeżenia Poznań", message: "Ostrzeżenia dla Poznania" },
  { label: "Stan wody Wisła", message: "Stan wody w Wiśle" },
];

export function QuickActions({ onQuickAction, disabled }: QuickActionsProps) {
  return (
    <div className="flex flex-wrap gap-2 px-4 pb-3">
      {quickActions.map((action) => (
        <Button
          key={action.label}
          variant="outline"
          size="sm"
          onClick={() => onQuickAction(action.message)}
          disabled={disabled}
          className="text-xs rounded-full bg-accent hover:bg-accent/80"
        >
          {action.label}
        </Button>
      ))}
    </div>
  );
}
