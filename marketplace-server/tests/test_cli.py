import pytest

from app import cli
from app.models.user import UserRole


class FakeSession:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = None
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def scalar(self, _query):
        return self.existing

    def add(self, user):
        self.added = user

    def commit(self):
        self.committed = True


def test_create_admin_hashes_password_and_persists_user(monkeypatch, capsys):
    session = FakeSession()
    monkeypatch.setattr(cli, "SessionLocal", lambda: session)
    passwords = iter(("secure-admin-password", "secure-admin-password"))
    monkeypatch.setattr(cli, "getpass", lambda _prompt: next(passwords))

    cli.create_admin("ADMIN@example.com")

    assert session.added.email == "admin@example.com"
    assert session.added.role == UserRole.admin
    assert session.added.password_hash != "secure-admin-password"
    assert session.committed
    assert "Administrator admin@example.com created" in capsys.readouterr().out


@pytest.mark.parametrize("password", ["short", "x" * 73])
def test_create_admin_rejects_password_outside_supported_length(monkeypatch, password):
    monkeypatch.setattr(cli, "getpass", lambda _prompt: password)
    with pytest.raises(SystemExit, match="Password must contain"):
        cli.create_admin("admin@example.com")


def test_create_admin_rejects_mismatched_confirmation(monkeypatch):
    passwords = iter(("secure-admin-password", "different-password"))
    monkeypatch.setattr(cli, "getpass", lambda _prompt: next(passwords))
    with pytest.raises(SystemExit, match="Passwords do not match"):
        cli.create_admin("admin@example.com")


def test_create_admin_rejects_existing_email(monkeypatch):
    session = FakeSession(existing=object())
    monkeypatch.setattr(cli, "SessionLocal", lambda: session)
    passwords = iter(("secure-admin-password", "secure-admin-password"))
    monkeypatch.setattr(cli, "getpass", lambda _prompt: next(passwords))
    with pytest.raises(SystemExit, match="already exists"):
        cli.create_admin("admin@example.com")
