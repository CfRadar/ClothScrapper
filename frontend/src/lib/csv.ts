import type { PlatformResult } from "../types";

export function escapeCSVCell(value: string | number | undefined | null): string {
  if (value === null || value === undefined) {
    return '""';
  }
  let str = String(value);

  // Formula injection defense: prefix dangerous leading characters with a single quote
  const dangerousPrefixes = ["=", "+", "-", "@", "\t", "\r"];
  if (dangerousPrefixes.some((p) => str.startsWith(p))) {
    str = "'" + str;
  }

  // Escape inner double quotes
  const escaped = str.replace(/"/g, '""');
  return `"${escaped}"`;
}

function downloadCSV(csvContent: string, filename: string): void {
  const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function exportKeywordsToCSV(platforms: PlatformResult[], filename = "keywords.csv"): void {
  const rows: string[][] = [["Platform", "Rank", "Keyword"]];

  for (const plat of platforms) {
    plat.keywords.forEach((kw, idx) => {
      rows.push([plat.platform, String(idx + 1), kw]);
    });
  }

  const csvContent = rows
    .map((row) => row.map((cell) => escapeCSVCell(cell)).join(","))
    .join("\r\n");

  downloadCSV(csvContent, filename);
}

export function exportTitlesToCSV(platforms: PlatformResult[], filename = "titles.csv"): void {
  const rows: string[][] = [["Platform", "Style", "Length", "Title"]];

  for (const plat of platforms) {
    for (const title of plat.titles || []) {
      rows.push([plat.platform, title.style, String(title.length), title.title]);
    }
  }

  const csvContent = rows
    .map((row) => row.map((cell) => escapeCSVCell(cell)).join(","))
    .join("\r\n");

  downloadCSV(csvContent, filename);
}

export function exportTopScrapedTitlesToCSV(
  platforms: PlatformResult[],
  filename = "scraped_competitor_titles.csv"
): void {
  const rows: string[][] = [
    ["Platform", "Search Rank", "Length", "Brand", "Price", "Rating", "Title"],
  ];

  for (const plat of platforms) {
    for (const comp of plat.top_scraped_titles || []) {
      rows.push([
        plat.platform,
        `#${comp.rank}`,
        String(comp.length),
        comp.brand || "",
        comp.price ? String(comp.price) : "",
        comp.rating ? String(comp.rating) : "",
        comp.title,
      ]);
    }
  }

  const csvContent = rows
    .map((row) => row.map((cell) => escapeCSVCell(cell)).join(","))
    .join("\r\n");

  downloadCSV(csvContent, filename);
}

export function exportAllToCSV(platforms: PlatformResult[], filename = "ecommerce_seo.csv"): void {
  const rows: string[][] = [["Section", "Platform", "Identifier", "Content"]];

  for (const plat of platforms) {
    for (const title of plat.titles || []) {
      rows.push(["Exact Title", plat.platform, `${title.style} (${title.length} chars)`, title.title]);
    }
    for (const comp of plat.top_scraped_titles || []) {
      rows.push([
        "Scraped Top Title",
        plat.platform,
        `#${comp.rank} (${comp.length} chars)${comp.brand ? ` [${comp.brand}]` : ""}`,
        comp.title,
      ]);
    }
    plat.keywords.forEach((kw, idx) => {
      rows.push(["Keyword", plat.platform, `#${idx + 1}`, kw]);
    });
    if (plat.details) {
      if (plat.details.price_band) {
        rows.push(["Details", plat.platform, "Price Band", plat.details.price_band]);
      }
      if (plat.details.negative_keywords?.length) {
        rows.push(["Details", plat.platform, "Negative Keywords", plat.details.negative_keywords.join(", ")]);
      }
      if (plat.details.competition_note) {
        rows.push(["Details", plat.platform, "Competition", plat.details.competition_note]);
      }
      if (plat.details.seasonality_note) {
        rows.push(["Details", plat.platform, "Seasonality", plat.details.seasonality_note]);
      }
    }
  }

  const csvContent = rows
    .map((row) => row.map((cell) => escapeCSVCell(cell)).join(","))
    .join("\r\n");

  downloadCSV(csvContent, filename);
}
