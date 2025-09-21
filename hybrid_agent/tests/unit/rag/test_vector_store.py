from pathlib import Path

from hybrid_agent.models import Document
from hybrid_agent.rag.vector_store import TfidfVectorStore


def _doc(doc_id: str, text: str) -> Document:
    return Document(
        id=doc_id,
        ticker="TEST",
        doc_type="10-K",
        title="Sample",
        date="2024-01-01",
        url=f"https://example.com/{doc_id}",
        pit_hash="deadbeef",
    )


def test_vector_store_add_and_search(tmp_path):
    store = TfidfVectorStore()
    store.add(_doc("doc-1", "Pricing power in the premium segment"), "Pricing power in the premium segment")
    store.add(_doc("doc-2", "Logistics expansion and driver incentives"), "Logistics expansion and driver incentives")

    results = store.search("pricing power")
    assert results
    assert results[0][0].document_id == "doc-1"

    artifact = tmp_path / "store.pkl"
    store.persist(artifact)
    loaded = TfidfVectorStore.load(artifact)
    results_loaded = loaded.search("driver incentives")
    assert results_loaded[0][0].document_id == "doc-2"
