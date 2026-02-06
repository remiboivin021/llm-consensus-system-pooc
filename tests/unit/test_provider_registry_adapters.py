import pytest

from src.adapters.orchestration.models import ProviderResult
from src.adapters.providers import registry
from src.adapters.providers.openrouter import OpenRouterProvider, register_default_openrouter
from src.errors import LcsError


@pytest.fixture(autouse=True)
def reset_registry():
    registry.clear_registry()
    register_default_openrouter()
    yield
    registry.clear_registry()
    register_default_openrouter()


def test_resolve_uses_default_openrouter():
    provider, model = registry.resolve_provider("any-model")
    assert isinstance(provider, OpenRouterProvider)
    assert model == "any-model"


def test_resolve_inline_unknown_provider_raises():
    with pytest.raises(LcsError):
        registry.resolve_provider("nope::model-x")


def test_resolve_override_unknown_provider_raises():
    with pytest.raises(LcsError):
        registry.resolve_provider("model-x", override_name="missing")


def test_resolve_supports_false_raises():
    class RejectingProvider:
        name = "reject"

        def supports(self, model: str) -> bool:
            return False

        async def call(self, *args, **kwargs):
            return ProviderResult(model="m", content=None, latency_ms=0, error=None)

    registry.register_provider(RejectingProvider())

    with pytest.raises(LcsError):
        registry.resolve_provider("model-y", override_name="reject")
