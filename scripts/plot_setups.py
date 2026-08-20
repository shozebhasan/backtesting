#convert the XAUUSD H1 CSV 

from pathlib import Path
import pandas as pd

from backtesting.charts import (
    create_strategy_chart,
    save_strategy_chart,
)

from backtesting.indicators import (
    add_indicators,
    add_rsi_trade_mode,
)

from backtesting.strategy import (
    StrategyConfig,
    scan_trade_setups,
)


def main():

    files = sorted(
        Path("data/raw").glob(
            "XAUUSD_H1_*.csv"
        )
    )

    if not files:
        raise FileNotFoundError(
            "No XAUUSD H1 CSV found."
        )

    file = files[-1]

    print("Loading:")
    print(file)

    # =========================================
    # LOAD DATA
    # =========================================

    df = pd.read_csv(
        file,
        parse_dates=["time"],
    )

    # =========================================
    # INDICATORS
    # =========================================

    df = add_indicators(
        df,
        baseline_len=8,
        rsi_period=14,
    )

    df = add_rsi_trade_mode(
        df,
        bull_upper=70,
        bull_lower=40,
        bear_upper=60,
        bear_lower=30,
    )

    # =========================================
    # STRATEGY CONFIG
    # =========================================

    config = StrategyConfig(
        baseline_len=8,
        max_waves_to_check=10,
        entry_ratio=1.5,
        manual_rr=1.5,
        wave_trigger_type="Valid Only",
        trade_direction="both",
        enable_rsi_filter=True,
        enable_momentum_entry=True,
        momentum_stop_mode="Wave Start",
    )

    # =========================================
    # GENERATE SIGNALS
    # =========================================

    setups = scan_trade_setups(
        df,
        config,
    )

    print(
        f"Generated {len(setups)} setups."
    )

    # =========================================
    # CHART
    #
    # Start with July only.
    # Showing all 6 months at once would
    # become cluttered.
    # =========================================

    fig = create_strategy_chart(
        df=df,
        setups=setups,
        start="2026-07-01",
        end="2026-08-01",
        bars_to_extend=10,
    )

    # =========================================
    # SAVE
    # =========================================

    save_strategy_chart(
        fig,
        "data/results/"
        "XAUUSD_H1_strategy_chart.html",
    )

    # Open browser
    fig.show(
        renderer="browser",
        config={
            "scrollZoom": True,
        },
    )


if __name__ == "__main__":
    main()