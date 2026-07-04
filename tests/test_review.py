import pytest

from clara.review import ReviewStore


@pytest.fixture
def store(tmp_path):
    return ReviewStore(tmp_path / "reviews.db")


def test_create_and_get(store):
    r = store.create_review(title="Notice", source="Pay $500 by 2024-01-01.",
                            output="Pay 500 dollars by 1 January 2024.", faithful=True)
    assert r["id"] >= 1
    assert r["status"] == "in_review"
    assert r["faithful"] is True
    assert len(r["versions"]) == 1        # initial version recorded
    assert r["versions"][0]["note"] == "initial"
    assert store.get_review(r["id"])["title"] == "Notice"


def test_list_and_status_filter(store):
    a = store.create_review(title="A", source="s", output="o")
    store.create_review(title="B", source="s", output="o")
    store.set_status(a["id"], "approved")
    assert len(store.list_reviews()) == 2
    approved = store.list_reviews(status="approved")
    assert len(approved) == 1 and approved[0]["title"] == "A"


def test_comments(store):
    r = store.create_review(title="A", source="s", output="o")
    store.add_comment(r["id"], "reviewer", "The second sentence is unclear.")
    got = store.get_review(r["id"])
    assert got["comments"][0]["author"] == "reviewer"
    assert "unclear" in got["comments"][0]["body"]


def test_revision_adds_version_and_updates_output(store):
    r = store.create_review(title="A", source="s", output="v1", faithful=False)
    updated = store.add_revision(r["id"], "v2 better", note="fixed the fine", faithful=True)
    assert updated["output"] == "v2 better"
    assert updated["faithful"] is True
    assert len(updated["versions"]) == 2
    assert updated["versions"][-1]["note"] == "fixed the fine"


def test_set_status_validates(store):
    r = store.create_review(title="A", source="s", output="o")
    with pytest.raises(ValueError):
        store.set_status(r["id"], "bogus")
    assert store.set_status(r["id"], "changes_requested")["status"] == "changes_requested"


def test_missing_review_returns_none(store):
    assert store.get_review(999) is None
    assert store.add_comment(999, "x", "y") is None
    assert store.set_status(999, "approved") is None


def test_delete(store):
    r = store.create_review(title="A", source="s", output="o")
    assert store.delete_review(r["id"]) is True
    assert store.get_review(r["id"]) is None
    assert store.delete_review(r["id"]) is False
