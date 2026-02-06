import pytest

from src.core.consensus.calibration import IdentityCalibrator, MapCalibrator


def test_identity_calibrator_passthrough():
    calibrator = IdentityCalibrator()

    result = calibrator.calibrate(0.42)

    assert result.calibrated == pytest.approx(0.42)
    assert result.applied is False
    assert result.version == "identity"


def test_map_calibrator_interpolates_and_clamps():
    calibrator = MapCalibrator(
        [(0.0, 0.0), (0.5, 0.6), (1.0, 1.0)], version="v1", sample_size=100
    )

    mid = calibrator.calibrate(0.25)
    assert mid.applied is True
    assert mid.calibrated == pytest.approx(0.3)
    assert 0.0 <= mid.calibrated <= 1.0

    above = calibrator.calibrate(1.5)
    assert above.calibrated == 1.0


def test_map_calibrator_enforces_sample_guard():
    calibrator = MapCalibrator(
        [(0.0, 0.0), (1.0, 1.0)], version="v2", sample_size=5, min_sample_size=10
    )

    guarded = calibrator.calibrate(0.7)

    assert guarded.applied is False
    assert guarded.calibrated == pytest.approx(0.7)
    assert guarded.reason == "insufficient_samples"


def test_map_calibrator_rejects_non_monotonic_map():
    with pytest.raises(ValueError):
        MapCalibrator([(0.0, 0.0), (0.5, 0.4), (0.4, 0.9)], version="bad")
