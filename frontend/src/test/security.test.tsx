import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { escapeCSVCell } from "../lib/csv";
import { isAllowlistedLink } from "../lib/sanitize";
import { loadBriefFromStorage, loadLastRunFromStorage } from "../lib/storage";
import { Chip } from "../ui/Chip";

describe("Frontend Security Controls", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it("renders keywords containing malicious script/html payload as plain text", () => {
    const maliciousPayload = '<img src=x onerror=alert(1)>';
    render(<Chip data-testid="chip">{maliciousPayload}</Chip>);

    const chipEl = screen.getByTestId("chip");
    expect(chipEl.textContent).toBe(maliciousPayload);
    // Ensure no actual img element was created in the DOM
    const imgEl = chipEl.querySelector("img");
    expect(imgEl).toBeNull();
  });

  it("prefixes dangerous CSV cells starting with =, +, -, @ to prevent formula injection", () => {
    expect(escapeCSVCell("=cmd|'/C calc'!A0")).toBe("\"'=cmd|'/C calc'!A0\"");
    expect(escapeCSVCell("+1+2")).toBe("\"'+1+2\"");
    expect(escapeCSVCell("-SUM(A1:A10)")).toBe("\"'-SUM(A1:A10)\"");
    expect(escapeCSVCell("@SUM(A1:A10)")).toBe("\"'@SUM(A1:A10)\"");
    expect(escapeCSVCell("\tTAB_INJECT")).toBe("\"'\tTAB_INJECT\"");
    expect(escapeCSVCell("Safe Keyword")).toBe('"Safe Keyword"');
  });

  it("safely ignores corrupted sessionStorage brief and run data without crashing", () => {
    // 1. Invalid JSON in brief
    sessionStorage.setItem("mka.brief.v1", "{bad json---");
    expect(loadBriefFromStorage()).toBeNull();

    // 2. Valid JSON with invalid schema in brief
    sessionStorage.setItem("mka.brief.v1", JSON.stringify({ platforms: ["invalid_plat_name"] }));
    expect(loadBriefFromStorage()).toBeNull();

    // 3. Valid JSON with correct brief schema
    sessionStorage.setItem(
      "mka.brief.v1",
      JSON.stringify({
        platforms: ["amazon"],
        tshirt_type: "oversized graphic tee",
        color: "black",
        gender: "unisex",
      })
    );
    const loadedBrief = loadBriefFromStorage();
    expect(loadedBrief).not.toBeNull();
    expect(loadedBrief?.tshirt_type).toBe("oversized graphic tee");

    // 4. Invalid run data
    sessionStorage.setItem("mka.last_run.v1", "{corrupted run---");
    expect(loadLastRunFromStorage()).toBeNull();
  });

  it("validates links against outbound allowlist and rejects javascript: schemes", () => {
    // Allowlisted Amazon, Myntra, Flipkart, Meesho HTTPS links
    expect(isAllowlistedLink("https://www.amazon.in/dp/B08XYZ")).toBe(true);
    expect(isAllowlistedLink("https://www.myntra.com/tshirts/brand")).toBe(true);
    expect(isAllowlistedLink("https://www.flipkart.com/tshirt/p/itm123")).toBe(true);
    expect(isAllowlistedLink("https://www.meesho.com/s/p/1234")).toBe(true);

    // Non-allowlisted external sites
    expect(isAllowlistedLink("https://attacker.com/steal")).toBe(false);
    expect(isAllowlistedLink("https://evilcorp.org")).toBe(false);

    // XSS / Malicious schemes
    expect(isAllowlistedLink("javascript:alert(1)")).toBe(false);
    expect(isAllowlistedLink("data:text/html,<script>alert(1)</script>")).toBe(false);
    expect(isAllowlistedLink("file:///etc/passwd")).toBe(false);
    expect(isAllowlistedLink("http://www.amazon.in/dp/123")).toBe(false); // Non-HTTPS
  });
});
