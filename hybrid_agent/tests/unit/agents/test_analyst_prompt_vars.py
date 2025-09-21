from hybrid_agent.agents.analyst import AnalystAgent


class StubLLM:
    def generate(self, prompt: str) -> str:
        return "{}"


def test_prompt_injects_ticker_and_path(tmp_path):
    agent = AnalystAgent(llm=StubLLM())
    prompt = agent.build_prompt(
        ticker="AAPL",
        today="2024-06-30",
        path="Mature",
        metrics_summary="Revenue: 1000",
    )

    assert "AAPL" in prompt
    assert "Mature" in prompt
