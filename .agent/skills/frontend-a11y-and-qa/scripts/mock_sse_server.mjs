#!/usr/bin/env node
/**
 * Standalone Mock SSE Server for Marketplace Keyword Agent Frontend QA.
 * Replays realistic event fixtures from event-fixtures.json with timestamps.
 * 
 * Usage: node mock_sse_server.mjs [port] [scenario]
 * Scenarios: happy_path_run (default) | blocked_platform_run | cancelled_run
 */

import http from "http";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = parseInt(process.argv[2], 10) || 8000;
const SCENARIO = process.argv[3] || "happy_path_run";

const fixturesPath = path.resolve(__dirname, "../../agent-run-visualization/examples/event-fixtures.json");

if (!fs.existsSync(fixturesPath)) {
  console.error(`[ERROR] Event fixtures file not found at: ${fixturesPath}`);
  process.exit(1);
}

const fixtures = JSON.parse(fs.readFileSync(fixturesPath, "utf-8"));
const events = fixtures[SCENARIO] || fixtures["happy_path_run"];

console.log(`[mock_sse_server] Loaded scenario: "${SCENARIO}" (${events.length} events)`);

const server = http.createServer((req, res) => {
  // CORS Headers
  res.setHeader("Access-Control-Allow-Origin", "http://localhost:5173");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Run-Token");

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://localhost:${PORT}`);

  // Health
  if (url.pathname === "/api/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true, mock: true }));
    return;
  }

  // Quota
  if (url.pathname === "/api/quota") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ remaining_today: 42, daily_limit: 45, rpm_limit: 16 }));
    return;
  }

  // POST /api/runs
  if (url.pathname === "/api/runs" && req.method === "POST") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      const mockRunId = "mock-run-" + Date.now();
      console.log(`[mock_sse_server] Created mock run: ${mockRunId}`);
      res.writeHead(201, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ run_id: mockRunId }));
    });
    return;
  }

  // GET /api/runs/:id/events (SSE Stream)
  if (url.pathname.includes("/events") && req.method === "GET") {
    console.log(`[mock_sse_server] Client connected to SSE stream: ${url.pathname}`);
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    });

    let index = 0;
    const startTime = Date.now();
    const firstEventTs = events[0]?.ts || 0;

    const interval = setInterval(() => {
      if (index >= events.length) {
        clearInterval(interval);
        console.log(`[mock_sse_server] All ${events.length} events streamed.`);
        res.end();
        return;
      }

      const evt = events[index];
      const payload = {
        ...evt,
        ts: Date.now() / 1000,
      };

      res.write(`data: ${JSON.stringify(payload)}\n\n`);
      console.log(`[mock_sse_server] Emitted [${evt.type}] ${evt.message || ""}`);
      index++;
    }, 600); // Emits an event every 600ms for realistic pacing

    req.on("close", () => {
      clearInterval(interval);
      console.log("[mock_sse_server] Client disconnected from SSE stream.");
    });
    return;
  }

  // Fallback 404
  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ detail: "Not found" }));
});

server.listen(PORT, () => {
  console.log(`[mock_sse_server] Mock API & SSE server listening on http://localhost:${PORT}`);
  console.log(`[mock_sse_server] Endpoints: /api/health, /api/quota, /api/runs, /api/runs/:id/events`);
});
