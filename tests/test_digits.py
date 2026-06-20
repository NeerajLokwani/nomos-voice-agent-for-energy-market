from app.digits import spell_date, spell_id


def test_spell_malo_matches_example_transcript():
    # CASE-A MaLo from the gold transcript: "fünf, null, drei, eins, zwei, vier, ..."
    assert spell_id("50312478901") == (
        "fünf, null, drei, eins, zwei, vier, sieben, acht, neun, null, eins"
    )


def test_spell_vorgangsnummer_with_letters():
    # CASE-B Vorgangsnummer "KL202644817" -> letters read as letters, digits as words
    assert spell_id("KL202644817") == (
        "K, L, zwei, null, zwei, sechs, vier, vier, acht, eins, sieben"
    )


def test_spell_id_skips_separators():
    assert spell_id("1ESY-9000") == "eins, E, S, Y, neun, null, null, null"


def test_spell_date_full():
    assert spell_date("12.06.2026") == "12. Juni 2026"


def test_spell_date_no_year():
    assert spell_date("18.05.") == "18. Mai"


def test_spell_date_fallback():
    assert spell_date("not-a-date") == "not-a-date"
