from app.services.analysis_service import _safe_gemini_error


def test_high_demand_error_is_actionable() -> None:
    message = _safe_gemini_error(RuntimeError("503 UNAVAILABLE: model at high demand"))
    assert "temporarily unavailable" in message
    assert "retry" in message.lower()


def test_auth_error_does_not_echo_provider_payload() -> None:
    message = _safe_gemini_error(RuntimeError("403 PERMISSION_DENIED"))
    assert "authorization failed" in message.lower()
    assert "PERMISSION_DENIED" not in message
