"""The pipeline sorts every failure into one of five classes. These tests pin the rules."""
import pytest

from notebook_loader import load_notebook_symbols

nb = load_notebook_symbols("notebooks/orchestration/nb_90_run_pipeline.ipynb",
                           ["classify_failure", "CLASS_RULES", "RETRYABLE", "SUGGESTED_ACTION"])
classify = nb["classify_failure"]


@pytest.mark.parametrize("message, expected", [
    ("java.io.FileNotFoundException: Operation failed: path does not exist", "source"),
    ("AnalysisException: [TABLE_OR_VIEW_NOT_FOUND] The table or view `bronze_crm_client` cannot be found", "integration"),
    ("RuntimeError: Silver reconciliation failed for: sales", "processing"),
    ("Notebook execution timed out after 3600 seconds", "infrastructure"),
    ("Fetch notebook content for 'nb_22_silver_identity' failed ... tokenservice1 ...", "infrastructure"),
    ("Request failed with status code 429", "infrastructure"),
    ("Cannot cast column amount: datatype mismatch", "integration"),
    ("Something odd happened", "unknown"),
])
def test_known_messages(message, expected):
    assert classify(message)[0] == expected


def test_numbers_alone_do_not_mean_throttling():
    # "429" and "503" only count when they look like an HTTP status
    assert classify("Row counts 429 and 503 look odd")[0] == "unknown"


def test_our_own_check_beats_platform_words():
    # a reconciliation message that also mentions a timeout is still a data problem to read first
    assert classify("reconciliation failed after timeout in the check cell")[0] == "processing"


def test_empty_and_none_are_unknown():
    assert classify("")[0] == "unknown"
    assert classify(None)[0] == "unknown"


def test_only_platform_failures_are_retryable():
    assert nb["RETRYABLE"] == {"infrastructure": 1, "source": 0, "integration": 0, "processing": 0, "unknown": 0}


def test_every_class_has_a_suggested_action():
    classes = {c for c, _ in nb["CLASS_RULES"]} | {"unknown"}
    assert classes == set(nb["SUGGESTED_ACTION"])
    assert all(len(text) > 20 for text in nb["SUGGESTED_ACTION"].values())
