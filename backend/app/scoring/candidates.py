import os
import re

RESOURCE_DIR = os.path.join(os.path.dirname(__file__), "resources")


def load_stopwords() -> set[str]:
    path = os.path.join(RESOURCE_DIR, "stopwords.txt")
    if not os.path.exists(path):
        return {
            "buy",
            "online",
            "price",
            "best",
            "cheap",
            "for",
            "with",
            "in",
            "and",
            "the",
            "a",
            "an",
            "of",
        }
    with open(path, encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}


STOPWORDS = load_stopwords()


def normalize_text(text: str) -> str:
    """Normalize text: lowercase, remove special characters except hyphen, fold plurals."""
    lower = text.lower().strip()
    # Unify apparel terms for matching
    lower = re.sub(r"\bt\s+shirts?\b", "t-shirt", lower)
    lower = re.sub(r"\btshirts?\b", "t-shirt", lower)
    lower = re.sub(r"\btees?\b", "t-shirt", lower)
    # Remove unwanted punctuation
    cleaned = re.sub(r"[^\w\s-]", " ", lower)
    # Collapse whitespace
    return re.sub(r"\s+", " ", cleaned).strip()


def fold_plural(word: str) -> str:
    """Simple plural folding for apparel keywords."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def extract_ngrams_from_string(text: str, n_min: int = 1, n_max: int = 4) -> list[str]:
    """Extract contiguous 1-4 word spans from a normalized string."""
    tokens = [t for t in text.split(" ") if t and not t.isdigit() and len(t) >= 2]
    ngrams = []
    length = len(tokens)
    for n in range(n_min, min(n_max + 1, length + 1)):
        for i in range(length - n + 1):
            chunk = tokens[i : i + n]
            # Avoid chunks starting or ending with stopwords
            if chunk[0] in STOPWORDS or chunk[-1] in STOPWORDS:
                continue
            phrase = " ".join(chunk)
            if len(phrase) >= 2:
                ngrams.append(phrase)
    return ngrams


def extract_candidates(
    product_titles: list[str],
    suggestions: list[str],
    related_searches: list[str],
    social_phrases: list[str],
) -> list[str]:
    """
    Extract and filter candidate n-grams.
    Keep n-grams appearing in >= 2 titles OR present in suggestions/related/social.
    """
    title_ngram_counts: dict[str, int] = {}
    external_candidates: set[str] = set()

    # 1. External high-intent sources (autosuggest, related, social)
    for s in suggestions + related_searches + social_phrases:
        norm = normalize_text(s)
        external_candidates.add(norm)
        for ng in extract_ngrams_from_string(norm, 1, 4):
            external_candidates.add(ng)

    # 2. Extract from titles
    for title in product_titles:
        norm_title = normalize_text(title)
        seen_in_this_title = set(extract_ngrams_from_string(norm_title, 1, 4))
        for ng in seen_in_this_title:
            title_ngram_counts[ng] = title_ngram_counts.get(ng, 0) + 1

    final_candidates: set[str] = set()

    # Keep n-grams appearing in >= 2 titles
    for ng, count in title_ngram_counts.items():
        if count >= 2:
            final_candidates.add(ng)

    # Always keep external candidates that match token quality
    for ec in external_candidates:
        if ec and len(ec) >= 2 and not ec.isdigit():
            final_candidates.add(ec)

    return sorted(list(final_candidates))
