"""Interpret kubectl self-access review output without confusing denials with errors."""


def access_review_allowed(return_code: int, output: str) -> bool:
    """Accept yes/no and GKE's one-line `no - reason`; fail on errors or contradictions."""
    text = output.strip()
    if return_code == 0 and text == "yes":
        return True
    denial = text == "no" or (
        text.startswith("no - ") and len(text) > 5 and "\n" not in text and "\r" not in text
    )
    if return_code == 1 and denial:
        return False
    raise ValueError("Unexpected authorization review result")
