from hybrid_agent.models import Document
from hybrid_agent.rag.index import InMemoryDocumentIndex
from hybrid_agent.rag.retrieve import Retriever


def test_retriever_returns_ranked_results():
    index = InMemoryDocumentIndex(chunk_size=20)
    doc = Document(
        id="DOC-1",
        ticker="AAPL",
        doc_type="10-K",
        title="Form 10-K",
        date="2024-02-01",
        url="https://example.com",
        pit_hash="hash",
    )
    index.add(doc, "Apple's services segment shows strong retention and pricing power.")
    retriever = Retriever(index=index)

    results = retriever.search("pricing power in services segment")

    assert results
    assert results[0]["document_id"] == "DOC-1"
    assert "pricing power" in results[0]["excerpt"].lower()
