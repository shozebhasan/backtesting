from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from backtesting.strategy import TradeSetup


def create_strategy_chart(
    df: pd.DataFrame,
    setups: list[TradeSetup],
    start: str | None = None,
    end: str | None = None,
    bars_to_extend: int = 10,
) -> go.Figure:
    """
    Interactive candlestick chart showing:

    - XAUUSD candles
    - Kijun baseline
    - Strict BUY/SELL entries
    - Momentum BUY/SELL entries
    - Entry / SL / TP levels
    """

    chart_df = df.copy()

    # -----------------------------------------
    # Optional visible date range
    # -----------------------------------------

    if start is not None:
        start_ts = pd.Timestamp(start, tz="UTC")
        chart_df = chart_df[
            chart_df["time"] >= start_ts
        ]

    if end is not None:
        end_ts = pd.Timestamp(end, tz="UTC")
        chart_df = chart_df[
            chart_df["time"] <= end_ts
        ]

    # -----------------------------------------
    # Candles
    # -----------------------------------------

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=chart_df["time"],
            open=chart_df["open"],
            high=chart_df["high"],
            low=chart_df["low"],
            close=chart_df["close"],
            name="XAUUSD",
        )
    )

    # -----------------------------------------
    # Kijun / baseline
    # -----------------------------------------

    fig.add_trace(
        go.Scatter(
            x=chart_df["time"],
            y=chart_df["baseline"],
            mode="lines",
            name="Kijun baseline",
        )
    )

    # -----------------------------------------
    # Only setups inside visible range
    # -----------------------------------------

    visible_setups = []

    for setup in setups:
        if start is not None:
            if setup.trigger_time < pd.Timestamp(
                start,
                tz="UTC",
            ):
                continue

        if end is not None:
            if setup.trigger_time > pd.Timestamp(
                end,
                tz="UTC",
            ):
                continue

        visible_setups.append(setup)

    # -----------------------------------------
    # Entry markers
    # -----------------------------------------

    groups = {
        "Strict BUY": [],
        "Strict SELL": [],
        "Momentum BUY": [],
        "Momentum SELL": [],
    }

    for setup in visible_setups:
        key = (
            f"{setup.signal_type.title()} "
            f"{setup.side}"
        )

        groups[key].append(setup)

    marker_symbols = {
        "Strict BUY": "triangle-up",
        "Strict SELL": "triangle-down",
        "Momentum BUY": "star-triangle-up",
        "Momentum SELL": "star-triangle-down",
    }

    for name, group in groups.items():
        if not group:
            continue

        fig.add_trace(
            go.Scatter(
                x=[
                    s.trigger_time
                    for s in group
                ],
                y=[
                    s.entry_price
                    for s in group
                ],
                mode="markers",
                name=name,
                marker={
                    "symbol": marker_symbols[name],
                    "size": 13,
                },
                text=[
                    (
                        f"Trade #{s.trade_id}<br>"
                        f"{s.signal_type} {s.side}<br>"
                        f"Entry: {s.entry_price:.2f}<br>"
                        f"SL: {s.stop_loss:.2f}<br>"
                        f"TP: {s.take_profit:.2f}<br>"
                        f"RSI: "
                        f"{s.rsi:.2f}<br>"
                        f"RSI mode: {s.rsi_mode}"
                    )
                    for s in group
                ],
                hovertemplate=(
                    "%{text}"
                    "<extra></extra>"
                ),
            )
        )

    # -----------------------------------------
    # Entry / SL / TP lines
    #
    # Similar idea to barsToExtend in Pine.
    # -----------------------------------------

    for setup in visible_setups:

        end_bar = min(
            setup.trigger_bar
            + bars_to_extend,
            len(df) - 1,
        )

        line_end_time = df.iloc[
            end_bar
        ]["time"]

        # Entry
        fig.add_trace(
            go.Scatter(
                x=[
                    setup.trigger_time,
                    line_end_time,
                ],
                y=[
                    setup.entry_price,
                    setup.entry_price,
                ],
                mode="lines",
                line={"dash": "solid"},
                showlegend=False,
                hoverinfo="skip",
            )
        )

        # Stop Loss
        fig.add_trace(
            go.Scatter(
                x=[
                    setup.trigger_time,
                    line_end_time,
                ],
                y=[
                    setup.stop_loss,
                    setup.stop_loss,
                ],
                mode="lines",
                line={"dash": "dot"},
                showlegend=False,
                hoverinfo="skip",
            )
        )

        # Take Profit
        fig.add_trace(
            go.Scatter(
                x=[
                    setup.trigger_time,
                    line_end_time,
                ],
                y=[
                    setup.take_profit,
                    setup.take_profit,
                ],
                mode="lines",
                line={"dash": "dash"},
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # -----------------------------------------
    # Layout
    # -----------------------------------------

    fig.update_layout(
        title=(
            "TriggerShark Python Backtest — "
            "XAUUSD H1"
        ),
        xaxis_title="Time (UTC)",
        yaxis_title="Gold Price",
        height=850,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )

    return fig


def save_strategy_chart(
    fig: go.Figure,
    filename: str,
) -> None:

    output = Path(filename)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.write_html(
        output,
        include_plotlyjs=True,
    )

    print(f"Chart saved to: {output}")