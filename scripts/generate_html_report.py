#!/usr/bin/env python3
"""Generate HTML investment analysis reports from ticker data."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add the project root to Python path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hybrid_agent.reports.html_generator import HTMLReportGenerator
from hybrid_agent.reports.store import ReportStore


def generate_html_report(ticker: str, output_path: Optional[Path] = None) -> Path:
    """Generate HTML report for a ticker.

    Args:
        ticker: Stock ticker symbol
        output_path: Optional output path for HTML file

    Returns:
        Path to generated HTML file
    """
    # Try to load from report store first
    report_store = ReportStore()

    try:
        data = report_store.fetch(ticker.upper())
        if not data:
            raise FileNotFoundError(f"No report data found for {ticker}")
    except Exception:
        # Fall back to JSON file if report store fails
        json_file = ROOT / f"{ticker.lower()}_output.json"
        if not json_file.exists():
            raise FileNotFoundError(f"No analysis data found for {ticker}. "
                                  f"Run analysis first with: python scripts/run_ticker.py --ticker {ticker}")

        with open(json_file, 'r') as f:
            data = json.load(f)

    # Generate HTML report
    generator = HTMLReportGenerator()
    html_content = generator.generate_report(data, ticker.upper())

    # Determine output path
    if output_path is None:
        output_path = ROOT / f"{ticker.lower()}_report.html"

    # Write HTML file
    output_path.write_text(html_content, encoding='utf-8')

    return output_path


def run_full_analysis_and_generate_html(ticker: str, output_path: Optional[Path] = None) -> Path:
    """Run full analysis pipeline and generate HTML report.

    Args:
        ticker: Stock ticker symbol
        output_path: Optional output path for HTML file

    Returns:
        Path to generated HTML file
    """
    import subprocess

    print(f"Running analysis for {ticker}...")

    # Run the analysis script
    run_ticker_script = ROOT / "scripts" / "run_ticker.py"
    temp_output = ROOT / f"{ticker.lower()}_output.json"
    cmd = [sys.executable, str(run_ticker_script), ticker, str(temp_output)]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Analysis completed successfully!")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Analysis failed: {e}")
        print(f"Error output: {e.stderr}")
        raise

    # Generate HTML report
    return generate_html_report(ticker, output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate HTML investment analysis reports")
    parser.add_argument("--ticker", required=True, help="Stock ticker symbol (e.g., UBER)")
    parser.add_argument("--output", type=Path, help="Output HTML file path")
    parser.add_argument("--run-analysis", action="store_true",
                       help="Run full analysis before generating HTML")
    parser.add_argument("--open", action="store_true",
                       help="Open the generated HTML file in browser")

    args = parser.parse_args()

    try:
        if args.run_analysis:
            html_path = run_full_analysis_and_generate_html(args.ticker, args.output)
        else:
            html_path = generate_html_report(args.ticker, args.output)

        print(f"✅ HTML report generated: {html_path}")

        if args.open:
            import webbrowser
            webbrowser.open(f"file://{html_path.resolve()}")
            print("📖 Opened in browser")

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print(f"💡 Try running with --run-analysis to generate fresh data")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()