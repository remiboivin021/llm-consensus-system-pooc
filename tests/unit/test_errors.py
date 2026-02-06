import pytest

from src.contracts.errors import ErrorEnvelope
from src.errors import LcsError, from_envelope


def test_from_envelope_maps_fields():
    envelope = ErrorEnvelope(type="timeout", message="slow", retryable=True, status_code=504)
    err = from_envelope(envelope)

    assert isinstance(err, LcsError)
    assert err.code == "timeout"
    assert err.retryable is True
    assert err.details == {"status_code": 504}


def test_from_envelope_unknown_type_defaults_internal():
    envelope = ErrorEnvelope(type="internal", message="boom", retryable=False, status_code=500)
    err = from_envelope(envelope)

    assert err.code == "internal_error"
    assert err.retryable is False


@pytest.mark.parametrize(
    ("etype", "expected"),
    [
        ("timeout", "timeout"),
        ("http_error", "provider_error"),
        ("rate_limited", "provider_error"),
        ("invalid_response", "provider_error"),
        ("config_error", "config_error"),
    ],
)
def test_from_envelope_type_map(etype, expected):
    envelope = ErrorEnvelope(type=etype, message="msg", retryable=False, status_code=418)
    err = from_envelope(envelope)
    assert err.code == expected
    assert err.details == {"status_code": 418}


def test_from_envelope_omits_empty_details():
    envelope = ErrorEnvelope(type="timeout", message="msg", retryable=True, status_code=None)
    err = from_envelope(envelope)
    assert err.retryable is True
    assert err.details is None


def test_from_envelope_preserves_message_and_retryable():
    envelope = ErrorEnvelope(type="http_error", message="bad gateway", retryable=True, status_code=502)
    err = from_envelope(envelope)
    assert err.code == "provider_error"
    assert err.message == "bad gateway"
    assert err.retryable is True


@pytest.mark.parametrize(
    "etype,retryable",
    [("http_error", False), ("rate_limited", True)],
)
def test_from_envelope_retryable_flag(etype, retryable):
    envelope = ErrorEnvelope(type=etype, message="msg", retryable=retryable, status_code=None)
    err = from_envelope(envelope)
    assert err.retryable is retryable
    assert err.details is None


def test_from_envelope_unknown_defaults_internal_and_not_retryable():
    class Unknown:
        def __init__(self):
            self.type = "weird"
            self.message = "boom"
            self.retryable = False
            self.status_code = None

    err = from_envelope(Unknown())
    assert err.code == "internal_error"
    assert err.retryable is False
    assert err.details is None


def test_from_envelope_missing_status_keeps_details_none():
    class NoStatus:
        type = "timeout"
        message = "m"
        retryable = False

    err = from_envelope(NoStatus())
    assert err.details is None
    assert err.retryable is False


def test_from_envelope_status_zero_in_details():
    envelope = ErrorEnvelope(type="timeout", message="zero", retryable=False, status_code=0)
    err = from_envelope(envelope)
    assert err.details == {"status_code": 0}


def test_from_envelope_missing_retryable_defaults_false():
    class NoRetry:
        type = "http_error"
        message = "m"
        status_code = 500

    err = from_envelope(NoRetry())
    assert err.retryable is False
    assert err.code == "provider_error"


def test_from_envelope_missing_message_defaults_empty():
    class NoMessage:
        type = "config_error"
        retryable = False
        status_code = 400

    err = from_envelope(NoMessage())
    assert err.message == ""
    assert err.code == "config_error"


@pytest.mark.parametrize(
    ("etype", "retryable"),
    [
        ("invalid_response", False),
        ("http_error", True),
        ("rate_limited", True),
    ],
)
def test_from_envelope_provider_errors_retryable_and_details(etype, retryable):
    envelope = ErrorEnvelope(type=etype, message="x", retryable=retryable, status_code=None)
    err = from_envelope(envelope)
    assert err.code == "provider_error"
    assert err.retryable is retryable
    assert err.details is None


def test_from_envelope_internal_maps_and_keeps_status():
    envelope = ErrorEnvelope(type="internal", message="boom", retryable=False, status_code=500)
    err = from_envelope(envelope)
    assert err.code == "internal_error"
    assert err.details == {"status_code": 500}


def test_from_envelope_internal_without_status():
    envelope = ErrorEnvelope(type="internal", message="boom", retryable=False, status_code=None)
    err = from_envelope(envelope)
    assert err.code == "internal_error"
    assert err.details is None


def test_from_envelope_unknown_with_status_and_retryable_true():
    class Unknown:
        type = "other"
        message = "msg"
        retryable = "yes"
        status_code = 599

    err = from_envelope(Unknown())
    assert err.code == "internal_error"
    assert err.retryable is True
    assert err.details == {"status_code": 599}


def test_from_envelope_empty_type_defaults_internal():
    class EmptyType:
        type = ""
        message = "x"
        retryable = False
        status_code = None

    err = from_envelope(EmptyType())
    assert err.code == "internal_error"
    assert err.details is None


def test_from_envelope_http_error_with_status_in_details():
    envelope = ErrorEnvelope(type="http_error", message="err", retryable=False, status_code=503)
    err = from_envelope(envelope)
    assert err.code == "provider_error"
    assert err.details == {"status_code": 503}


def test_from_envelope_missing_type_defaults_internal():
    class NoType:
        message = "mt"
        retryable = False
        status_code = None

    err = from_envelope(NoType())
    assert err.code == "internal_error"
    assert err.details is None


def test_from_envelope_maps_provider_errors():
    envelope = ErrorEnvelope(type="rate_limited", message="slow down", retryable=True, status_code=429)
    err = from_envelope(envelope)

    assert err.code == "provider_error"
    assert err.retryable is True
    assert err.details == {"status_code": 429}


def test_from_envelope_handles_missing_fields():
    class Minimal:
        message = "fallback"

    err = from_envelope(Minimal())
    assert err.code == "internal_error"
    assert err.details is None
