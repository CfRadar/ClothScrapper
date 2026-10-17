import type {
  ChatResponse,
  PreflightResponse,
  ProductBrief,
  RunResult,
} from "../types";

const API_BASE = "";

export class APIError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = "APIError";
    this.status = status;
    this.data = data;
  }
}

export async function createRun(
  brief: ProductBrief
): Promise<{ run_id: string; run_token: string }> {
  const resp = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(brief),
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new APIError(
      errorData.detail || errorData.error || "Failed to initiate workflow run.",
      resp.status,
      errorData
    );
  }

  return resp.json();
}

export async function getRun(
  runId: string,
  runToken: string
): Promise<RunResult | { run_id: string; status: string; nodes_snapshot?: any }> {
  const resp = await fetch(`${API_BASE}/api/runs/${encodeURIComponent(runId)}`, {
    headers: {
      "X-Run-Token": runToken,
    },
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new APIError(
      errorData.detail || "Failed to load run data.",
      resp.status,
      errorData
    );
  }

  return resp.json();
}

export async function cancelRun(
  runId: string,
  runToken: string
): Promise<{ run_id: string; cancelled: boolean }> {
  const resp = await fetch(
    `${API_BASE}/api/runs/${encodeURIComponent(runId)}/cancel`,
    {
      method: "POST",
      headers: {
        "X-Run-Token": runToken,
      },
    }
  );

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new APIError(
      errorData.detail || "Failed to cancel run.",
      resp.status,
      errorData
    );
  }

  return resp.json();
}

export async function sendChat(
  runId: string,
  runToken: string,
  message: string
): Promise<ChatResponse> {
  const resp = await fetch(
    `${API_BASE}/api/runs/${encodeURIComponent(runId)}/chat`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Run-Token": runToken,
      },
      body: JSON.stringify({ message }),
    }
  );

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new APIError(
      errorData.detail || "Failed to send chat message.",
      resp.status,
      errorData
    );
  }

  return resp.json();
}

export async function getQuota(): Promise<{
  remaining_today: number;
  daily_limit: number;
  rpm_limit: number;
  active_model: string;
}> {
  const resp = await fetch(`${API_BASE}/api/quota`);
  if (!resp.ok) {
    throw new APIError("Failed to fetch quota.", resp.status);
  }
  return resp.json();
}

export async function getPreflight(): Promise<PreflightResponse> {
  const resp = await fetch(`${API_BASE}/api/system/preflight`);
  if (!resp.ok) {
    throw new APIError("Failed to fetch security preflight.", resp.status);
  }
  return resp.json();
}
