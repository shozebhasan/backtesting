from pathlib import Path
import pandas as pd
from backtesting.indicators import add_indicators
from backtesting.strategy import detect_wave_points


def main():
    files = sorted(
        Path("data/raw").glob("XAUUSD_H1_*.csv")
    )

    if not files:
        raise FileNotFoundError(
            "No XAUUSD H1 data found."
        )

    file = files[-1]

    df = pd.read_csv(
        file,
        parse_dates=["time"],
    )

    df = add_indicators(
        df,
        baseline_len=8,
        rsi_period=14,
    )

    points = detect_wave_points(df)

    print(f"\nWave points detected: {len(points)}")

    print("\nLatest 20 wave points:\n")

    for point in points[-20:]:
        point_type = (
            "Q-LOW"
            if point.is_q_low
            else "Q-HIGH"
        )

        print(
            f"{point.trade_id:>4} | "
            f"{point_type:<6} | "
            f"{point.time} | "
            f"{point.price:.2f} | "
            f"confirmed bar={point.confirmed_bar}"
        )


if __name__ == "__main__":
    main()