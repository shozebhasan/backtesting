import numpy as np
import pandas as pd


def pine_rsi(close: pd.Series, length: int = 14) -> pd.Series:
    """
    Wilder RSI implementation intended to match Pine ta.rsi()
    on normal OHLC data without missing bars.
    """
    close = close.astype(float)

    delta = close.diff()

    gains = delta.clip(lower=0.0).to_numpy()
    losses = (-delta.clip(upper=0.0)).to_numpy()

    result = np.full(len(close), np.nan, dtype=float)

    if len(close) <= length:
        return pd.Series(result, index=close.index, name="rsi")

    # First delta is NaN, so first RSI uses `length`
    # actual price changes.
    avg_gain = np.mean(gains[1 : length + 1])
    avg_loss = np.mean(losses[1 : length + 1])

    def calculate_rsi(gain: float, loss: float) -> float:
        if loss == 0 and gain == 0:
            return 50.0

        if loss == 0:
            return 100.0

        if gain == 0:
            return 0.0

        rs = gain / loss
        return 100.0 - (100.0 / (1.0 + rs))

    result[length] = calculate_rsi(
        avg_gain,
        avg_loss,
    )

    for i in range(length + 1, len(close)):
        avg_gain = (
            avg_gain * (length - 1) + gains[i]
        ) / length

        avg_loss = (
            avg_loss * (length - 1) + losses[i]
        ) / length

        result[i] = calculate_rsi(
            avg_gain,
            avg_loss,
        )

    return pd.Series(
        result,
        index=close.index,
        name="rsi",
    )


def add_indicators(
    df: pd.DataFrame,
    baseline_len: int = 8,
    rsi_period: int = 14,
) -> pd.DataFrame:
    df = df.copy()

    # Pine:
    # donchianHigh = ta.highest(high, baselineLen)
    # donchianLow  = ta.lowest(low, baselineLen)

    df["donchian_high"] = (
        df["high"]
        .rolling(
            window=baseline_len,
            min_periods=baseline_len,
        )
        .max()
    )

    df["donchian_low"] = (
        df["low"]
        .rolling(
            window=baseline_len,
            min_periods=baseline_len,
        )
        .min()
    )

    # Pine:
    # baseline = (donchianHigh + donchianLow) / 2

    df["baseline"] = (df["donchian_high"] + df["donchian_low"]) / 2.0

    # Pine:
    # bullCross = ta.crossover(close, baseline)
    #
    # Current close > current baseline
    # AND
    # previous close <= previous baseline

    df["bull_cross"] = (
        (df["close"] > df["baseline"])
        & (
            df["close"].shift(1)
            <= df["baseline"].shift(1)
        )
    )

    # Pine:
    # bearCross = ta.crossunder(close, baseline)

    df["bear_cross"] = (
        (df["close"] < df["baseline"])
        & (
            df["close"].shift(1)
            >= df["baseline"].shift(1)
        )
    )

    # Pine:
    # ta.rsi(close, rsiPeriod)

    df["rsi"] = pine_rsi(
        df["close"],
        length=rsi_period,
    )

    return df

def add_rsi_trade_mode(
    df: pd.DataFrame,
    bull_upper: float = 70,
    bull_lower: float = 40,
    bear_upper: float = 60,
    bear_lower: float = 30,
) -> pd.DataFrame:
    """
    Reproduces TriggerShark's persistent RSI state machine.

    0  = neutral
    1  = bullish RSI regime
    -1 = bearish RSI regime
    """

    df = df.copy()

    modes: list[int] = []
    mode = 0

    for rsi in df["rsi"]:
        if pd.isna(rsi):
            modes.append(mode)
            continue

        # Pine:
        # if rsiTradeMode == 0 and rsiValue >= rsiBullUpper
        if mode == 0 and rsi >= bull_upper:
            mode = 1

        # Pine:
        # if rsiTradeMode == 0 and rsiValue <= rsiBearLower
        if mode == 0 and rsi <= bear_lower:
            mode = -1

        # Pine:
        # if rsiTradeMode == 1 and rsiValue < rsiBullLower
        if mode == 1 and rsi < bull_lower:
            mode = 0

        # Pine:
        # if rsiTradeMode == -1 and rsiValue > rsiBearUpper
        if mode == -1 and rsi > bear_upper:
            mode = 0

        modes.append(mode)

    df["rsi_trade_mode"] = modes

    return df