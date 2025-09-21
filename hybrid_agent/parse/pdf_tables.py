"""Simple PDF table extraction placeholder."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Union


class PDFTableExtractor:
    """Parses delimited text exported from PDFs into rows."""

    def extract_tables(self, source: Union[Path, str]) -> Iterable[List[str]]:
        path = Path(source)
        for line in path.read_text(encoding="utf-8").strip().splitlines():
            yield [cell.strip() for cell in line.split(",")]
