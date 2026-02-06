import pytest

from src.core.consensus.utils import clamp_confidence, relative_confidence


def test_clamp_confidence_bounds():
    assert clamp_confidence(-0.5) == 0.0
    assert clamp_confidence(0.5) == 0.5
    assert clamp_confidence(1.5) == 1.0


def test_relative_confidence_handles_zero_and_gap():
    assert relative_confidence(0.0, 0.0) == 0.0
    assert relative_confidence(0.9, 0.3) == pytest.approx(2 / 3)
    # Gap larger than top should clamp to 1.0
    assert relative_confidence(0.2, -0.2) == 1.0


def test_relative_confidence_when_top_is_zero():
    # denominator guard should avoid ZeroDivision and return 0
    assert relative_confidence(0.0, 1.0) == 0.0


def test_relative_confidence_when_second_bigger():
    assert relative_confidence(0.5, 0.7) == 0.0


def test_relative_confidence_when_equal():
    assert relative_confidence(0.4, 0.4) == 0.0


def test_relative_confidence_handles_negative_inputs():
    # top negative but gap positive should clamp to 1.0 due to denominator guard
    assert relative_confidence(-0.1, -0.2) == 1.0
