"""Retention limits live in nb_21b as plain settings. These tests make sure nobody weakens them by accident."""
from notebook_loader import load_notebook_symbols

s = load_notebook_symbols("notebooks/silver/nb_21b_silver_history_retention.ipynb",
                          ["PROSPECT_MONTHS", "COUNTRY_PROSPECT_MONTHS", "RELATIONSHIP_YEARS", "TRACKED_COLUMNS"])


def test_every_region_has_a_prospect_limit():
    assert set(s["PROSPECT_MONTHS"]) == {"americas", "europe", "asia_pacific"}
    assert all(isinstance(m, int) and 1 <= m <= 60 for m in s["PROSPECT_MONTHS"].values())


def test_country_override_is_stricter_than_its_region():
    # KR sits in asia_pacific; an override should shorten the limit, never extend it
    assert s["COUNTRY_PROSPECT_MONTHS"]["KR"] < s["PROSPECT_MONTHS"]["asia_pacific"]


def test_relationship_clients_are_held_for_review_not_quickly_deleted():
    assert s["RELATIONSHIP_YEARS"] >= 5


def test_consent_is_tracked_in_history():
    assert "consent_share_cross_region" in s["TRACKED_COLUMNS"]
