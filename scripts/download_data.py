from datetime import datetime, timezone
from pathlib import Path

from backtesting.data_loader import load_mt5_bars


SYMBOL = "XAUUSD"
TIMEFRAME = "H1"

START = datetime(
    2026,
    2,
    1,
    tzinfo=timezone.utc,
)

END = datetime(
    2026,
    8,
    1,
    tzinfo=timezone.utc,
)


def main():
    print(
        f"Downloading {SYMBOL} {TIMEFRAME} "
        f"from {START} to {END}..."
    )

    df = load_mt5_bars(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        start=START,
        end=END,
    )

    print("\nFirst 5 candles:")
    print(df.head())

    print("\nLast 5 candles:")
    print(df.tail())

    print("\nDataset information:")
    print("Rows:", len(df))
    print("Start:", df["time"].min())
    print("End:", df["time"].max())

    output_dir = Path("data/raw")
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / f"{SYMBOL}_{TIMEFRAME}_2026-02-01_2026-08-01.csv"
    )

    df.to_csv(
        output_file,
        index=False,
    )

    print(f"\n✅ Saved to: {output_file}")


if __name__ == "__main__":
    main()