"""Compile the five patterns shared by validation and extraction."""

import re  # Use Python's standard regex engine for both actions.

# A DNS label is 1–63 ASCII characters and starts and ends with a letter or digit.
DOMAIN_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
# Require at least one label and a final alphabetic suffix of 2–63 letters.
DOMAIN = rf"(?:{DOMAIN_LABEL}\.)+[A-Za-z]{{2,63}}"
# Allow common email characters in each segment between literal dots.
EMAIL_SEGMENT = r"[A-Za-z0-9_+%-]+"
# Stop before a sentence-ending period but reject continuations of a malformed domain.
DOMAIN_END = r"(?![\w@%+-]|\.+[\w@-])"
# Leave spaces, enclosing punctuation and parentheses out of ordinary URL text.
URL_CHAR = r"""[^\s<>"“”‘’()[\]{}\\]"""

PATTERNS = {  # Keep the compiled patterns in display order.
    "email": re.compile(
        r"(?<![\w.@+%\\!&*-])"  # Prevent a match from starting inside an unsupported local segment.
        r"(?<!\w['’])"  # Allow a leading quote but skip suffixes after a word and apostrophe.
        rf"{EMAIL_SEGMENT}(?:\.{EMAIL_SEGMENT})*@"  # Join local segments with dots, then require @.
        rf"{DOMAIN}{DOMAIN_END}"  # Read the DNS-style domain and check its right boundary.
    ),
    "url": re.compile(
        r"(?<![\w/])(?ai:https?)://"  # Start at a token boundary with HTTP or HTTPS.
        rf"{DOMAIN}{DOMAIN_END}"  # Use the same DNS rules as email.
        r"(?!:[0-9])"  # Skip numeric port URLs instead of returning just their hostname.
        rf"(?:[/?#](?:{URL_CHAR}|"  # Start a path, query or fragment and allow URL text.
        rf"\({URL_CHAR}*\))*)?"  # Keep balanced, non-nested parentheses inside the URL.
        r"(?<![.,!?;:#'…])"  # Backtrack past trailing sentence punctuation or a bare delimiter.
    ),
    "phone": re.compile(
        r"(?<!\w)(?<![0-9][.-])"  # Reject starts inside words and longer separated numbers.
        r"(?:\([0-9]{3}\) [0-9]{3}-[0-9]{4}|"  # Accept the parenthesized US-style format.
        r"[0-9]{3}(?P<separator>[.-])[0-9]{3}(?P=separator)[0-9]{4})"  # Reuse the first separator.
        r"(?!\w|[.-][0-9])"  # Reject attached word characters and extra digit groups.
    ),
    "time": re.compile(
        r"(?<![\w:])"  # Reject starts inside words, longer numbers and colon groups.
        r"(?:(?:0?[1-9]|1[0-2]):[0-5][0-9][ \t]+(?ai:[AP]M)|"  # Prefer the full 12-hour time.
        r"(?:[01][0-9]|2[0-3]):[0-5][0-9](?![ \t]+(?ai:[AP]M)\b))"  # Block 24-hour matches with AM/PM.
        r"(?!\w|:[0-9])"  # Reject attached word characters and seconds but allow a prose colon.
    ),
    "hashtag": re.compile(
        r"(?<![\w#])"  # Reject hashes attached to a word or another hash.
        r"#[A-Za-z0-9_]+"  # Require at least one ASCII letter, digit or underscore.
        r"(?!\w)"  # Skip partial tags ending before a Unicode word character.
    ),
}


def validate(category: str, text: str) -> bool:  # Check one category for the entire input.
    return PATTERNS[category].fullmatch(text.strip()) is not None  # Ignore surrounding whitespace.


def extract(category: str, text: str) -> list[dict[str, str | int]]:  # Scan the original text.
    categories = PATTERNS if category == "all" else (category,)  # Reuse the same compiled patterns.
    matches = [  # Collect matches and their spans before combining the categories.
        {
            "category": name,  # Identify the pattern that produced the match.
            "value": match.group(),  # Preserve the exact substring.
            "start": match.start(),  # Count Python characters from zero.
            "end": match.end(),  # Stop just after the final character.
        }
        for name in categories  # Run each requested category independently.
        for match in PATTERNS[name].finditer(text)  # Retain matches from overlapping categories.
    ]
    return sorted(matches, key=lambda match: match["start"])  # Return matches in source order.
