from hybrid_agent.storage.json_store import JSONKeyValueStore


def test_json_key_value_store_roundtrip(tmp_path):
    path = tmp_path / "store.json"
    store = JSONKeyValueStore(path)
    store.set("AAPL", {"value": 1})

    assert store.get("AAPL")["value"] == 1
    assert store.all()["AAPL"]["value"] == 1

    store.delete("AAPL")
    assert store.get("AAPL") is None
