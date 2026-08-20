from pathlib import Path

import pandas as pd

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

    df = pd.read_csv(
        file,
        parse_dates=["time"],
    )

    # ------------------------------------------
    # Indicators
    # ------------------------------------------

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

    # ------------------------------------------
    # Exact/default Pine configuration
    # ------------------------------------------

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

    # ------------------------------------------
    # Scan historical bars
    # ------------------------------------------

    setups = scan_trade_setups(
        df,
        config,
    )

    strict = [
        setup
        for setup in setups
        if setup.signal_type == "STRICT"
    ]

    momentum = [
        setup
        for setup in setups
        if setup.signal_type == "MOMENTUM"
    ]

    buys = [
        setup
        for setup in setups
        if setup.side == "BUY"
    ]

    sells = [
        setup
        for setup in setups
        if setup.side == "SELL"
    ]

    print("\n==========================")
    print("SETUP SUMMARY")
    print("==========================")

    print("Total:", len(setups))
    print("Strict:", len(strict))
    print("Momentum:", len(momentum))
    print("BUY:", len(buys))
    print("SELL:", len(sells))

    print("\nLatest 20 setups:\n")

    for setup in setups[-20:]:
        print(
            f"#{setup.trade_id:<4} "
            f"{setup.signal_type:<8} "
            f"{setup.side:<4} | "
            f"{setup.trigger_time} | "
            f"entry={setup.entry_price:.2f} | "
            f"SL={setup.stop_loss:.2f} | "
            f"TP={setup.take_profit:.2f} | "
            f"RSI={setup.rsi:.2f} | "
            f"mode={setup.rsi_mode}"
        )


if __name__ == "__main__":
    main()