from datetime import date

from hybrid_agent.triggers.monitor import TriggerMonitor


def test_trigger_monitor_flags_breach():
    monitor = TriggerMonitor()
    monitor.upsert(
        ticker="AAPL",
        name="Gross Margin",
        threshold=0.4,
        comparison="gte",
        deadline=date(2024, 9, 30),
    )

    alerts = monitor.evaluate(
        ticker="AAPL",
        metrics={"Gross Margin": 0.35},
        today=date(2024, 9, 30),
    )

    assert alerts
    assert alerts[0]["trigger"] == "Gross Margin"
    assert "breach" in alerts[0]["message"].lower()
