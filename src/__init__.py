"""Public interface for the LCS consensus library."""

from src.client import LcsClient, consensus, list_strategies
from src.contracts.request import ConsensusRequest
from src.contracts.response import ConsensusResult
from src.errors import LcsError

__all__ = [
    "LcsClient",
    "consensus",
    "list_strategies",
    "ConsensusRequest",
    "ConsensusResult",
    "LcsError",
]
