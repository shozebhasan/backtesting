from pathlib import Path
import pandas as pd
from backtesting.indicators import add_indicators, add_rsi_trade_mode


def main():
    files = sorted(
        Path("data/raw").glob("XAUUSD_H1_*.csv")
    )

    if not files:
        raise FileNotFoundError(
            "No XAUUSD H1 CSV found in data/raw"
        )

    file = files[-1]

    print("Loading:")
    print(file)

    df = pd.read_csv(
        file,
        parse_dates=["time"],
    )

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

    print("\nLatest values:")

    print(
        df[
            [
                "time",
                "close",
                "baseline",
                "rsi",
                "bull_cross",
                "bear_cross",
                "rsi_trade_mode"
            ]
        ].tail(20)
    )

    print("\nSummary:")
    print("Rows:", len(df))
    print(
        "Bull crosses:",
        int(df["bull_cross"].sum()),
    )
    print(
        "Bear crosses:",
        int(df["bear_cross"].sum()),
    )


if __name__ == "__main__":
    main()