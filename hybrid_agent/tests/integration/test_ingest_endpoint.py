from fastapi.testclient import TestClient

from hybrid_agent.api import app, get_ingest_service
from hybrid_agent.ingest.edgar import EDGARClient
from hybrid_agent.ingest.service import IngestService
from hybrid_agent.ingest.store import DocumentStore


def test_ingest_endpoint_persists_documents(tmp_path):
    content_map = {
        "https://example.com/aapl-10k.pdf": b"filing-body",
    }

    def fake_http_get(url: str) -> bytes:
        return content_map[url]

    edgar_client = EDGARClient(http_get=fake_http_get)
    document_store = DocumentStore(base_path=tmp_path)
    ingest_service = IngestService(client=edgar_client, store=document_store)

    app.dependency_overrides[get_ingest_service] = lambda: ingest_service
    client = TestClient(app)

    response = client.post(
        "/ingest",
        json={
            "ticker": "AAPL",
            "documents": [
                {
                    "doc_type": "10-K",
                    "title": "Form 10-K",
                    "date": "2024-02-01",
                    "url": "https://example.com/aapl-10k.pdf",
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "AAPL"
    assert len(payload["documents"]) == 1

    doc_payload = payload["documents"][0]
    loaded_doc, raw_bytes = document_store.load(doc_payload["id"])

    assert raw_bytes == b"filing-body"
    assert str(loaded_doc.url) == "https://example.com/aapl-10k.pdf"
    assert loaded_doc.doc_type == "10-K"

    app.dependency_overrides.clear()
