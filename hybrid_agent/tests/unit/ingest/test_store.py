import pytest

from hybrid_agent.ingest.store import DocumentStore
from hybrid_agent.models import Document


@pytest.fixture
def sample_document(tmp_path):
    return Document(
        id="AAPL-20240201-abcdef",
        ticker="AAPL",
        doc_type="10-K",
        title="Form 10-K",
        date="2024-02-01",
        url="https://example.com/aapl-10k.pdf",
        pit_hash="abcdef",
        pdf_pages=None,
    )


def test_save_and_load_roundtrip(tmp_path, sample_document):
    store = DocumentStore(base_path=tmp_path)
    content = b"filing body"

    store.save(sample_document, content)
    loaded_document, loaded_bytes = store.load(sample_document.id)

    assert loaded_document == sample_document
    assert loaded_bytes == content


def test_save_is_idempotent(tmp_path, sample_document):
    store = DocumentStore(base_path=tmp_path)
    content = b"filing body"

    store.save(sample_document, content)
    store.save(sample_document, content)

    documents = list(store.list_documents())

    assert len(documents) == 1
    assert documents[0].id == sample_document.id


def test_list_documents(tmp_path, sample_document):
    store = DocumentStore(base_path=tmp_path)
    content = b"filing body"
    store.save(sample_document, content)

    documents = list(store.list_documents())

    assert len(documents) == 1
    assert documents[0].id == sample_document.id
