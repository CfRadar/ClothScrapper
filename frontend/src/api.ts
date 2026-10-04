import type { ProductBrief, RunResult, ChatResponse, QuotaInfo, SSEEvent } from './types';

const API_BASE = '/api';

export async function createRun(brief: ProductBrief): Promise<{ run_id: string }> {
  const resp = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(brief),
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to start run (HTTP ${resp.status})`);
  }

  return resp.json();
}

export async function getRun(runId: string): Promise<RunResult | { run_id: string; status: string }> {
  const resp = await fetch(`${API_BASE}/runs/${runId}`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch run status (HTTP ${resp.status})`);
  }
  return resp.json();
}

export async function chat(runId: string, message: string): Promise<ChatResponse> {
  const resp = await fetch(`${API_BASE}/runs/${runId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new Error(errorData.detail || `Chat request failed (HTTP ${resp.status})`);
  }

  return resp.json();
}

export async function getQuota(): Promise<QuotaInfo> {
  const resp = await fetch(`${API_BASE}/quota`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch quota info (HTTP ${resp.status})`);
  }
  return resp.json();
}

export function streamEvents(
  runId: string,
  onEvent: (event: SSEEvent) => void,
  onError: (err: string) => void
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(`${API_BASE}/runs/${runId}/events`, {
        signal: controller.signal,
        headers: { Accept: 'text/event-stream' },
      });

      if (!response.ok) {
        throw new Error(`Event stream connection failed (HTTP ${response.status})`);
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported on response.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data:')) {
            const dataStr = trimmed.slice(5).trim();
            if (dataStr === 'keepalive') continue;
            try {
              const parsed: SSEEvent = JSON.parse(dataStr);
              onEvent(parsed);
            } catch {
              // Ignore partial JSON
            }
          }
        }
      }
    } catch (err: unknown) {
      if ((err as Error)?.name !== 'AbortError') {
        onError((err as Error)?.message || 'Stream disconnected.');
      }
    }
  })();

  return () => {
    controller.abort();
  };
}
