from src.adapters.observability.metrics import render_metrics


def test_render_metrics_returns_bytes():
    data = render_metrics()
    assert isinstance(data, (bytes, bytearray))
    assert len(data) > 0
