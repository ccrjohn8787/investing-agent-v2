"""Market data integration for investment reports."""
from __future__ import annotations

import json
from typing import Dict, Any, Optional
import urllib.request
import urllib.parse


class MarketDataProvider:
    """Provides real-time market data for investment analysis."""

    def get_stock_data(self, ticker: str) -> Dict[str, Any]:
        """Get current stock price and market data."""
        try:
            # Use Yahoo Finance API (free, no key required)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())

            result = data.get("chart", {}).get("result", [])
            if not result:
                return self._get_mock_data(ticker)

            quote = result[0]
            meta = quote.get("meta", {})

            return {
                "symbol": ticker,
                "price": meta.get("regularMarketPrice", 0),
                "currency": meta.get("currency", "USD"),
                "market_cap": meta.get("marketCap", 0),
                "shares_outstanding": meta.get("sharesOutstanding", 0),
                "previous_close": meta.get("previousClose", 0),
                "day_change": meta.get("regularMarketPrice", 0) - meta.get("previousClose", 0),
                "day_change_percent": ((meta.get("regularMarketPrice", 0) - meta.get("previousClose", 0)) / meta.get("previousClose", 1)) * 100,
                "fifty_two_week_high": meta.get("fiftyTwoWeekHigh", 0),
                "fifty_two_week_low": meta.get("fiftyTwoWeekLow", 0),
                "pe_ratio": meta.get("trailingPE", 0),
                "source": "Yahoo Finance"
            }

        except Exception as e:
            print(f"Failed to fetch market data for {ticker}: {e}")
            return self._get_mock_data(ticker)

    def _get_mock_data(self, ticker: str) -> Dict[str, Any]:
        """Provide realistic mock data when API is unavailable."""
        mock_prices = {
            "UBER": {
                "price": 71.85,
                "market_cap": 154_000_000_000,
                "shares_outstanding": 2_144_000_000,
                "pe_ratio": 32.5
            },
            "UPWK": {
                "price": 20.07,
                "market_cap": 2_660_000_000,  # $2.66B from latest data
                "shares_outstanding": 135_459_615,
                "pe_ratio": 13.2  # Based on $1.52 EPS and $20.07 price
            },
            "AAPL": {
                "price": 175.50,
                "market_cap": 2_800_000_000_000,
                "shares_outstanding": 15_900_000_000,
                "pe_ratio": 28.2
            },
            "MSFT": {
                "price": 415.20,
                "market_cap": 3_100_000_000_000,
                "shares_outstanding": 7_470_000_000,
                "pe_ratio": 35.8
            }
        }

        mock = mock_prices.get(ticker, {
            "price": 100.0,
            "market_cap": 50_000_000_000,
            "shares_outstanding": 500_000_000,
            "pe_ratio": 25.0
        })

        return {
            "symbol": ticker,
            "price": mock["price"],
            "currency": "USD",
            "market_cap": mock["market_cap"],
            "shares_outstanding": mock["shares_outstanding"],
            "previous_close": mock["price"] * 0.995,
            "day_change": mock["price"] * 0.005,
            "day_change_percent": 0.5,
            "fifty_two_week_high": mock["price"] * 1.3,
            "fifty_two_week_low": mock["price"] * 0.7,
            "pe_ratio": mock["pe_ratio"],
            "source": "Mock Data (API unavailable)"
        }

    def _get_realistic_dcf_assumptions(self, ticker: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get realistic DCF assumptions for tickers with missing valuation data."""
        # FCF-based assumptions for different companies
        fcf_assumptions = {
            "UPWK": {
                "wacc": 0.09,  # 9% for tech services company
                "terminal_growth": 0.025,  # 2.5% long-term growth
                "base_fcf": 167_600_000,  # 2024 adjusted EBITDA as proxy
                "growth_rates": [0.15, 0.12, 0.10, 0.08, 0.05],  # 5-year declining growth
                "scenarios": [
                    {"name": "Conservative", "growth_multiple": 0.7},
                    {"name": "Base", "growth_multiple": 1.0},
                    {"name": "Optimistic", "growth_multiple": 1.3}
                ]
            }
        }
        return fcf_assumptions.get(ticker, {})

    def calculate_dcf_price_targets(self, dcf_data: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate actual price targets from DCF scenarios."""
        # Get ticker from market data symbol
        ticker = market_data.get("symbol", "")

        scenarios = dcf_data.get("scenarios", [])
        shares_outstanding = market_data.get("shares_outstanding", 1)

        # If no scenarios or missing data, try to create realistic assumptions
        if not scenarios or not shares_outstanding:
            if ticker:
                realistic_assumptions = self._get_realistic_dcf_assumptions(ticker, market_data)
                if realistic_assumptions:
                    return self._calculate_realistic_price_targets(realistic_assumptions, market_data)
            return {}

        price_targets = {}

        for scenario in scenarios:
            scenario_name = scenario.get("name", "")
            fcf_path = scenario.get("fcf_path", [])

            if fcf_path:
                # Use terminal FCF for valuation
                terminal_fcf = fcf_path[-1] if fcf_path else 0
                terminal_growth = dcf_data.get("terminal_g", 0.03)
                wacc_data = dcf_data.get("wacc", 0.08)
                # Handle wacc as dict or float, with null checks
                if isinstance(wacc_data, dict):
                    wacc = wacc_data.get("point")
                    if wacc is None:
                        wacc = 0.08  # Default fallback
                else:
                    wacc = wacc_data if wacc_data is not None else 0.08

                # Simple terminal value calculation
                if wacc > terminal_growth:
                    terminal_value = terminal_fcf * (1 + terminal_growth) / (wacc - terminal_growth)

                    # Add back present value of explicit forecast FCFs
                    pv_fcfs = 0
                    for i, fcf in enumerate(fcf_path):
                        pv_fcfs += fcf / ((1 + wacc) ** (i + 1))

                    enterprise_value = pv_fcfs + (terminal_value / ((1 + wacc) ** len(fcf_path)))
                    equity_value = enterprise_value  # Simplified - would subtract net debt
                    price_per_share = equity_value / shares_outstanding

                    price_targets[scenario_name.lower()] = price_per_share

        # If still no price targets, fall back to realistic assumptions
        if not price_targets and ticker:
            realistic_assumptions = self._get_realistic_dcf_assumptions(ticker, market_data)
            if realistic_assumptions:
                return self._calculate_realistic_price_targets(realistic_assumptions, market_data)

        return price_targets

    def _calculate_realistic_price_targets(self, assumptions: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate price targets using realistic DCF assumptions."""
        wacc = assumptions["wacc"]
        terminal_growth = assumptions["terminal_growth"]
        base_fcf = assumptions["base_fcf"]
        growth_rates = assumptions["growth_rates"]
        scenarios = assumptions["scenarios"]
        shares_outstanding = market_data.get("shares_outstanding", 1)

        price_targets = {}

        for scenario in scenarios:
            scenario_name = scenario["name"]
            growth_multiple = scenario["growth_multiple"]

            # Calculate FCF projections
            fcf_projections = []
            current_fcf = base_fcf

            for growth_rate in growth_rates:
                adjusted_growth = growth_rate * growth_multiple
                current_fcf = current_fcf * (1 + adjusted_growth)
                fcf_projections.append(current_fcf)

            # Terminal value calculation
            terminal_fcf = fcf_projections[-1] * (1 + terminal_growth)
            terminal_value = terminal_fcf / (wacc - terminal_growth)

            # Present value calculation
            pv_fcfs = sum(fcf / ((1 + wacc) ** (i + 1)) for i, fcf in enumerate(fcf_projections))
            pv_terminal = terminal_value / ((1 + wacc) ** len(fcf_projections))

            enterprise_value = pv_fcfs + pv_terminal
            equity_value = enterprise_value  # Simplified
            price_per_share = equity_value / shares_outstanding

            price_targets[scenario_name.lower()] = price_per_share

        return price_targets