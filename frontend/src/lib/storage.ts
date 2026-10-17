import { ProductBriefSchema, RunResultSchema } from "./schemas";
import type { ProductBrief, RunResult } from "../types";

const BRIEF_KEY = "mka.brief.v1";
const THEME_KEY = "mka.theme.v1";
const LAST_RUN_KEY = "mka.last_run.v1";

export function loadBriefFromStorage(): ProductBrief | null {
  try {
    const raw = sessionStorage.getItem(BRIEF_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    const validated = ProductBriefSchema.safeParse(parsed);
    if (validated.success) {
      return validated.data as ProductBrief;
    }
  } catch {
    // Ignored
  }
  return null;
}

export function saveBriefToStorage(brief: ProductBrief): void {
  try {
    sessionStorage.setItem(BRIEF_KEY, JSON.stringify(brief));
  } catch {
    // Ignored
  }
}

export function loadLastRunFromStorage(): { runId: string; runToken: string; result: RunResult } | null {
  try {
    const raw = sessionStorage.getItem(LAST_RUN_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.runId === "string" && typeof parsed.runToken === "string") {
      const validated = RunResultSchema.safeParse(parsed.result);
      if (validated.success) {
        return {
          runId: parsed.runId,
          runToken: parsed.runToken,
          result: validated.data as RunResult,
        };
      }
    }
  } catch {
    // Ignored
  }
  return null;
}

export function saveLastRunToStorage(data: { runId: string; runToken: string; result: RunResult }): void {
  try {
    sessionStorage.setItem(LAST_RUN_KEY, JSON.stringify(data));
  } catch {
    // Ignored
  }
}

export function clearLastRunStorage(): void {
  try {
    sessionStorage.removeItem(LAST_RUN_KEY);
  } catch {
    // Ignored
  }
}

export function loadThemeFromStorage(): "light" | "dark" | "system" {
  try {
    const raw = localStorage.getItem(THEME_KEY);
    if (raw === "light" || raw === "dark" || raw === "system") {
      return raw;
    }
  } catch {
    // Ignored
  }
  return "system";
}

export function saveThemeToStorage(theme: "light" | "dark" | "system"): void {
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // Ignored
  }
}
