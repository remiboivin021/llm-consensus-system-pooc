import pytest
from pydantic import ValidationError

from src.contracts.request import ConsensusRequest
from src.contracts.response import Timing


def test_consensus_request_requires_models():
    with pytest.raises(ValidationError):
        ConsensusRequest(prompt="hi", models=[])


def test_timing_rejects_negative():
    with pytest.raises(ValidationError):
        Timing(e2e_ms=-1)
