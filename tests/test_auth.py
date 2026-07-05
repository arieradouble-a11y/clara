import pytest

from clara.auth import AuthStore, bearer_token, hash_password, verify_password


@pytest.fixture
def store(tmp_path):
    return AuthStore(tmp_path / "auth.db")


def test_password_hash_roundtrip():
    h = hash_password("secret")
    assert verify_password("secret", h)
    assert not verify_password("wrong", h)
    assert h != hash_password("secret")  # random salt each time


def test_first_user_is_admin(store):
    assert store.create_user("alice", "pw")["role"] == "admin"
    assert store.count_users() == 1
    assert store.create_user("bob", "pw")["role"] == "reviewer"


def test_duplicate_username_raises(store):
    store.create_user("alice", "pw")
    with pytest.raises(ValueError):
        store.create_user("alice", "pw2")


def test_login_token_resolves_and_hides_hash(store):
    store.create_user("alice", "pw")
    result = store.login("alice", "pw")
    assert result and result["token"]
    user = store.user_for_token(result["token"])
    assert user and user["username"] == "alice"
    assert "password" not in user  # never leak the hash


def test_bad_credentials(store):
    store.create_user("alice", "pw")
    assert store.login("alice", "nope") is None
    assert store.login("ghost", "pw") is None


def test_logout_invalidates_token(store):
    store.create_user("alice", "pw")
    token = store.login("alice", "pw")["token"]
    store.logout(token)
    assert store.user_for_token(token) is None


def test_expired_token_is_rejected(store):
    store.create_user("alice", "pw")
    token = store.login("alice", "pw", ttl_days=-1)["token"]  # already expired
    assert store.user_for_token(token) is None


def test_bearer_parsing():
    assert bearer_token("Bearer abc123") == "abc123"
    assert bearer_token("bearer xyz") == "xyz"
    assert bearer_token("Basic foo") is None
    assert bearer_token(None) is None
