import { useState } from "react";
import { MessageSquare, Send, X } from "lucide-react";
import { Button } from "../../ui/Button";
import { Input } from "../../ui/Input";
import type { ChatMessage } from "../run/useRun";

export interface RefineBoxProps {
  chatHistory: ChatMessage[];
  chatLoading: boolean;
  onSendMessage: (message: string) => void;
}

export function RefineBox({ chatHistory, chatLoading, onSendMessage }: RefineBoxProps) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || chatLoading) return;
    onSendMessage(input.trim());
    setInput("");
  };

  if (!open && chatHistory.length === 0) {
    return (
      <div className="pt-2">
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 text-sm text-accent hover:text-accent/80 font-semibold transition-colors cursor-pointer py-1"
        >
          <MessageSquare className="w-4 h-4" />
          <span>Refine results with AI...</span>
        </button>
      </div>
    );
  }

  return (
    <div className="border border-border rounded-input bg-surface p-4 space-y-3.5">
      <div className="flex items-center justify-between border-b border-border pb-2.5">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-accent" />
          <span className="text-sm font-bold text-text">Refine Results with AI</span>
        </div>
        {chatHistory.length === 0 && (
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="text-text-muted hover:text-text cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* History */}
      {chatHistory.length > 0 && (
        <div className="space-y-2.5 max-h-56 overflow-y-auto text-sm pr-1">
          {chatHistory.map((msg, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-md ${
                msg.role === "user"
                  ? "bg-accent-soft text-accent ml-6"
                  : "bg-surface-2 text-text mr-6"
              }`}
            >
              <span className="font-semibold block text-xs uppercase opacity-75 mb-1">
                {msg.role === "user" ? "You" : "Analyst"}
              </span>
              <p className="leading-relaxed text-sm font-medium">{msg.content}</p>
            </div>
          ))}
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex gap-2.5">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. Focus Amazon title on heavy fabric, remove oversized from Myntra..."
          disabled={chatLoading}
          className="text-sm"
        />
        <Button
          type="submit"
          variant="primary"
          size="sm"
          loading={chatLoading}
          disabled={!input.trim()}
          className="shrink-0 gap-1.5 px-4 text-sm font-semibold"
        >
          <Send className="w-4 h-4" />
          <span>Send</span>
        </Button>
      </form>
    </div>
  );
}
