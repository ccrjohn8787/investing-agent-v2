from datetime import date

from hybrid_agent.calculators.metric_builder import MetricBuilder
from hybrid_agent.gates import StageZeroBuilder, determine_path
from hybrid_agent.models import CompanyQuarter, Metric


def _metric(name: str, value, unit="", period="2024Q2") -> Metric:
    return Metric(
        name=name,
        value=value,
        unit=unit,
        period=period,
        source_doc_id="DOC",
        page_or_section="p1",
        quote="Sample quote",
        url="https://example.com",
    )


def _quarter(period="2024Q2", revenue=500_000, fcf=40_000, ebit=50_000, debt=60_000, cash=40_000):
    return CompanyQuarter(
        ticker="TEST",
        period=period,
        income_stmt={"Revenue": revenue, "EBIT": ebit},
        balance_sheet={
            "TotalDebt": debt,
            "Cash": cash,
            "AccountsReceivable": revenue * 0.1,
            "Inventory": revenue * 0.05,
        },
        cash_flow={"FCF": fcf, "CFO": fcf + 5_000},
        segments={"Consolidated": {"Revenue": revenue}},
        metadata={
            "ttm": {
                "Revenue": revenue * 4,
                "FCF": fcf * 4,
                "EBIT": ebit * 4,
                "Cash": cash,
            },
        },
    )


def test_stage0_builder_outputs_gates():
    metrics = [
        _metric("Revenue", 500_000),
        _metric("Accruals Ratio", 0.05),
        _metric("Net Debt / EBITDA", 0.8),
        _metric("ROIC", 0.12),
        _metric("WACC-point", 0.09),
        _metric("Take Rate", 0.2),
    ]
    metadata = {
        "ttm": {"FCF": 200_000, "Cash": 50_000, "Revenue": 2_000_000, "EBIT": 300_000},
    }
    builder = StageZeroBuilder()
    results = builder.build(metrics, metadata, path="Mature")

    assert len(results["hard"]) == 5
    assert results["hard"][0].result == "Pass"
    assert any(row.result != "Fail" for row in results["soft"])
    assert all((row.flip_trigger or row.result == "Pass") for row in results["soft"])


def test_determine_path_checks_rules():
    history = [_quarter(period=f"2023Q{i}") for i in range(1, 9)]
    current = _quarter()
    path = determine_path(current, history)
    assert path.path == "Mature"
    assert path.reasons == []

    weak = _quarter(fcf=-10_000, ebit=-5_000)
    path2 = determine_path(weak, history)
    assert path2.path == "Emergent"
    assert any("TTM FCF" in reason for reason in path2.reasons)
