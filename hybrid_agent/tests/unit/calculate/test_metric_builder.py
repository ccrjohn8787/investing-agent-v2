from hybrid_agent.calculators.metric_builder import MetricBuilder
from hybrid_agent.models import CompanyQuarter


def _quarter():
    return CompanyQuarter(
        ticker="AAPL",
        period="2024Q2",
        income_stmt={
            "Revenue": 1000.0,
            "NetIncome": 220.0,
            "EBIT": 260.0,
        },
        balance_sheet={
            "AccountsReceivable": 150.0,
            "Inventory": 120.0,
            "AccountsPayable": 80.0,
            "CurrentAssets": 700.0,
            "CurrentLiabilities": 400.0,
            "TotalAssets": 2000.0,
            "TotalDebt": 500.0,
            "Cash": 300.0,
            "TotalEquity": 1200.0,
        },
        cash_flow={
            "CFO": 350.0,
            "CapEx": -120.0,
            "FCF": 230.0,
        },
        segments={"Hardware": {"Revenue": 600.0}, "Services": {"Revenue": 400.0}},
    )


def test_metric_builder_generates_metrics():
    builder = MetricBuilder()
    metrics = builder.build(_quarter())

    names = {metric.name for metric in metrics}
    assert "FCF" in names
    assert "DSO" in names
    assert any(metric.inputs for metric in metrics if metric.name == "Accruals Ratio")


def test_metric_builder_marks_abstain_when_missing_fields():
    quarter = _quarter()
    quarter.balance_sheet.pop("AccountsReceivable")
    builder = MetricBuilder()

    metrics = builder.build(quarter)
    dso_metric = next(metric for metric in metrics if metric.name == "DSO")

    assert dso_metric.value == "ABSTAIN"
