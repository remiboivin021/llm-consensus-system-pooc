from src.core.safety.truncation import truncate_middle


def test_truncate_middle_no_change_when_short():
    text = "hello"
    truncated, info = truncate_middle(text, 10)
    assert truncated == text
    assert info.applied is False
    assert info.removed_bytes == 0


def test_truncate_middle_applies_ellipsis():
    text = "abcdefghijklmnopqrstuvwxyz"
    truncated, info = truncate_middle(text, 10)
    assert truncated.startswith("abc")
    assert truncated.endswith("xyz")
    assert len(truncated) == 10
    assert info.applied is True
    assert info.original_chars == len(text)
    assert info.truncated_chars == len(truncated)
