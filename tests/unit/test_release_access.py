from pathlib import Path
from runpy import run_path

from pytest import mark, raises

HELPERS = run_path(str(Path(__file__).resolve().parents[2] / "scripts/release_access.py"))


@mark.parametrize(
    ("code", "output", "allowed"),
    [
        (0, "yes\n", True),
        (1, "no\n", False),
        (1, "no - requires container.secrets.get permission\n", False),
        (1, "no - provider denial\r\n", False),
    ],
)
def test_interprets_review_decisions_including_gke_denial_explanation(code, output, allowed):
    assert HELPERS["access_review_allowed"](code, output) is allowed


@mark.parametrize(
    ("code", "output"),
    [
        (0, "no"),
        (1, "yes"),
        (2, "no - reason"),
        (-9, "no"),
        (1, ""),
        (1, "Unauthorized"),
        (1, "no - "),
        (1, "nope"),
        (1, "no - reason\nunexpected output"),
        (0, "yes - reason"),
    ],
)
def test_rejects_errors_and_contradictory_review_results(code, output):
    with raises(ValueError, match="Unexpected authorization review result"):
        HELPERS["access_review_allowed"](code, output)
