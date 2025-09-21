import textwrap

from hybrid_agent.parse.filing_extractor import FilingExtractor


HTML_SAMPLE = textwrap.dedent(
    """
    <html>
      <body>
        <h2>Consolidated Statements of Operations</h2>
        <table>
          <tr><th>Metric</th><th>2023</th><th>2024</th></tr>
          <tr><td>Revenues</td><td>31,000</td><td>35,000</td></tr>
          <tr><td>Operating income</td><td>(1,200)</td><td>820</td></tr>
          <tr><td>Net income</td><td>(2,000)</td><td>540</td></tr>
        </table>
        <h2>Consolidated Balance Sheets</h2>
        <table>
          <tr><th>Metric</th><th>2023</th><th>2024</th></tr>
          <tr><td>Total assets</td><td>50,000</td><td>55,000</td></tr>
          <tr><td>Total liabilities</td><td>22,000</td><td>23,500</td></tr>
        </table>
        <h2>Consolidated Statements of Cash Flows</h2>
        <table>
          <tr><th>Metric</th><th>2023</th><th>2024</th></tr>
          <tr><td>Net cash provided by operating activities</td><td>4,200</td><td>5,100</td></tr>
          <tr><td>Payments to acquire property and equipment</td><td>(1,100)</td><td>(1,200)</td></tr>
        </table>
      </body>
    </html>
    """
)


def test_filing_extractor_parses_sample_statements():
    extractor = FilingExtractor()
    result = extractor.extract(HTML_SAMPLE)

    assert result.income_statement["Revenues"] == 35000
    assert result.income_statement["Net income"] == 540
    assert result.balance_sheet["Total assets"] == 55000
    assert result.cash_flow["Net cash provided by operating activities"] == 5100
