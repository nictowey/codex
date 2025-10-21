from __future__ import annotations

from app.core.metrics import (
    CatalystMetrics,
    CompanyIndicators,
    GrowthMetrics,
    QualityMetrics,
    RiskMetrics,
    ValuationMetrics,
)

SAMPLE_FUNDAMENTALS = {
    "CLS": {
        "growth": {"threeYearRevenueCagr": 0.17, "revenueGrowth": 0.05},
        "profitability": {
            "ebitMargin": 0.04,
            "freeCashFlowMargin": 0.08,
            "roic": 0.19,
        },
        "operational": {"backlogGrowth": 0.32},
        "trend": {"roic": 0.05, "assetTurnover": 0.08},
        "leverage": {"netDebtToEbitda": 1.1, "interestCoverage": 10.0},
        "sentiment": {"earningsRevision": 0.18, "insiderActivity": 0.55},
        "valuation": {"pegRatio": 0.9, "fcfYield": 0.05},
        "size": {"marketCap": 4.2e9},
        "risk": {"beta": 1.1, "volatility3Y": 0.32},
        "profile": {"sector": "Technology", "industry": "Electronic Components"},
        "themeAlignment": 0.85,
        "strategicInvestorScore": 0.3,
        "evToEbitdaVsPeers": -1.5,
        "priceMomentum": 0.22,
        "consolidationScore": 0.6,
        "avgDollarVolume": 4.5e7,
        "drawdown1Y": 0.2,
    },
    "NVST": {
        "growth": {"threeYearRevenueCagr": 0.09, "revenueGrowth": 0.03},
        "profitability": {
            "ebitMargin": 0.02,
            "freeCashFlowMargin": 0.07,
            "roic": 0.14,
        },
        "operational": {"backlogGrowth": 0.18},
        "trend": {"roic": 0.03, "assetTurnover": 0.05},
        "leverage": {"netDebtToEbitda": 1.8, "interestCoverage": 8.0},
        "sentiment": {"earningsRevision": 0.1, "insiderActivity": 0.35},
        "valuation": {"pegRatio": 1.1, "fcfYield": 0.045},
        "size": {"marketCap": 6.5e9},
        "risk": {"beta": 1.0, "volatility3Y": 0.28},
        "profile": {"sector": "Healthcare", "industry": "Medical Instruments"},
        "themeAlignment": 0.7,
        "strategicInvestorScore": 0.15,
        "evToEbitdaVsPeers": -0.8,
        "priceMomentum": 0.15,
        "consolidationScore": 0.5,
        "avgDollarVolume": 2.2e7,
        "drawdown1Y": 0.25,
    },
    "SMCI": {
        "growth": {"threeYearRevenueCagr": 0.4, "revenueGrowth": 0.2},
        "profitability": {
            "ebitMargin": 0.07,
            "freeCashFlowMargin": 0.09,
            "roic": 0.23,
        },
        "operational": {"backlogGrowth": 0.45},
        "trend": {"roic": 0.07, "assetTurnover": 0.12},
        "leverage": {"netDebtToEbitda": -0.5, "interestCoverage": 20.0},
        "sentiment": {"earningsRevision": 0.25, "insiderActivity": 0.4},
        "valuation": {"pegRatio": 1.4, "fcfYield": 0.03},
        "size": {"marketCap": 25e9},
        "risk": {"beta": 1.45, "volatility3Y": 0.55},
        "profile": {"sector": "Technology", "industry": "Computer Hardware"},
        "themeAlignment": 0.95,
        "strategicInvestorScore": 0.2,
        "evToEbitdaVsPeers": 1.0,
        "priceMomentum": 0.3,
        "consolidationScore": 0.35,
        "avgDollarVolume": 1.5e9,
        "drawdown1Y": 0.4,
    },
}


def load_sample_companies() -> list[CompanyIndicators]:
    """Provide sample companies approximating Celestica-like setups."""

    companies: list[CompanyIndicators] = []
    for ticker, fundamentals in SAMPLE_FUNDAMENTALS.items():
        metadata = {
            "sector": fundamentals.get("profile", {}).get("sector"),
            "industry": fundamentals.get("profile", {}).get("industry"),
            "themeAlignment": fundamentals["themeAlignment"],
            "strategicInvestorScore": fundamentals["strategicInvestorScore"],
            "evToEbitdaVsPeers": fundamentals["evToEbitdaVsPeers"],
            "priceMomentum": fundamentals["priceMomentum"],
            "consolidationScore": fundamentals["consolidationScore"],
            "avgDollarVolume": fundamentals["avgDollarVolume"],
            "drawdown1Y": fundamentals["drawdown1Y"],
        }

        companies.append(
            CompanyIndicators(
                ticker=ticker,
                name={
                    "CLS": "Celestica Inc.",
                    "NVST": "Envista Holdings",
                    "SMCI": "Super Micro Computer",
                }[ticker],
                growth=GrowthMetrics(
                    revenue_cagr_3y=fundamentals["growth"]["threeYearRevenueCagr"],
                    revenue_acceleration=fundamentals["growth"]["revenueGrowth"],
                    ebit_margin_trend=fundamentals["profitability"]["ebitMargin"],
                    fcf_margin=fundamentals["profitability"]["freeCashFlowMargin"],
                    backlog_growth=fundamentals["operational"]["backlogGrowth"],
                ),
                quality=QualityMetrics(
                    roic=fundamentals["profitability"]["roic"],
                    roic_trend=fundamentals["trend"]["roic"],
                    net_debt_to_ebitda=fundamentals["leverage"]["netDebtToEbitda"],
                    interest_coverage=fundamentals["leverage"]["interestCoverage"],
                    asset_turnover_trend=fundamentals["trend"]["assetTurnover"],
                ),
                catalysts=CatalystMetrics(
                    theme_alignment=fundamentals["themeAlignment"],
                    earnings_revision_trend=fundamentals["sentiment"]["earningsRevision"],
                    insider_activity_score=fundamentals["sentiment"]["insiderActivity"],
                    strategic_investor_presence=fundamentals["strategicInvestorScore"],
                ),
                valuation=ValuationMetrics(
                    peg_ratio=fundamentals["valuation"]["pegRatio"],
                    ev_to_ebitda_vs_peers=fundamentals["evToEbitdaVsPeers"],
                    free_cash_flow_yield=fundamentals["valuation"]["fcfYield"],
                    price_momentum=fundamentals["priceMomentum"],
                    consolidation_score=fundamentals["consolidationScore"],
                ),
                risk=RiskMetrics(
                    market_cap=fundamentals["size"]["marketCap"],
                    avg_daily_dollar_volume=fundamentals["avgDollarVolume"],
                    beta=fundamentals["risk"]["beta"],
                    volatility_3y=fundamentals["risk"]["volatility3Y"],
                    drawdown_1y=fundamentals["drawdown1Y"],
                ),
                sector=metadata.get("sector"),
                industry=metadata.get("industry"),
                metadata=metadata,
            )
        )
    return companies
