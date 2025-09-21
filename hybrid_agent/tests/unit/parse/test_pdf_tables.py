from pathlib import Path

from hybrid_agent.parse.pdf_tables import PDFTableExtractor


def test_pdf_table_extractor_returns_rows(tmp_path):
    sample_text = """Revenue,Region,Value\nProduct,US,400\nProduct,EMEA,350\n"""
    pdf_path = tmp_path / "kpi_table.txt"
    pdf_path.write_text(sample_text)

    extractor = PDFTableExtractor()
    rows = list(extractor.extract_tables(pdf_path))

    assert rows[0] == ["Revenue", "Region", "Value"]
    assert rows[2][2] == "350"
