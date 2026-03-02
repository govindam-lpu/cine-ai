LETTERBOXD_SYMBOL_TO_VALUE = {
    "½": 0.5,
    "★": 1.0,
    "★★": 2.0,
    "★★★": 3.0,
    "★★★★": 4.0,
    "★★★★★": 5.0,
    "★½": 1.5,
    "★★½": 2.5,
    "★★★½": 3.5,
    "★★★★½": 4.5,
}


def parse_letterboxd_rating(raw: str | None) -> float | None:
    if not raw:
        return None
    normalized = raw.strip().replace(" ", "")
    return LETTERBOXD_SYMBOL_TO_VALUE.get(normalized)
