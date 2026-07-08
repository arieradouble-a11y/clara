import pytest

from clara.auth import (
    AuthStore,
    RateLimitedError,
    bearer_token,
    can_approve,
    hash_password,
    is_admin,
    verify_password,
)


@pytest.fixture
def store(tmp_path):
    return AuthStore(tmp_path / "auth.db")


def test_login_rate_limited_after_max_attempts(tmp_path):
    s = AuthStore(tmp_path / "auth.db", max_attempts=3, lockout_seconds=300)
    s.create_user("alice", "correct")
    for _ in range(3):
        assert s.login("alice", "wrong") is None      # failures counted
    with pytest.raises(RateLimitedError):
        s.login("alice", "wrong")                      # 4th is locked out
    with pytest.raises(RateLimitedError):
        s.login("alice", "correct")                    # even a correct pw is blocked while locked


def test_successful_login_clears_failure_counter(tmp_path):
    s = AuthStore(tmp_path / "auth.db", max_attempts=3, lockout_seconds=300)
    s.create_user("alice", "correct")
    assert s.login("alice", "wrong") is None
    assert s.login("alice", "wrong") is None
    assert s.login("alice", "correct") is not None     # succeeds and resets
    for _ in range(3):
        assert s.login("alice", "wrong") is None       # counter was reset, so 3 more allowed


def test_prune_sessions_removes_expired(store):
    store.create_user("alice", "pw")
    sess = store.login("alice", "pw", ttl_days=-1)      # already expired
    assert sess is not None
    assert store.user_for_token(sess["token"]) is None  # expired -> not resolved
    assert store.prune_sessions() >= 0                  # and prunable without error


def test_role_helpers():
    assert is_admin({"role": "admin"})
    assert not is_admin({"role": "reviewer"})
    assert not is_admin(None)
    # auth off (user None) -> anyone can approve; auth on -> admin or the assignee
    assert can_approve(None, None)
    assert can_approve({"id": 1, "role": "admin"}, None)
    assert can_approve({"id": 7, "role": "reviewer"}, 7)       # the assigned validator
    assert not can_approve({"id": 8, "role": "reviewer"}, 7)   # a different reviewer


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
