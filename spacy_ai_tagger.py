
import re
from collections import Counter
import spacy

nlp = spacy.load("en_core_web_sm")
ruler = nlp.get_pipe("attribute_ruler")


STOP_BOUNDARIES = {
    "for", "with", "and", "in", "of", "to", "on", "a", "an", "the",
    "by", "pack", "pcs", "set", "piece", "pieces", "quality", "new", "best", "rechargeable"
}


def clean_title(text) -> str:
    """Remove special characters, digits, underscores, and normalize whitespace."""
    if not text or not isinstance(text, str):
        return ""
    text = text.replace("_", " ")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\d+", " ", text)
    return " ".join(text.lower().split())


def is_valid_phrase(phrase_tokens, min_words: int = 2, max_words: int = 4) -> bool:
    """Validate word count range and boundary noise."""
    if not (min_words <= len(phrase_tokens) <= max_words):
        return False

    if phrase_tokens[0] in STOP_BOUNDARIES or phrase_tokens[-1] in STOP_BOUNDARIES:
        return False

    return True


def is_valid_pos_sequence(tokens) -> bool:
    """Ensure tokens follow strictly [ADJ]* -> [NOUN/PROPN]+ order."""
    pos_tags = [t.pos_ for t in tokens]

    # Must contain only ADJ, NOUN, PROPN and strictly end in NOUN or PROPN
    if not (all(p in {"NOUN", "PROPN", "ADJ"} for p in pos_tags) and pos_tags[-1] in {"NOUN", "PROPN"}):
        return False

    # Prevent ADJ from appearing after a NOUN
    has_noun = False
    for p in pos_tags:
        if p in {"NOUN", "PROPN"}:
            has_noun = True
        elif p == "ADJ" and has_noun:
            return False

    return True

import spacy

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def extract_candidate_phrases(listings):
    if not listings or isinstance(listings, str):
        return []

    # Safely pull titles from valid dict items only
    titles = [
        item["Title"]
        for item in listings
        if isinstance(item, dict) and item.get("Title")
    ]

    if not titles:
        return []

    text_corpus = " ".join(titles)
    doc = nlp(text_corpus)

    phrases = []
    for chunk in doc.noun_chunks:
        clean_phrase = chunk.text.strip().lower()
        if len(clean_phrase) > 2 and not clean_phrase.isdigit():
            phrases.append(clean_phrase)

    return list(dict.fromkeys(phrases))
def _tokens_similar(t1: str, t2: str) -> bool:
    """Helper to match tokens considering plurals, stems, and minor typos."""
    if t1 == t2:
        return True
    # Strip common plural suffixes for short/medium words
    if t1.rstrip('s') == t2.rstrip('s'):
        return True
    # Prefix/stem match for words with at least 4 characters (e.g. luxuty/luxury)
    if len(t1) >= 4 and len(t2) >= 4 and t1[:4] == t2[:4]:
        return True
    return False




def _extract_raw_ngrams(titles: list, min_words=2, max_words=4) -> Counter:
    """Fallback n-gram extractor using simple regex tokenization."""
    counts = Counter()
    for item in titles:
        title_str = item.get("title", "") if isinstance(item, dict) else str(item)
        words = re.findall(r'\b[a-zA-Z]{2,}\b', title_str.lower())

        for n in range(min_words, max_words + 1):
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i:i + n])
                counts[ngram] += 1
    return counts


def get_top_phrases(
        titles: list,
        seed_keyword: str = None,
        top_n: int = 10,
        min_words: int = 2,
        max_words: int = 4
) -> list:
    """Helium 10 phrase extractor with fuzzy typo matching and raw n-gram fallback."""
    if not titles:
        print("⚠️ DEBUG: get_top_phrases received an EMPTY titles list from scraper.")
        return []

    print(f"📊 DEBUG: Processing {len(titles)} titles for keyword: '{seed_keyword}'")

    clean_seed = clean_title(seed_keyword) if seed_keyword else ""
    seed_tokens = set(clean_seed.split()) if clean_seed else set()
    phrase_counter = Counter()

    # Step A: Attempt spaCy candidate extraction
    for item in titles:
        raw_title = item.get("title", "") if isinstance(item, dict) else str(item)
        cleaned = clean_title(raw_title)
        if not cleaned:
            continue

        doc = nlp(cleaned)
        title_candidates = set(extract_candidate_phrases(doc, min_words=min_words, max_words=max_words))

        for phrase in title_candidates:
            phrase_tokens = set(phrase.split())
            score = 1.0

            if seed_tokens:
                overlap = sum(
                    1 for st in seed_tokens
                    if any(st[:4] == pt[:4] for pt in phrase_tokens if
                           len(st) >= 4 and len(pt) >= 4) or st in phrase_tokens
                )
                if overlap == len(seed_tokens):
                    score *= 3.0
                elif overlap > 0:
                    score *= 1.5

            phrase_counter[phrase] += score

    # Step B: Fallback to raw regex n-grams if spaCy returned 0 candidates
    if not phrase_counter:
        print("⚠️ DEBUG: spaCy extracted 0 candidates. Triggering raw n-gram fallback...")
        phrase_counter = _extract_raw_ngrams(titles, min_words=min_words, max_words=max_words)

    if not phrase_counter:
        return []

    # Step C: Rank and deduplicate
    sorted_candidates = sorted(
        phrase_counter.keys(),
        key=lambda p: (phrase_counter[p], len(p.split())),
        reverse=True
    )

    final_phrases = []
    for phrase in sorted_candidates:
        if not any(phrase in existing for existing in final_phrases):
            final_phrases.append(phrase)
        if len(final_phrases) == top_n:
            break

    return final_phrases

def build_expansion_urls(top_phrases):
    urls = {}
    for phrase in top_phrases:
        urls[phrase] = f"https://www.daraz.pk/catalog/?q={phrase.replace(' ', '+')}"
    return urls

