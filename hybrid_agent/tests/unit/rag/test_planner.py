from hybrid_agent.models import CompanyQuarter
from hybrid_agent.rag.planner import RetrievalPlanner


def test_retrieval_planner_queries_include_intents():
    quarter = CompanyQuarter(
        ticker="TEST",
        period="2024Q2",
        income_stmt={},
        balance_sheet={},
        cash_flow={},
        segments={},
    )
    planner = RetrievalPlanner()
    output = planner.build_queries(quarter, path="Mature")
    assert {"pricing_power", "kpi_definition", "debt_footnote"}.issubset(output.keys())
    assert any("pricing power" in query for query in output["pricing_power"])
