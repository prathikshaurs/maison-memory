"""Name comparison used by identity matching (nb_22). Plain Python, no Spark needed."""
import pytest

from notebook_loader import load_notebook_symbols

fn = load_notebook_symbols("notebooks/silver/nb_22_silver_identity.ipynb",
                           ["fold", "edit_distance_le1", "token_match", "name_match_kind", "name_key", "NICKNAMES"])
fold, edit1, token_match, kind, name_key = (fn[k] for k in ["fold", "edit_distance_le1", "token_match", "name_match_kind", "name_key"])


def test_fold_removes_accents_case_and_symbols():
    assert fold("Zoë-Ann") == "zoeann"
    assert fold("López") == "lopez"
    assert fold(None) is None


@pytest.mark.parametrize("a, b, ok", [
    ("anna", "anna", True), ("anna", "ana", True), ("anna", "anne", True),
    ("anna", "anan", True),            # two neighbours swapped
    ("anna", "ann", True), ("anna", "bobb", False), ("anna", "annaxx", False),
])
def test_edit_distance_at_most_one(a, b, ok):
    assert edit1(a, b) is ok


def test_short_names_never_count_as_typos():
    assert token_match("li", "lu") is None      # too short to trust a one-letter difference


def test_initial_and_nickname():
    assert token_match("j", "john") == "initial"
    assert token_match("alexander", "alex") == "nickname"


@pytest.mark.parametrize("a, b, expected", [
    (("Ana", "Lopez"), ("ana", "lópez"), "exact"),
    (("Ana", "Lopez"), ("Lopez", "Ana"), "swapped"),
    (("Katherine", "Moreau"), ("Katherin", "Moreau"), "typo"),
    (("Ana", "Lopez"), ("Maria", "Silva"), None),
])
def test_name_match_kind(a, b, expected):
    assert kind(*a, *b) == expected


def test_two_fuzzy_parts_are_rejected():
    # a typo in the first name AND a typo in the last name together are too weak
    assert kind("Katherine", "Moreau", "Katherin", "Moreu") is None


def test_name_key_ignores_order_accents_and_case():
    assert name_key("Ana", "Lopez") == name_key("lópez", "ANA")
