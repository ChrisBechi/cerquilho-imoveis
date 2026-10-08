import smtplib
from unittest.mock import MagicMock

import pytest

import test_email


def test_missing_credentials_do_not_connect(monkeypatch):
    monkeypatch.setattr(test_email, "EMAIL_USERNAME", None)
    monkeypatch.setattr(test_email.smtplib, "SMTP", lambda *_args, **_kwargs: pytest.fail("Unexpected SMTP connection"))

    assert test_email.main() == 1


def test_login_uses_configured_credentials_and_tls(monkeypatch):
    smtp = MagicMock()
    tls_context = object()
    monkeypatch.setattr(test_email, "EMAIL_HOST", "smtp.example.com")
    monkeypatch.setattr(test_email, "EMAIL_PORT", 587)
    monkeypatch.setattr(test_email, "EMAIL_USERNAME", "test@example.com")
    monkeypatch.setattr(test_email, "EMAIL_PASSWORD", "fake-test-password")
    monkeypatch.setattr(test_email.smtplib, "SMTP", smtp)
    monkeypatch.setattr(test_email.ssl, "create_default_context", lambda: tls_context)

    assert test_email.main() == 0
    smtp.assert_called_once_with("smtp.example.com", 587, timeout=30)
    server = smtp.return_value.__enter__.return_value
    server.starttls.assert_called_once_with(context=tls_context)
    server.login.assert_called_once_with("test@example.com", "fake-test-password")


def test_authentication_failure_returns_error(monkeypatch, capsys):
    smtp = MagicMock(side_effect=smtplib.SMTPAuthenticationError(535, b"Invalid credentials"))
    monkeypatch.setattr(test_email, "EMAIL_USERNAME", "test@example.com")
    monkeypatch.setattr(test_email, "EMAIL_PASSWORD", "fake-test-password")
    monkeypatch.setattr(test_email.smtplib, "SMTP", smtp)

    assert test_email.main() == 1
    assert "fake-test-password" not in capsys.readouterr().out
