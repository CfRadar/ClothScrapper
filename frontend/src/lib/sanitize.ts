const CONTROL_AND_ZERO_WIDTH_REGEX =
  /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200d\ufeff]/g;

const ALLOWLISTED_HOSTS = new Set([
  "amazon.in",
  "www.amazon.in",
  "completion.amazon.in",
  "myntra.com",
  "www.myntra.com",
  "flipkart.com",
  "www.flipkart.com",
  "meesho.com",
  "www.meesho.com",
  "reddit.com",
  "www.reddit.com",
  "openrouter.ai",
]);

export function cleanText(input: string | null | undefined): string {
  if (!input) return "";
  return input.replace(CONTROL_AND_ZERO_WIDTH_REGEX, "").trim();
}

export function isAllowlistedLink(urlStr: string): boolean {
  try {
    const url = new URL(urlStr);
    if (url.protocol !== "https:") {
      return false;
    }
    return ALLOWLISTED_HOSTS.has(url.hostname.toLowerCase());
  } catch {
    return false;
  }
}
