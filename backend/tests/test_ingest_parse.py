"""Parser tests: each fixture parses to the expected films, or the expected friendly error."""

import pytest

from app.services.ingest import IngestError, parse_csv_rating, parse_export, slug_from_uri
from tests.helpers import build_export_zip, build_zip_from, fixture_bytes


def _by_slug(films):
    return {f.slug: f for f in films}


def test_full_export_zip_parses_and_dedupes():
    films = parse_export(build_export_zip(), "letterboxd-export.zip")
    by_slug = _by_slug(films)

    # 7 unique films across ratings/diary/watched/reviews (The Matrix appears in 3 files).
    assert len(films) == 7

    matrix = by_slug["the-matrix"]
    assert matrix.title == "The Matrix"
    assert matrix.year == 1999
    assert matrix.rating == 5.0
    assert matrix.review_text == "A perfect film, still."   # merged from reviews.csv
    assert str(matrix.watched_at) == "2024-01-15"           # latest across the three files
    assert matrix.is_rewatch is False


def test_quoted_comma_title_and_accents_survive():
    films = _by_slug(parse_export(build_export_zip(), "e.zip"))
    assert films["goodbye-dragon-inn"].title == "Goodbye, Dragon Inn"   # quoted comma preserved
    assert films["amelie"].title == "Amélie"                            # accents preserved


def test_non_latin_title_and_missing_year():
    films = _by_slug(parse_export(build_export_zip(), "e.zip"))
    assert films["shoplifters"].title == "万引き家族"
    assert films["some-short-film"].year is None                        # missing Year tolerated


def test_rewatch_detected_by_flag_and_by_repeat():
    films = _by_slug(parse_export(build_export_zip(), "e.zip"))
    assert films["amelie"].is_rewatch is True          # explicit Rewatch=Yes
    paprika = films["paprika"]
    assert paprika.is_rewatch is True                  # two diary entries → rewatch
    assert str(paprika.watched_at) == "2024-06-01"     # most-recent watch kept


def test_unrated_watched_film_included_without_rating():
    films = _by_slug(parse_export(build_export_zip(), "e.zip"))
    stalker = films["stalker"]                          # only in watched.csv, no rating
    assert stalker.rating is None
    assert str(stalker.watched_at) == "2019-02-02"


def test_rated_counts():
    films = parse_export(build_export_zip(), "e.zip")
    rated = [f for f in films if f.rating is not None]
    assert len(rated) == 6                             # all but Stalker


def test_zip_nested_in_subfolder_still_parses():
    films = parse_export(build_export_zip(subdir="letterboxd-2024"), "e.zip")
    assert len(films) == 7


def test_bare_single_csv_parses_with_unrated_rows():
    films = parse_export(fixture_bytes("single_diary.csv"), "diary.csv")
    by_slug = {f.slug: f for f in films}
    assert len(films) == 2
    assert by_slug["se7en"].title == "Se7en, Redux"
    assert by_slug["se7en"].rating is None            # empty rating cell → unrated
    assert by_slug["heat"].rating == 4.5


def test_utf8_bom_is_stripped():
    data = b"\xef\xbb\xbf" + fixture_bytes("single_diary.csv")   # prepend a UTF-8 BOM
    films = parse_export(data, "diary.csv")
    assert {f.title for f in films} == {"Se7en, Redux", "Heat"}


# --- error paths (friendly 4xx, never a 500) ---------------------------------


def test_empty_file_raises_empty():
    with pytest.raises(IngestError) as exc:
        parse_export(b"", "export.zip")
    assert exc.value.code == "EMPTY_FILE"


def test_headers_only_csv_raises_no_films():
    with pytest.raises(IngestError) as exc:
        parse_export(fixture_bytes("headers_only.csv"), "ratings.csv")
    assert exc.value.code == "NO_FILMS"


def test_zip_without_letterboxd_csvs_raises():
    data = build_zip_from({"readme.txt": b"not a letterboxd export"})
    with pytest.raises(IngestError) as exc:
        parse_export(data, "random.zip")
    assert exc.value.code == "NO_LETTERBOXD_CSVS"


def test_wrong_file_type_raises_invalid():
    with pytest.raises(IngestError) as exc:
        parse_export(b"\x89PNG\r\n\x1a\n not a csv or zip", "photo.png")
    assert exc.value.code == "INVALID_FILE"


# --- unit helpers ------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [("5.0", 5.0), ("4.5", 4.5), ("0.5", 0.5), ("", None), (None, None), ("6.0", None), ("abc", None), ("3", 3.0)],
)
def test_parse_csv_rating(raw, expected):
    assert parse_csv_rating(raw) == expected


@pytest.mark.parametrize(
    "uri,expected",
    [
        ("https://letterboxd.com/film/the-matrix/", "the-matrix"),
        ("https://letterboxd.com/user/film/amelie/2/", "amelie"),
        ("", None),
        (None, None),
        ("https://example.com/notafilm/", None),
    ],
)
def test_slug_from_uri(uri, expected):
    assert slug_from_uri(uri) == expected
