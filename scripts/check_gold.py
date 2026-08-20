import MetaTrader5 as mt5
import pandas as pd


def main():
    if not mt5.initialize():
        raise RuntimeError(f"MT5 connection failed: {mt5.last_error()}")

    try:
        # Find possible gold symbols
        symbols = mt5.symbols_get()

        gold_symbols = [
            symbol.name
            for symbol in symbols
            if "XAU" in symbol.name.upper()
            or "GOLD" in symbol.name.upper()
        ]

        print("Possible gold symbols:")
        for symbol in gold_symbols:
            print(" -", symbol)

        if not gold_symbols:
            print("❌ No gold symbol found.")
            return

        # For now use the first result
        symbol = gold_symbols[0]

        print(f"\nUsing: {symbol}")

        # Download latest 100 hourly candles
        rates = mt5.copy_rates_from_pos(
            symbol,
            mt5.TIMEFRAME_H1,
            0,
            100,
        )

        if rates is None:
            raise RuntimeError(
                f"Could not download candles: {mt5.last_error()}"
            )

        df = pd.DataFrame(rates)

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s",
            utc=True,
        )

        print("\nLatest candles:")
        print(
            df[
                [
                    "time",
                    "open",
                    "high",
                    "low",
                    "close",
                    "tick_volume",
                ]
            ].tail(10)
        )

        print(f"\n✅ Downloaded {len(df)} H1 candles.")

    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()