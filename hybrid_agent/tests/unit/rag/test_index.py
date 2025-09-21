from hybrid_agent.rag.index import InMemoryDocumentIndex
from hybrid_agent.models import Document


def test_index_builds_chunks():
    document = Document(
        id="DOC-1",
        ticker="AAPL",
        doc_type="10-K",
        title="Form 10-K",
        date="2024-02-01",
        url="https://example.com",
        pit_hash="deadbeef",
    )
    index = InMemoryDocumentIndex(chunk_size=5)
    index.add(document, "Pricing power evident in consumer upgrades.")

    chunks = list(index.iter_chunks())
    assert len(chunks) >= 1
    assert chunks[0].document_id == "DOC-1"
