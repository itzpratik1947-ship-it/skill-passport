import services.passport_store as store


def test_publish_get_and_revoke(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test.sqlite3")
    sample = {"passport_id": "SP-TEST", "candidate": {"name": "Test"}, "skills": []}
    token = store.publish_passport(sample)
    assert token and token != sample["passport_id"]
    assert store.get_public_passport(token) == sample
    assert store.revoke_passport(token) is True
    assert store.get_public_passport(token) is None
    assert store.revoke_passport(token) is False


def test_url_uses_configured_app_url():
    assert store.make_public_url("abc", "https://example.streamlit.app/") == "https://example.streamlit.app/?passport=abc"
