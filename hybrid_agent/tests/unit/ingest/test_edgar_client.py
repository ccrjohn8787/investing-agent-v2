import hashlib
from unittest.mock import Mock

import pytest

from hybrid_agent.ingest.edgar import EDGARClient, FetchError
from hybrid_agent.models import Document


def _sample_doc_kwargs():
    return {
        "ticker": "AAPL",
        "doc_type": "10-K",
        "title": "Form 10-K",
        "date": "2024-02-01",
        "url": "https://example.com/aapl-10k.pdf",
    }


def test_fetch_document_success():
    content = b"sample filing content"
    http_get = Mock(return_value=content)
    client = EDGARClient(http_get=http_get)

    document, raw_bytes = client.fetch_document(**_sample_doc_kwargs())

    assert isinstance(document, Document)
    assert raw_bytes == content
    assert document.ticker == "AAPL"
    assert str(document.url) == "https://example.com/aapl-10k.pdf"
    assert document.pit_hash == hashlib.sha256(content).hexdigest()
    assert document.id.startswith("AAPL-")
    http_get.assert_called_once_with("https://example.com/aapl-10k.pdf")


def test_fetch_document_retries_then_raises():
    http_get = Mock(side_effect=IOError("boom"))
    client = EDGARClient(http_get=http_get, max_retries=2)

    with pytest.raises(FetchError):
        client.fetch_document(**_sample_doc_kwargs())

    assert http_get.call_count == 3
