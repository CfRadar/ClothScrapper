import type { NodeEvent, SSEEvent } from "../types";

export interface SSEConnectionOptions {
  runId: string;
  runToken: string;
  onEvent: (event: SSEEvent | NodeEvent) => void;
  onError?: (err: any) => void;
  onDone?: () => void;
}

export function connectSSE(options: SSEConnectionOptions): () => void {
  const { runId, runToken, onEvent, onError, onDone } = options;
  const abortController = new AbortController();
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 3;
  let lastEventId: number | null = null;
  let isClosed = false;

  async function startStream() {
    if (isClosed || abortController.signal.aborted) return;

    try {
      const headers: Record<string, string> = {
        "X-Run-Token": runToken,
      };
      if (lastEventId !== null) {
        headers["Last-Event-ID"] = String(lastEventId);
      }

      const response = await fetch(`/api/runs/${encodeURIComponent(runId)}/events`, {
        headers,
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`SSE stream failed with status ${response.status}`);
      }

      if (!response.body) {
        throw new Error("No response body available for SSE streaming.");
      }

      reconnectAttempts = 0; // Reset counter on successful connection
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (!isClosed && !abortController.signal.aborted) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() || "";

        for (const block of blocks) {
          const lines = block.split(/\r?\n/);
          let eventType = "message";
          let dataStr = "";
          let blockId: string | null = null;

          for (const line of lines) {
            if (line.startsWith("event:")) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith("id:")) {
              blockId = line.slice(3).trim();
            } else if (line.startsWith("data:")) {
              dataStr += line.slice(5).trim();
            }
          }

          if (blockId) {
            const parsedId = parseInt(blockId, 10);
            if (!isNaN(parsedId)) {
              lastEventId = parsedId;
            }
          }

          if (eventType === "message" && dataStr) {
            try {
              const parsed = JSON.parse(dataStr);
              onEvent(parsed);
              if (parsed.type === "done") {
                isClosed = true;
                if (onDone) onDone();
                return;
              }
              if (parsed.type === "error") {
                isClosed = true;
                if (onError) onError(new Error(parsed.message || "Pipeline error"));
                return;
              }
            } catch {
              // Ignore JSON parse errors for keepalives
            }
          }
        }
      }
    } catch (err: any) {
      if (abortController.signal.aborted || isClosed) return;

      if (reconnectAttempts < maxReconnectAttempts) {
        const delay = Math.pow(2, reconnectAttempts) * 1000; // 1s, 2s, 4s
        reconnectAttempts++;
        setTimeout(() => {
          if (!abortController.signal.aborted && !isClosed) {
            startStream();
          }
        }, delay);
      } else {
        isClosed = true;
        if (onError) onError(err);
      }
    }
  }

  startStream();

  return () => {
    isClosed = true;
    abortController.abort();
  };
}
