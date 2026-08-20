
from datetime import datetime

import MetaTrader5 as mt5
import pandas as pd


TIMEFRAMES = {
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


def load_mt5_bars(
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame:

    if timeframe not in TIMEFRAMES:
        raise ValueError(
            f"Unsupported timeframe: {timeframe}. "
            f"Choose from {list(TIMEFRAMES)}"
        )

    if not mt5.initialize():
        raise RuntimeError(
            f"MT5 initialization failed: {mt5.last_error()}"
        )

    try:
        symbol_info = mt5.symbol_info(symbol)

        if symbol_info is None:
            raise ValueError(f"Symbol does not exist: {symbol}")

        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(
                    f"Could not select symbol {symbol}"
                )

        rates = mt5.copy_rates_range(
            symbol,
            TIMEFRAMES[timeframe],
            start,
            end,
        )

        if rates is None:
            raise RuntimeError(
                f"MT5 data request failed: {mt5.last_error()}"
            )

        df = pd.DataFrame(rates)

        if df.empty:
            raise RuntimeError(
                f"No data returned for {symbol} {timeframe}"
            )

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s",
            utc=True,
        )

        return df[
            [
                "time",
                "open",
                "high",
                "low",
                "close",
                "tick_volume",
                "spread",
                "real_volume",
            ]
        ].copy()

    finally:
        mt5.shutdown()