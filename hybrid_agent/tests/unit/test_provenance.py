from pathlib import Path

from hybrid_agent.models import Metric, Document
from hybrid_agent.provenance.validator import ProvenanceValidator
from hybrid_agent.ingest.store import DocumentStore


def test_quote_substring_validation(tmp_path):
    store = DocumentStore(tmp_path)
    doc = Document(
        id="TEST-DOC-1",
        ticker="TEST",
        doc_type="10-K",
        title="Test",
        date="2024-01-01",
        url="https://example.com",
        pit_hash="hash",
    )
    content = b"Pricing power remains strong in the premium segment."
    store.save(doc, content)

    metric = Metric(
        name="Revenue",
        value=100.0,
        unit="USD",
        period="2024Q2",
        source_doc_id="TEST-DOC-1",
        page_or_section="p1",
        quote="Pricing power remains strong in the premium segment",
        url="https://example.com",
        metadata={
            "date": "2024-02-01",
        },
    )
    validator = ProvenanceValidator(store)
    issues = validator.validate_metrics([metric])
    assert issues == []

    bad_metric = metric.model_copy(update={"quote": "Nonexistent snippet"})
    issues = validator.validate_metrics([bad_metric])
    assert issues and "quote not found" in issues[0].reason
