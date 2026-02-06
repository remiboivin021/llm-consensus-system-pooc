from src.contracts.early_stop import EarlyStopConfig
from src.core.consensus.early_stop import early_stop_decision


def test_early_stop_disabled_no_stop():
    cfg = EarlyStopConfig(enabled=False)
    decision = early_stop_decision(1, 0.9, cfg)
    assert decision.stop is False


def test_early_stop_respects_min_samples():
    cfg = EarlyStopConfig(enabled=True, min_samples=3, max_samples=5, confidence_threshold=0.6)
    decision = early_stop_decision(2, 0.9, cfg)
    assert decision.stop is False


def test_early_stop_confidence_reached():
    cfg = EarlyStopConfig(enabled=True, min_samples=2, max_samples=5, confidence_threshold=0.5)
    decision = early_stop_decision(2, 0.6, cfg)
    assert decision.stop is True
    assert decision.reason == "confidence_reached"


def test_early_stop_hits_max_samples():
    cfg = EarlyStopConfig(enabled=True, min_samples=1, max_samples=2, confidence_threshold=0.9)
    decision = early_stop_decision(2, 0.1, cfg)
    assert decision.stop is True
    assert decision.reason == "max_samples"
