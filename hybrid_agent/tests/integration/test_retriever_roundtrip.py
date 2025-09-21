from hybrid_agent.models import Document
from hybrid_agent.rag.index import InMemoryDocumentIndex
from hybrid_agent.rag.retrieve import Retriever


def test_retriever_roundtrip_returns_metadata():
    doc = Document(
        id="DOC-IR",
        ticker="AAPL",
        doc_type="IR-Deck",
        title="Investor Day",
        date="2024-02-15",
        url="https://example.com/ir",
        pit_hash="abc123",
    )
    index = InMemoryDocumentIndex(chunk_size=50)
    index.add(doc, "Management reaffirmed long-term gross margin targets at 45%.")

    retriever = Retriever(index=index)
    results = retriever.search("gross margin targets")

    assert results
    assert results[0]["url"] == "https://example.com/ir"
    assert results[0]["document_type"] == "IR-Deck"
