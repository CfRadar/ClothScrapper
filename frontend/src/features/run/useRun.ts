import { useCallback, useEffect, useRef, useState } from "react";
import { cancelRun, createRun, sendChat } from "../../lib/api";
import { SSEConnectionOptions, connectSSE } from "../../lib/sse";
import {
  clearLastRunStorage,
  loadLastRunFromStorage,
  saveLastRunToStorage,
} from "../../lib/storage";
import type {
  ProductBrief,
  RunResult,
  SSEEvent,
} from "../../types";

export type RunStatus = "idle" | "running" | "done" | "error" | "cancelled";
export type StepStatus = "pending" | "running" | "done" | "error";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface UseRunReturn {
  status: RunStatus;
  runId: string | null;
  runToken: string | null;
  result: RunResult | null;
  error: string | null;
  activeMessage: string;
  stepStatuses: Record<1 | 2 | 3 | 4, StepStatus>;
  chatHistory: ChatMessage[];
  chatLoading: boolean;
  startRun: (brief: ProductBrief) => Promise<void>;
  stopRun: () => Promise<void>;
  sendChatMessage: (message: string) => Promise<void>;
  reset: () => void;
}

const INITIAL_STEPS: Record<1 | 2 | 3 | 4, StepStatus> = {
  1: "pending",
  2: "pending",
  3: "pending",
  4: "pending",
};

export function useRun(): UseRunReturn {
  const initialCache = loadLastRunFromStorage();

  const [status, setStatus] = useState<RunStatus>(initialCache ? "done" : "idle");
  const [runId, setRunId] = useState<string | null>(initialCache?.runId || null);
  const [runToken, setRunToken] = useState<string | null>(initialCache?.runToken || null);
  const [result, setResult] = useState<RunResult | null>(initialCache?.result || null);
  const [error, setError] = useState<string | null>(null);
  const [activeMessage, setActiveMessage] = useState<string>(
    initialCache ? "Loaded previous run from session." : ""
  );
  const [stepStatuses, setStepStatuses] = useState<Record<1 | 2 | 3 | 4, StepStatus>>(
    initialCache
      ? { 1: "done", 2: "done", 3: "done", 4: "done" }
      : INITIAL_STEPS
  );
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState<boolean>(false);

  const disconnectRef = useRef<(() => void) | null>(null);
  const resultRef = useRef<RunResult | null>(result);

  useEffect(() => {
    resultRef.current = result;
  }, [result]);

  const cleanupSSE = useCallback(() => {
    if (disconnectRef.current) {
      disconnectRef.current();
      disconnectRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    cleanupSSE();
    setStatus("idle");
    setRunId(null);
    setRunToken(null);
    setResult(null);
    setError(null);
    setActiveMessage("");
    setStepStatuses(INITIAL_STEPS);
    setChatHistory([]);
    setChatLoading(false);
    clearLastRunStorage();
  }, [cleanupSSE]);

  const stopRun = useCallback(async () => {
    if (runId && runToken && status === "running") {
      cleanupSSE();
      try {
        await cancelRun(runId, runToken);
      } catch {
        // Ignored
      }
      setStatus("cancelled");
      setActiveMessage("Generation was stopped.");
      setStepStatuses((prev) => {
        const next = { ...prev };
        for (const k of [1, 2, 3, 4] as const) {
          if (next[k] === "running" || next[k] === "pending") {
            next[k] = "pending";
          }
        }
        return next;
      });
    }
  }, [runId, runToken, status, cleanupSSE]);

  const startRun = useCallback(
    async (brief: ProductBrief) => {
      cleanupSSE();
      setStatus("running");
      setError(null);
      setResult(null);
      setChatHistory([]);
      setActiveMessage("Initializing research pipeline...");
      setStepStatuses({
        1: "running",
        2: "pending",
        3: "pending",
        4: "pending",
      });

      let newRunId = "";
      let newRunToken = "";

      try {
        const runData = await createRun(brief);
        newRunId = runData.run_id;
        newRunToken = runData.run_token;
        setRunId(newRunId);
        setRunToken(newRunToken);
      } catch (err: any) {
        setStatus("error");
        setError(err.message || "Failed to start pipeline run.");
        setStepStatuses((prev) => ({ ...prev, 1: "error" }));
        return;
      }

      const sseOpts: SSEConnectionOptions = {
        runId: newRunId,
        runToken: newRunToken,
        onEvent: (event: SSEEvent | any) => {
          if (event.type === "stage" || event.type === "progress") {
            const stage = event.stage;
            if (event.message) {
              setActiveMessage(event.message);
            }

            setStepStatuses((prev) => {
              const next = { ...prev };
              if (stage === "planner") {
                next[1] = "running";
              } else if (stage === "marketplace") {
                next[1] = "done";
                next[2] = "running";
              } else if (stage === "social") {
                next[2] = "running";
                next[3] = "running";
              } else if (stage === "analyst") {
                next[1] = "done";
                next[2] = "done";
                next[3] = "done";
                next[4] = "running";
              }
              return next;
            });
          } else if (event.type === "result") {
            if (event.data) {
              const res = event.data as RunResult;
              setResult(res);
              resultRef.current = res;
            }
          } else if (event.type === "done") {
            setStatus("done");
            setStepStatuses({ 1: "done", 2: "done", 3: "done", 4: "done" });
            setActiveMessage("Analysis and title generation completed.");
            if (resultRef.current) {
              saveLastRunToStorage({
                runId: newRunId,
                runToken: newRunToken,
                result: resultRef.current,
              });
            }
            cleanupSSE();
          } else if (event.type === "error") {
            setStatus("error");
            setError(event.message || "An error occurred during pipeline execution.");
            cleanupSSE();
          }
        },
        onError: (err: any) => {
          if (status !== "done") {
            setStatus("error");
            setError(err?.message || "Connection to pipeline server was lost.");
          }
          cleanupSSE();
        },
      };

      disconnectRef.current = connectSSE(sseOpts);
    },
    [cleanupSSE, status]
  );

  const sendChatMessage = useCallback(
    async (message: string) => {
      if (!runId || !runToken || !message.trim()) return;

      const trimmed = message.trim();
      setChatHistory((prev) => [...prev, { role: "user", content: trimmed }]);
      setChatLoading(true);

      try {
        const response = await sendChat(runId, runToken, trimmed);
        setChatHistory((prev) => [
          ...prev,
          { role: "assistant", content: response.reply },
        ]);

        if (response.patch && response.patch.length > 0 && resultRef.current) {
          const patchMap = new Map(response.patch.map((p) => [p.platform, p]));
          const updatedPlatforms = resultRef.current.platforms.map((plat) => {
            if (patchMap.has(plat.platform)) {
              return patchMap.get(plat.platform)!;
            }
            return plat;
          });

          const updatedResult: RunResult = {
            ...resultRef.current,
            platforms: updatedPlatforms,
          };

          setResult(updatedResult);
          saveLastRunToStorage({
            runId,
            runToken,
            result: updatedResult,
          });
        }
      } catch (err: any) {
        setChatHistory((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Failed to process request: ${err.message || "Unknown error"}`,
          },
        ]);
      } finally {
        setChatLoading(false);
      }
    },
    [runId, runToken]
  );

  return {
    status,
    runId,
    runToken,
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
  };
}
