from __future__ import annotations

import io
from datetime import datetime
from typing import Dict, Iterable, List, Tuple

import pandas as pd
import streamlit as st
import altair as alt

from app.core.backtesting import run_backtests
from app.core.metrics import (
    CatalystMetrics,
    CompanyIndicators,
    GrowthMetrics,
    QualityMetrics,
    RiskMetrics,
    ScoreBreakdown,
    ValuationMetrics,
    WeightConfig,
)
from app.core.portfolio import build_portfolio_plan
from app.core.scoring_engine import rank_companies
from app.core.settings import UserPreferences, UserPreferencesStore, WeightSettingsStore
from app.core.tuning import recommend_weights
from app.data.ingestion import DataIngestionManager, build_default_manager
from app.data.sample_data import load_sample_companies
from app.data.sample_history import SAMPLE_PRICE_SERIES, load_fundamental_history
from app.data.tracking import RankingTracker

st.set_page_config(page_title="Growth Breakout Stock Picker", layout="wide")

THEME_PALETTES = {
    "Aurora Dark": {
        "background": "linear-gradient(135deg, #0b132b 0%, #1c2541 45%, #3a506b 100%)",
        "container_bg": "rgba(14, 23, 43, 0.72)",
        "card_bg": "rgba(28, 37, 65, 0.88)",
        "accent": "#43d9ad",
        "accent_soft": "rgba(67, 217, 173, 0.18)",
        "text_primary": "#f5f7fa",
        "text_secondary": "#a7b0c4",
        "chart_colors": ["#43d9ad", "#7fffd4", "#6f9ceb", "#b892ff", "#f5a5ff"],
    },
    "Nimbus Light": {
        "background": "linear-gradient(135deg, #f8fafc 0%, #eef2ff 45%, #e0f2fe 100%)",
        "container_bg": "rgba(255, 255, 255, 0.85)",
        "card_bg": "rgba(246, 249, 255, 0.92)",
        "accent": "#2563eb",
        "accent_soft": "rgba(37, 99, 235, 0.12)",
        "text_primary": "#0f172a",
        "text_secondary": "#475569",
        "chart_colors": ["#2563eb", "#7dd3fc", "#a855f7", "#f472b6", "#fb923c"],
    },
}


def apply_theme(theme_name: str) -> None:
    palette = THEME_PALETTES.get(theme_name, THEME_PALETTES["Aurora Dark"])
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        body, .stApp {{
            background: {palette['background']} !important;
            color: {palette['text_primary']} !important;
            font-family: 'Inter', sans-serif;
        }}
        .stMarkdown p, .stMarkdown li, .stMarkdown span {{
            font-family: 'Inter', sans-serif !important;
        }}
        .hero-container {{
            background: {palette['container_bg']};
            border-radius: 24px;
            padding: 28px 36px 32px 36px;
            box-shadow: 0 25px 60px rgba(4, 12, 33, 0.35);
            margin-bottom: 24px;
        }}
        .hero-title {{
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 6px;
            color: {palette['text_primary']};
        }}
        .hero-subtitle {{
            font-size: 1.05rem;
            color: {palette['text_secondary']};
            margin-bottom: 0;
        }}
        .pill-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 999px;
            background: {palette['accent_soft']};
            color: {palette['accent']};
            font-size: 0.85rem;
            margin-right: 10px;
            font-weight: 600;
        }}
        .metric-card {{
            background: {palette['card_bg']};
            border-radius: 18px;
            padding: 16px 18px;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 12px 30px rgba(3, 15, 35, 0.2);
            min-height: 120px;
        }}
        .metric-card h3 {{
            font-size: 0.9rem;
            font-weight: 600;
            color: {palette['text_secondary']};
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }}
        .metric-card .metric-value {{
            font-size: 1.8rem;
            font-weight: 700;
            color: {palette['text_primary']};
        }}
        .metric-card .metric-note {{
            font-size: 0.85rem;
            color: {palette['text_secondary']};
            margin-top: 6px;
        }}
        .stMetric label {{
            color: {palette['text_secondary']} !important;
        }}
        .stMetric div[data-testid="stMetricValue"] {{
            color: {palette['text_primary']} !important;
        }}
        .stTabs [data-baseweb="tab-list"] button {{
            background: transparent;
            padding: 14px 22px;
            border-radius: 14px 14px 0 0;
            font-weight: 600;
            color: {palette['text_secondary']};
        }}
        .stTabs [aria-selected="true"] {{
            background: {palette['card_bg']};
            color: {palette['text_primary']};
            box-shadow: inset 0 -3px 0 {palette['accent']};
        }}
        [data-testid="stSidebar"] {{
            background: transparent;
        }}
        .stButton button {{
            border-radius: 14px;
            background: {palette['accent']};
            color: white;
            font-weight: 600;
            padding: 0.6rem 1.4rem;
            box-shadow: 0 15px 30px rgba(28, 214, 155, 0.25);
            border: none;
        }}
        .stButton button:hover {{
            filter: brightness(1.05);
        }}
        .stDownloadButton button {{
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.15);
            color: {palette['text_primary']};
            background: transparent;
            font-weight: 600;
        }}
        .stDownloadButton button:hover {{
            background: rgba(255,255,255,0.08);
        }}
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stSelectbox div[data-baseweb="select"] > div,
        .stSelectbox div[data-baseweb="select"] input {{
            background: {palette['card_bg']};
            color: {palette['text_primary']} !important;
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.35);
        }}
        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {{
            color: {palette['text_secondary']} !important;
            opacity: 0.7;
        }}
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] p {{
            color: {palette['text_secondary']} !important;
        }}
        [data-testid="stSidebar"] .stTextInput input,
        [data-testid="stSidebar"] .stTextArea textarea,
        [data-testid="stSidebar"] .stNumberInput input,
        [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] input {{
            color: {palette['text_primary']} !important;
        }}
        .streamlit-expanderHeader {{
            font-weight: 600;
            color: {palette['text_primary']} !important;
        }}
        .streamlit-expanderContent {{
            background: {palette['card_bg']};
            border-radius: 0 0 16px 16px;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .stDataFrame {{
            background: {palette['card_bg']};
            border-radius: 18px;
            padding: 8px;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .highlight-chip {{
            display: inline-flex;
            flex-direction: column;
            justify-content: center;
            gap: 2px;
            min-width: 160px;
            padding: 12px 16px;
            background: {palette['card_bg']};
            border-radius: 16px;
            border: 1px solid {palette['accent_soft']};
            box-shadow: 0 18px 30px rgba(15, 23, 42, 0.25);
            margin-right: 12px;
        }}
        .highlight-chip span:first-child {{
            font-size: 0.75rem;
            color: {palette['text_secondary']};
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .highlight-chip span:last-child {{
            font-size: 1.1rem;
            font-weight: 600;
            color: {palette['text_primary']};
        }}
        .highlight-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin: 6px 0 24px 0;
        }}
        .app-footer {{
            margin-top: 54px;
            padding: 18px 24px;
            border-radius: 18px;
            background: {palette['card_bg']};
            border: 1px solid rgba(255,255,255,0.05);
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .app-footer a {{
            color: {palette['accent']};
            font-weight: 600;
        }}
        .weight-chart-container {{
            background: {palette['card_bg']};
            padding: 16px 18px 12px 18px;
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 12px 28px rgba(3, 15, 35, 0.18);
        }}
        .altair-tooltip {{
            font-family: 'Inter', sans-serif;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(theme_name: str) -> None:
    palette = THEME_PALETTES.get(theme_name, THEME_PALETTES["Aurora Dark"])
    st.markdown(
        f"""
        <div class="hero-container">
            <div class="pill-badge">🚀 Breakout intelligence · 3–5 year horizon</div>
            <h1 class="hero-title">Growth Breakout Stock Picker</h1>
            <p class="hero-subtitle">
                Surface high-conviction U.S. equities that mirror the Celestica-style run: accelerating fundamentals, strategic catalysts, and balanced risk.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer(theme_name: str) -> None:
    palette = THEME_PALETTES.get(theme_name, THEME_PALETTES["Aurora Dark"])
    st.markdown(
        f"""
        <div class="app-footer">
            <span>⚡️ Continue refining your playbook — refresh data frequently to capture regime shifts.</span>
            <span><a href="https://www.investopedia.com/terms/b/bottomsupanalysis.asp" target="_blank">Explore bottom-up research primer ↗</a></span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _persist_preferences() -> None:
    current = UserPreferences(
        theme=st.session_state.get("theme_choice", "Aurora Dark"),
        favorites=st.session_state.get("favorite_tickers", []),
        live_tickers=st.session_state.get("live_tickers", []),
        data_mode=st.session_state.get("data_mode", "Live data (cached)"),
        auto_refresh=st.session_state.get("auto_refresh", False),
    )
    stored: UserPreferences = st.session_state.get("preferences", UserPreferences())
    if current != stored:
        preferences_store.save(current)
        st.session_state["preferences"] = current


@st.cache_resource(show_spinner=False)
def _get_manager() -> DataIngestionManager:
    return build_default_manager()


@st.cache_resource(show_spinner=False)
def _get_tracker() -> RankingTracker:
    return RankingTracker()


weight_store = WeightSettingsStore()
preferences_store = UserPreferencesStore()

default_weights = weight_store.load()
stored_preferences = preferences_store.load()

if "weight_config" not in st.session_state:
    st.session_state["weight_config"] = default_weights
if "preferences" not in st.session_state:
    st.session_state["preferences"] = stored_preferences

preferences: UserPreferences = st.session_state["preferences"]

st.session_state.setdefault("theme_choice", preferences.theme)
st.session_state.setdefault("favorite_tickers", preferences.favorites)
st.session_state.setdefault("live_tickers", preferences.live_tickers)
st.session_state.setdefault("auto_refresh", preferences.auto_refresh)
st.session_state.setdefault("data_mode", preferences.data_mode)

apply_theme(st.session_state["theme_choice"])
render_hero(st.session_state["theme_choice"])


manager = _get_manager()


def _render_scorecards(
    scores: List[ScoreBreakdown],
    theme_name: str,
    favorites: List[str],
    price_payloads: Dict[str, Dict[str, object]],
) -> None:
    weight_mapping = (scores[0].weights or WeightConfig()).normalized().to_dict() if scores else {}
    ranking_df = pd.DataFrame([score.to_dict() for score in scores])
    highlight_records: List[Dict[str, object]] = []
    if not ranking_df.empty:
        favorite_set = {ticker.upper() for ticker in favorites}
        ranking_df["is_favorite"] = ranking_df["ticker"].str.upper().isin(favorite_set)
        highlight_records = ranking_df.head(3)[
            ["ticker", "name", "is_favorite"]
        ].to_dict(orient="records")
        ranking_df = ranking_df[
            [
                "ticker",
                "name",
                "is_favorite",
                "composite",
                "growth",
                "quality",
                "catalysts",
                "valuation",
                "risk",
            ]
        ]
        ranking_df = ranking_df.rename(
            columns={
                "ticker": "Ticker",
                "name": "Name",
                "is_favorite": "★",
                "composite": "Composite",
                "growth": "Growth",
                "quality": "Quality",
                "catalysts": "Catalysts",
                "valuation": "Valuation",
                "risk": "Risk",
            }
        )

    st.subheader("Ranked Candidates")
    if ranking_df.empty:
        st.info("No companies to display yet. Configure a data source to begin.")
        return

    palette = THEME_PALETTES.get(theme_name, THEME_PALETTES["Aurora Dark"])

    top_highlights_html = ""
    if highlight_records:
        chips = []
        for record in highlight_records:
            favorite_marker = "⭐" if record.get("is_favorite") else ""
            chips.append(
                f"""
                    <div class='highlight-chip'>
                        <span>{record['ticker']}</span>
                        <span>{favorite_marker} {record['name']}</span>
                    </div>
                """
            )
        top_highlights_html = "".join(chips)

    if top_highlights_html:
        st.markdown(
            f"<div class='highlight-row'>{top_highlights_html}</div>",
            unsafe_allow_html=True,
        )

    top_row = ranking_df.iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.markdown(
        f"""
        <div class="metric-card">
            <h3>Top composite</h3>
            <div class="metric-value">{top_row['Composite']:.3f}</div>
            <div class="metric-note">{top_row['Ticker']} · {top_row['Name']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col2.markdown(
        f"""
        <div class="metric-card">
            <h3>Average growth score</h3>
            <div class="metric-value">{ranking_df['Growth'].mean():.3f}</div>
            <div class="metric-note">Blend of revenue, backlog, and margin acceleration</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col3.markdown(
        f"""
        <div class="metric-card">
            <h3>Risk guardrail</h3>
            <div class="metric-value">{ranking_df['Risk'].mean():.3f}</div>
            <div class="metric-note">Lower is safer · Liquidity & drawdown filters</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    styled_df = (
        ranking_df.assign(**{"★": ranking_df["★"].map({True: "★", False: ""})})
        .style.format(
            {
                "Composite": "{:.3f}",
                "Growth": "{:.3f}",
                "Quality": "{:.3f}",
                "Catalysts": "{:.3f}",
                "Valuation": "{:.3f}",
                "Risk": "{:.3f}",
            }
        )
        .background_gradient(cmap="viridis", subset=["Composite"])
        .set_properties(**{"font-weight": "600"}, subset=["Composite"])
    )

    st.dataframe(styled_df, use_container_width=True)

    st.markdown(
        f"<span style='font-weight:600;color:{palette['accent']}'>Active weights</span> — "
        + ", ".join(f"{factor}: {weight_mapping[factor]:.0%}" for factor in weight_mapping),
        unsafe_allow_html=True,
    )

    tracker = _get_tracker()
    if st.button("Record snapshot", icon="🗂️"):
        tracker.append(scores, price_lookup=price_payloads)
        st.success("Snapshot saved for historical tracking.")

    for score in scores:
        with st.expander(f"{score.ticker} — {score.name}"):
            st.markdown(
                f"**Composite:** {score.composite:.3f}\\  "
                f"Growth {score.growth:.3f} • Quality {score.quality:.3f} • "
                f"Catalysts {score.catalysts:.3f} • Valuation {score.valuation:.3f} • "
                f"Risk {score.risk:.3f}"
            )


def _render_factor_drilldown(
    indicator_map: Dict[str, CompanyIndicators],
    price_payloads: Dict[str, Dict[str, object]],
) -> None:
    if not indicator_map:
        st.info("Rank companies first to unlock drill-down analytics.")
        return

    ticker = st.selectbox("Select a ticker", list(indicator_map.keys()))
    indicators = indicator_map[ticker]
    cols = st.columns(5)
    cols[0].metric("Revenue CAGR (3y)", f"{indicators.growth.revenue_cagr_3y:.1%}")
    cols[1].metric("FCF Margin", f"{indicators.growth.fcf_margin:.1%}")
    cols[2].metric("ROIC", f"{indicators.quality.roic:.1%}")
    cols[3].metric("PEG", f"{indicators.valuation.peg_ratio:.2f}")
    cols[4].metric("Beta", f"{indicators.risk.beta:.2f}")

    left, right = st.columns(2)
    with left:
        try:
            fundamentals_df = load_fundamental_history(ticker)
            st.line_chart(fundamentals_df[["revenue"]], height=260)
            st.line_chart(fundamentals_df[["ebit_margin"]], height=260)
        except Exception:
            st.warning("Fundamental history unavailable for this ticker.")

    with right:
        payload = price_payloads.get(ticker)
        if payload:
            df = pd.DataFrame(payload.get("candles", []))
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
                st.line_chart(df[["close"]], height=320)
            else:
                st.info("Price history not available in the selected data source.")
        else:
            st.info("Price history not cached yet. Run a refresh to populate.")


def _render_backtests(results) -> None:
    if results is None:
        st.info("Fetch live data or use the sample dataset to run backtests.")
        return
    if len(results) == 0:
        st.warning("No valid price history was available for backtesting.")
        return

    df = pd.DataFrame(
        [
            {
                "Ticker": result.ticker,
                "Cumulative Return": result.cumulative_return,
                "CAGR": result.cagr,
                "Max Drawdown": result.max_drawdown,
            }
            for result in results
        ]
    )
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Cumulative Return": st.column_config.NumberColumn(format="%.1%"),
            "CAGR": st.column_config.NumberColumn(format="%.1%"),
            "Max Drawdown": st.column_config.NumberColumn(format="%.1%"),
        },
    )


def _render_portfolio(scores: List[ScoreBreakdown], indicator_map: Dict[str, CompanyIndicators]) -> None:
    plan = build_portfolio_plan(scores, indicator_map)
    if not plan.suggestions:
        st.info("Compute rankings to generate a draft portfolio plan.")
        return

    df = pd.DataFrame(
        {
            "Ticker": suggestion.ticker,
            "Name": suggestion.name,
            "Weight": suggestion.weight,
            "Composite": suggestion.composite,
            "Notes": ", ".join(suggestion.notes) if suggestion.notes else "",
        }
        for suggestion in plan.suggestions
    )
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Weight": st.column_config.NumberColumn(format="%.1%"),
            "Composite": st.column_config.NumberColumn(format="%.3f"),
        },
    )
    st.markdown(
        f"**Expected return proxy:** {plan.expected_return:.1%}  •  "
        f"Volatility proxy: {plan.volatility_proxy:.2f}  •  "
        f"Diversification index: {plan.diversification_index:.2f}"
    )
    if plan.sector_allocations:
        sector_df = pd.DataFrame(
            {
                "Sector": list(plan.sector_allocations.keys()),
                "Weight": list(plan.sector_allocations.values()),
            }
        )
        st.markdown("#### Sector exposures")
        st.dataframe(
            sector_df,
            use_container_width=True,
            column_config={"Weight": st.column_config.NumberColumn(format="%.1%")},
        )

    if plan.scenarios:
        scenario_df = pd.DataFrame(
            {
                "Scenario": [scenario.name for scenario in plan.scenarios],
                "Expected": [scenario.expected_return for scenario in plan.scenarios],
                "Volatility": [scenario.volatility for scenario in plan.scenarios],
                "5% VaR": [scenario.value_at_risk for scenario in plan.scenarios],
                "Notes": ["; ".join(scenario.notes) for scenario in plan.scenarios],
            }
        )
        st.markdown("#### Stress scenarios")
        st.dataframe(
            scenario_df,
            use_container_width=True,
            column_config={
                "Expected": st.column_config.NumberColumn(format="%.1%"),
                "Volatility": st.column_config.NumberColumn(format="%.1%"),
                "5% VaR": st.column_config.NumberColumn(format="%.1%"),
            },
        )


def _manual_csv_upload() -> List[CompanyIndicators]:
    st.subheader("Upload your own indicators")
    st.write(
        "Upload a CSV that includes at least the metrics defined in the planning phase. "
        "A ready-to-edit template is provided below."
    )

    template_buffer = io.StringIO()
    template_columns = {
        "ticker": "CLS",
        "name": "Celestica Inc.",
        "revenue_cagr_3y": 0.17,
        "revenue_acceleration": 0.05,
        "ebit_margin_trend": 0.04,
        "fcf_margin": 0.08,
        "backlog_growth": 0.32,
        "roic": 0.19,
        "roic_trend": 0.05,
        "net_debt_to_ebitda": 1.1,
        "interest_coverage": 10.0,
        "asset_turnover_trend": 0.08,
        "theme_alignment": 0.85,
        "earnings_revision_trend": 0.18,
        "insider_activity_score": 0.55,
        "strategic_investor_presence": 0.3,
        "peg_ratio": 0.9,
        "ev_to_ebitda_vs_peers": -1.5,
        "free_cash_flow_yield": 0.05,
        "price_momentum": 0.22,
        "consolidation_score": 0.6,
        "market_cap": 4.2e9,
        "avg_daily_dollar_volume": 4.5e7,
        "beta": 1.1,
        "volatility_3y": 0.32,
        "drawdown_1y": 0.2,
    }
    pd.DataFrame([template_columns]).to_csv(template_buffer, index=False)
    st.download_button(
        "Download CSV template",
        template_buffer.getvalue().encode("utf-8"),
        file_name="indicator_template.csv",
        mime="text/csv",
    )

    uploaded_file = st.file_uploader("Upload indicator CSV", type="csv")
    if uploaded_file is None:
        st.info("Upload a CSV to evaluate your tickers.")
        return []

    df = pd.read_csv(uploaded_file)
    missing_columns = [col for col in template_columns if col not in df.columns]
    if missing_columns:
        st.error(
            "The following columns are missing from the uploaded CSV: " + ", ".join(missing_columns)
        )
        return []

    indicators: List[CompanyIndicators] = []
    for _, row in df.iterrows():
        growth = GrowthMetrics(
            revenue_cagr_3y=float(row["revenue_cagr_3y"]),
            revenue_acceleration=float(row["revenue_acceleration"]),
            ebit_margin_trend=float(row["ebit_margin_trend"]),
            fcf_margin=float(row["fcf_margin"]),
            backlog_growth=float(row["backlog_growth"]),
        )
        quality = QualityMetrics(
            roic=float(row["roic"]),
            roic_trend=float(row["roic_trend"]),
            net_debt_to_ebitda=float(row["net_debt_to_ebitda"]),
            interest_coverage=float(row["interest_coverage"]),
            asset_turnover_trend=float(row["asset_turnover_trend"]),
        )
        catalysts = CatalystMetrics(
            theme_alignment=float(row["theme_alignment"]),
            earnings_revision_trend=float(row["earnings_revision_trend"]),
            insider_activity_score=float(row["insider_activity_score"]),
            strategic_investor_presence=float(row["strategic_investor_presence"])
            if not pd.isna(row["strategic_investor_presence"])
            else None,
        )
        valuation = ValuationMetrics(
            peg_ratio=float(row["peg_ratio"]),
            ev_to_ebitda_vs_peers=float(row["ev_to_ebitda_vs_peers"]),
            free_cash_flow_yield=float(row["free_cash_flow_yield"]),
            price_momentum=float(row["price_momentum"]),
            consolidation_score=float(row["consolidation_score"]),
        )
        risk = RiskMetrics(
            market_cap=float(row["market_cap"]),
            avg_daily_dollar_volume=float(row["avg_daily_dollar_volume"]),
            beta=float(row["beta"]),
            volatility_3y=float(row["volatility_3y"]),
            drawdown_1y=float(row["drawdown_1y"]),
        )

        indicators.append(
            CompanyIndicators(
                ticker=str(row["ticker"]).upper(),
                name=str(row.get("name", "")) or str(row["ticker"]).upper(),
                growth=growth,
                quality=quality,
                catalysts=catalysts,
                valuation=valuation,
                risk=risk,
            )
        )

    return indicators


with st.sidebar:
    st.header("Appearance")
    st.selectbox(
        "Interface theme",
        list(THEME_PALETTES.keys()),
        key="theme_choice",
        help="Toggle between Aurora Dark and Nimbus Light modes.",
    )
    st.markdown("---")
    favorites_input = st.text_input(
        "Favorite tickers",
        value=", ".join(st.session_state.get("favorite_tickers", [])),
        help="Use favorites to spotlight must-track names across runs.",
    )
    favorites = [item.strip().upper() for item in favorites_input.split(",") if item.strip()]
    st.session_state["favorite_tickers"] = favorites

    st.session_state["auto_refresh"] = st.toggle(
        "Auto-refresh cache",
        value=st.session_state.get("auto_refresh", False),
        help="Automatically refresh cached indicators when data looks stale.",
    )

    st.header("Configuration")
    mode = st.radio(
        "Data source",
        (
            "Sample data",
            "Live data (cached)",
            "Upload CSV",
        ),
        key="data_mode",
    )

    if mode == "Live data (cached)":
        st.caption(
            "Live fetches use bundled free-tier API keys unless overridden by "
            "FINNHUB_TOKEN, FMP_TOKEN, or TWELVE_DATA_TOKEN environment variables."
        )

    st.markdown("""
        ### Methodology Overview
        * **Growth momentum** emphasizes revenue, margin, and backlog acceleration.
        * **Quality** prioritizes capital efficiency, leverage, and coverage trends.
        * **Catalysts** track narrative tailwinds, estimate revisions, and insider activity.
        * **Valuation** balances upside vs. pricing and technical confirmation.
        * **Risk** enforces liquidity and drawdown guardrails.
    """)

    st.header("Scoring weights")
    weight_config = st.session_state["weight_config"]
    growth_weight = st.slider("Growth", 0.0, 0.6, value=float(weight_config.growth), step=0.01)
    quality_weight = st.slider("Quality", 0.0, 0.6, value=float(weight_config.quality), step=0.01)
    catalyst_weight = st.slider("Catalysts", 0.0, 0.6, value=float(weight_config.catalysts), step=0.01)
    valuation_weight = st.slider("Valuation", 0.0, 0.6, value=float(weight_config.valuation), step=0.01)
    risk_weight = st.slider("Risk", 0.0, 0.6, value=float(weight_config.risk), step=0.01)

    updated_weights = WeightConfig(
        growth=growth_weight,
        quality=quality_weight,
        catalysts=catalyst_weight,
        valuation=valuation_weight,
        risk=risk_weight,
    )
    st.session_state["weight_config"] = updated_weights

    if updated_weights.total_weight() == 0:
        st.warning("Assign at least one non-zero weight to generate rankings.")

    if st.button("Save weights as default", use_container_width=True):
        weight_store.save(updated_weights)
        st.success("Weights saved to local profile.")


    st.markdown("---")
    st.header("Data health")
    for status in manager.get_provider_health():
        last_success = (
            datetime.fromtimestamp(status.last_success_at).strftime("%b %d %H:%M")
            if status.last_success_at
            else "never"
        )
        health_msg = f"✅ Last success {last_success}"
        if status.last_error:
            last_error = (
                datetime.fromtimestamp(status.last_error_at).strftime("%b %d %H:%M")
                if status.last_error_at
                else ""
            )
            health_msg = f"⚠️ {status.last_error} ({last_error})"
        st.caption(f"**{status.name}** — {health_msg}")


indicator_map: Dict[str, CompanyIndicators] = {}
price_payloads: Dict[str, Dict[str, object]] = {}
indicators: List[CompanyIndicators] = []

if mode == "Sample data":
    indicators = load_sample_companies()
    indicator_map = {item.ticker: item for item in indicators}
    price_payloads = {ticker: {"candles": candles} for ticker, candles in SAMPLE_PRICE_SERIES.items()}
elif mode == "Live data (cached)":
    tickers_input = st.sidebar.text_input(
        "Tickers", value=", ".join(st.session_state.get("live_tickers", ["CLS", "NVST", "SMCI"]))
    )
    tickers = [ticker.strip().upper() for ticker in tickers_input.split(",") if ticker.strip()]
    st.session_state["live_tickers"] = tickers
    refresh = st.sidebar.button("Force refresh cache", use_container_width=True)
    auto_summary = None
    if tickers and st.session_state.get("auto_refresh"):
        auto_summary = manager.ensure_auto_refresh(tickers)
        if auto_summary.refreshed:
            st.sidebar.success(
                f"Auto-refreshed: {', '.join(auto_summary.refreshed)}", icon="🔄"
            )
    if tickers:
        for ticker in tickers:
            try:
                result = manager.get_company(ticker, force_refresh=refresh)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Failed to fetch {ticker}: {exc}")
                continue
            indicators.append(result.indicators)
            indicator_map[result.ticker] = result.indicators
            if result.price_history is not None:
                price_payloads[result.ticker] = result.price_history
    else:
        st.warning("Enter at least one ticker to pull live data.")
else:
    indicators = _manual_csv_upload()
    indicator_map = {item.ticker: item for item in indicators}

_persist_preferences()


scores: List[ScoreBreakdown] = []
if indicators and st.session_state["weight_config"].total_weight() > 0:
    scores = rank_companies(indicators, weight_config=st.session_state["weight_config"].normalized())


backtest_results = run_backtests(price_payloads) if price_payloads else None


tab_rank, tab_drilldown, tab_backtest, tab_portfolio, tab_history = st.tabs(
    [
        "Ranking dashboard",
        "Factor drill-down",
        "Backtesting",
        "Portfolio plan",
        "Ranking history",
    ]
)

with tab_rank:
    _render_scorecards(
        scores,
        st.session_state["theme_choice"],
        st.session_state.get("favorite_tickers", []),
        price_payloads,
    )
    if scores:
        with st.container():
            st.markdown("### Weight distribution")
            palette = THEME_PALETTES.get(st.session_state["theme_choice"], THEME_PALETTES["Aurora Dark"])
            weights = st.session_state["weight_config"].normalized().to_dict()
            weight_df = pd.DataFrame(
                {"Factor": list(weights.keys()), "Weight": list(weights.values())}
            )
            if not weight_df.empty:
                color_scale = alt.Scale(range=palette["chart_colors"])
                chart = (
                    alt.Chart(weight_df)
                    .mark_arc(innerRadius=60, stroke="white")
                    .encode(
                        theta=alt.Theta(field="Weight", type="quantitative"),
                        color=alt.Color(field="Factor", type="nominal", scale=color_scale),
                        tooltip=["Factor", alt.Tooltip("Weight", format=".0%")],
                    )
                )
        st.markdown("<div class='weight-chart-container'>", unsafe_allow_html=True)
        st.altair_chart(chart, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Adjust weights to visualize distribution.")

    if scores and backtest_results:
        if st.button("Recommend weights from backtests", icon="🧠"):
            optimization = recommend_weights(scores, backtest_results)
            if optimization is None:
                st.warning("Need more overlapping performance data to tune weights.")
            else:
                st.session_state["weight_config"] = optimization.recommended
                st.success("Applied backtest-informed weights. Rankings will refresh.")
                st.caption(
                    " • ".join(
                        f"{factor.title()}: {corr:.2f}" for factor, corr in optimization.factor_correlations.items()
                    )
                )
                st.experimental_rerun()

with tab_drilldown:
    _render_factor_drilldown(indicator_map, price_payloads)

with tab_backtest:
    _render_backtests(backtest_results)

with tab_portfolio:
    _render_portfolio(scores, indicator_map)

with tab_history:
    tracker = _get_tracker()
    history = tracker.load_history()
    if not history:
        st.info("Record at least one snapshot to view historical rankings.")
    else:
        performances = tracker.build_performance(manager)
        if not performances:
            st.warning("Snapshots exist but no price history is available to score performance yet.")
        else:
            df = pd.DataFrame(
                {
                    "Run": item.run_timestamp,
                    "Ticker": item.ticker,
                    "Composite": item.composite,
                    "Recorded price": item.recorded_price,
                    "Latest price": item.latest_price,
                    "Return since snapshot": item.return_since_capture,
                    "Target met": "🎯" if item.target_met else "",
                }
                for item in performances
            )
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "Composite": st.column_config.NumberColumn(format="%.3f"),
                    "Recorded price": st.column_config.NumberColumn(format="$%.2f"),
                    "Latest price": st.column_config.NumberColumn(format="$%.2f"),
                    "Return since snapshot": st.column_config.NumberColumn(format="%.1%"),
                },
            )

            summary = (
                df.assign(hit=df["Target met"] == "🎯")
                .groupby("Run")
                .agg(
                    ideas=("Ticker", "count"),
                    avg_return=("Return since snapshot", "mean"),
                    hit_rate=("hit", "mean"),
                )
                .reset_index()
            )
            summary["hit_rate"] = summary["hit_rate"].fillna(0.0)
            st.markdown("#### Snapshot summary")
            st.dataframe(
                summary,
                use_container_width=True,
                column_config={
                    "ideas": st.column_config.NumberColumn(format="%d"),
                    "avg_return": st.column_config.NumberColumn(format="%.1%"),
                    "hit_rate": st.column_config.NumberColumn(format="%.1%"),
                },
            )

render_footer(st.session_state["theme_choice"])
