import { useEffect, useState } from "react";
import { Moon, ShieldCheck, Sparkles, Sun } from "lucide-react";
import { BriefForm } from "../features/brief/BriefForm";
import { ResultsPanel } from "../features/results/ResultsPanel";
import { useRun } from "../features/run/useRun";
import { SystemCheckDialog } from "../features/system/SystemCheckDialog";
import { getQuota } from "../lib/api";
import { loadThemeFromStorage, saveThemeToStorage } from "../lib/storage";
import type { ProductBrief } from "../types";
import { TooltipProvider } from "../ui/Tooltip";
import { ErrorBoundary } from "./ErrorBoundary";

export default function App() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = loadThemeFromStorage();
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

  const [systemCheckOpen, setSystemCheckOpen] = useState(false);
  const [quota, setQuota] = useState<{
    remaining_today: number;
    daily_limit: number;
  } | null>(null);

  const {
    status,
    result,
    error,
    activeMessage,
    stepStatuses,
    chatHistory,
    chatLoading,
    startRun,
    stopRun,
    sendChatMessage,
    reset,
  } = useRun();

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    saveThemeToStorage(theme);
  }, [theme]);

  // Fetch daily LLM quota
  const fetchQuota = async () => {
    try {
      const q = await getQuota();
      setQuota({
        remaining_today: q.remaining_today,
        daily_limit: q.daily_limit,
      });
    } catch {
      // Ignored
    }
  };

  useEffect(() => {
    fetchQuota();
    const interval = setInterval(fetchQuota, 30000);
    return () => clearInterval(interval);
  }, []);

  const toggleTheme = () => {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  };

  const handleSelectSampleBrief = (sample: Partial<ProductBrief>) => {
    // Save to storage and dispatch event or reload
    const current = {
      platforms: ["amazon", "myntra", "flipkart", "meesho"],
      tshirt_type: "oversized graphic tee",
      color: "black",
      gender: "unisex",
      fit: "oversized",
      fabric: "100% cotton 240 GSM",
      neck: "round neck",
      sleeve: "half sleeve",
      pattern: "graphic print",
      occasion: "casual streetwear",
      pack: "single",
      size_range: "S to XXL",
      price_range: "₹499 - ₹899",
      brand_name: "",
      extra_details: "",
      ...sample,
    } as ProductBrief;

    sessionStorage.setItem("mka.brief.v1", JSON.stringify(current));
    window.location.reload();
  };

  return (
    <ErrorBoundary fallbackTitle="Application Error">
      <TooltipProvider delayDuration={200}>
        <div className="min-h-screen flex flex-col bg-bg text-text selection:bg-accent/20">
          {/* Header (56px) */}
          <header className="h-14 border-b border-border bg-surface/80 backdrop-blur sticky top-0 z-30 flex items-center justify-between px-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-input bg-accent flex items-center justify-center text-white shadow-sm">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h1 className="text-base font-bold tracking-tight text-text leading-none">
                  Keyword Agent
                </h1>
                <span className="text-xs text-text-muted mt-0.5 block">
                  Marketplace SEO & Title Engine
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {quota && (
                <div
                  className="hidden sm:inline-flex items-center gap-2 text-xs text-text-muted bg-surface-2 border border-border px-3 py-1 rounded-full font-mono font-medium"
                  title="Daily OpenRouter free tier token quota"
                >
                  <span className="w-2 h-2 rounded-full bg-success" />
                  <span>
                    Calls left: {quota.remaining_today} / {quota.daily_limit}
                  </span>
                </div>
              )}

              <button
                type="button"
                onClick={toggleTheme}
                className="w-8 h-8 rounded-input border border-border bg-surface hover:bg-surface-2 flex items-center justify-center text-text-muted hover:text-text transition-colors cursor-pointer"
                title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
                aria-label="Toggle theme"
              >
                {theme === "dark" ? (
                  <Sun className="w-4 h-4 text-warning" />
                ) : (
                  <Moon className="w-4 h-4 text-text-muted" />
                )}
              </button>
            </div>
          </header>

          {/* Main 2-column layout */}
          <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 flex flex-col lg:flex-row gap-6 items-start">
            {/* Left 400px sticky column */}
            <div className="w-full lg:w-[400px] shrink-0 lg:sticky lg:top-20">
              <BriefForm
                onGenerate={startRun}
                onStop={stopRun}
                isRunning={status === "running"}
              />
            </div>

            {/* Right flexible results column */}
            <div className="flex-1 w-full min-w-0">
              <ResultsPanel
                status={status}
                result={result}
                error={error}
                activeMessage={activeMessage}
                stepStatuses={stepStatuses}
                chatHistory={chatHistory}
                chatLoading={chatLoading}
                onStop={stopRun}
                onReset={reset}
                onSendMessage={sendChatMessage}
                onSelectSampleBrief={handleSelectSampleBrief}
              />
            </div>
          </main>

          {/* Footer */}
          <footer className="border-t border-border bg-surface/40 py-3 px-6 text-xs text-text-muted flex flex-col sm:flex-row items-center justify-between gap-2 mt-auto">
            <div className="flex items-center gap-1.5">
              <span>Marketplace Keyword Agent v2.0</span>
              <span>•</span>
              <span>Multi-marketplace T-shirt SEO</span>
            </div>

            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={() => setSystemCheckOpen(true)}
                className="flex items-center gap-1 text-text-muted hover:text-text hover:underline transition-colors cursor-pointer"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-accent" />
                <span>System check</span>
              </button>
            </div>
          </footer>

          {/* System Check Preflight Modal */}
          <SystemCheckDialog
            open={systemCheckOpen}
            onOpenChange={setSystemCheckOpen}
          />
        </div>
      </TooltipProvider>
    </ErrorBoundary>
  );
}
