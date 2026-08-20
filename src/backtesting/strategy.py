from dataclasses import dataclass, field
import pandas as pd

@dataclass
class StrategyConfig:
    # Wave
    baseline_len: int = 8
    max_waves_to_check: int = 10

    # Entry
    entry_ratio: float = 1.5
    manual_rr: float = 1.5

    # Direction
    trade_direction: str = "both"

    wave_trigger_type: str = "Valid Only"

    # RSI
    enable_rsi_filter: bool = True
    rsi_period: int = 14
    rsi_bull_upper: float = 70
    rsi_bull_lower: float = 40
    rsi_bear_upper: float = 60
    rsi_bear_lower: float = 30

    # Momentum
    enable_momentum_entry: bool = True
    momentum_stop_mode: str = "wave_start"

    # Filters
    enable_extreme_filter: bool = False
    extreme_lookback: int = 5

    enable_min_move_filter: bool = False
    min_move_pct: float = 0.3

    enable_max_sl_move_filter: bool = False
    max_sl_move_pct: float = 0.5

    enable_max_active_trades: bool = False
    max_active_trades: int = 1

    # Optional filters
    enable_ichimoku_bias: bool = False
    enable_directional_bias_filter: bool = False


@dataclass
class WavePoint:
    trade_id: int

    bar_index: int
    time: pd.Timestamp

    price: float

    # True = Q-Low
    # False = Q-High
    is_q_low: bool

    # Pine stores this only for Q-High points.
    q_high_close: float | None = None

    confirmed: bool = True
    confirmed_bar: int | None = None

    invalidated: bool = False
    triggered: bool = False

    first_test_bar: int | None = None

    rsi_passed_first_test: bool = False
    rescue_momentum_triggered: bool = False

@dataclass
class TradeSetup:
    trade_id: int

    signal_type: str
    side: str

    trigger_bar: int
    trigger_time: pd.Timestamp

    entry_price: float
    stop_loss: float
    take_profit: float

    wave_start: float
    wave_length: float

    invalidated: bool

    rsi: float | None
    rsi_mode: int


@dataclass
class StrategyState:
    # Current wave construction
    in_bullish: bool = False

    temp_high: float | None = None
    temp_high_close: float | None = None
    temp_high_bar: int | None = None

    temp_low: float | None = None
    temp_low_bar: int | None = None

    # RSI state
    rsi_trade_mode: int = 0

    # Confirmed waves
    points: list[WavePoint] = field(default_factory=list)

    # IDs
    next_trade_id: int = 1


def detect_wave_points(
    df: pd.DataFrame,
) -> list[WavePoint]:
    """
    Reproduce the Q-low/Q-high construction
    from the TriggerShark Pine script.

    No entries or TP/SL yet.
    """

    state = StrategyState()

    for bar_index, row in enumerate(
        df.itertuples(index=False)
    ):
        high = float(row.high)
        low = float(row.low)
        close = float(row.close)

        bull_cross = bool(row.bull_cross)
        bear_cross = bool(row.bear_cross)

        # =====================================
        # Pine: if bullCross
        # =====================================

        if bull_cross:
            if (
                not state.in_bullish
                and state.temp_low is not None
            ):
                final_low = min(
                    low,
                    state.temp_low,
                )

                if low < state.temp_low:
                    final_low_bar = bar_index
                else:
                    final_low_bar = state.temp_low_bar

                point = WavePoint(
                    trade_id=state.next_trade_id,
                    bar_index=final_low_bar,
                    time=df.iloc[
                        final_low_bar
                    ]["time"],
                    price=final_low,
                    is_q_low=True,
                    q_high_close=None,
                    confirmed=True,
                    confirmed_bar=bar_index,
                )

                state.points.append(point)
                state.next_trade_id += 1

            state.temp_high = high
            state.temp_high_close = close
            state.temp_high_bar = bar_index

            state.temp_low = None
            state.temp_low_bar = None

            state.in_bullish = True

        # =====================================
        # Pine: if bearCross
        # =====================================

        if bear_cross:
            if (
                state.in_bullish
                and state.temp_high is not None
            ):
                final_high = max(
                    high,
                    state.temp_high,
                )

                if high > state.temp_high:
                    final_high_bar = bar_index
                else:
                    final_high_bar = (
                        state.temp_high_bar
                    )

                final_high_close = max(
                    close,
                    state.temp_high_close,
                )

                point = WavePoint(
                    trade_id=state.next_trade_id,
                    bar_index=final_high_bar,
                    time=df.iloc[
                        final_high_bar
                    ]["time"],
                    price=final_high,
                    is_q_low=False,
                    q_high_close=final_high_close,
                    confirmed=True,
                    confirmed_bar=bar_index,
                )

                state.points.append(point)
                state.next_trade_id += 1

            state.temp_low = low
            state.temp_low_bar = bar_index

            state.temp_high = None
            state.temp_high_bar = None
            state.temp_high_close = None

            state.in_bullish = False

        # =====================================
        # Pine continuously tracks extreme
        # while inside the current wave.
        # =====================================

        if state.in_bullish:
            if (
                state.temp_high is None
                or high > state.temp_high
            ):
                state.temp_high = high

            if (
                state.temp_high_close is None
                or close > state.temp_high_close
            ):
                state.temp_high_close = close

            # Intentionally mirrors your Pine.
            state.temp_high_bar = bar_index

        else:
            if (
                state.temp_low is None
                or low < state.temp_low
            ):
                state.temp_low = low

            # Intentionally mirrors your Pine.
            state.temp_low_bar = bar_index

    return state.points


def scan_trade_setups(
    df: pd.DataFrame,
    config: StrategyConfig,
) -> list[TradeSetup]:
    """
    Sequential TriggerShark scanner.

    Important:
    Processes bars chronologically so historical bars
    cannot see future wave points.
    """

    state = StrategyState()

    setups: list[TradeSetup] = []

    for bar_index, row in enumerate(
        df.itertuples(index=False)
    ):
        high = float(row.high)
        low = float(row.low)
        close = float(row.close)

        bull_cross = bool(row.bull_cross)
        bear_cross = bool(row.bear_cross)

        rsi = (
            None
            if pd.isna(row.rsi)
            else float(row.rsi)
        )

        rsi_mode = int(row.rsi_trade_mode)

        # ==================================================
        # 1. WAVE DETECTION
        # Exact ordering from Pine
        # ==================================================

        if bull_cross:
            if (
                not state.in_bullish
                and state.temp_low is not None
            ):
                final_low = min(
                    low,
                    state.temp_low,
                )

                if low < state.temp_low:
                    final_low_bar = bar_index
                else:
                    final_low_bar = state.temp_low_bar

                point = WavePoint(
                    trade_id=state.next_trade_id,
                    bar_index=final_low_bar,
                    time=df.iloc[
                        final_low_bar
                    ]["time"],
                    price=final_low,
                    is_q_low=True,
                    q_high_close=None,
                    confirmed=True,
                    confirmed_bar=bar_index,
                )

                state.points.append(point)

                state.next_trade_id += 1

            state.temp_high = high
            state.temp_high_close = close
            state.temp_high_bar = bar_index

            state.temp_low = None
            state.temp_low_bar = None

            state.in_bullish = True

        if bear_cross:
            if (
                state.in_bullish
                and state.temp_high is not None
            ):
                final_high = max(
                    high,
                    state.temp_high,
                )

                if high > state.temp_high:
                    final_high_bar = bar_index
                else:
                    final_high_bar = state.temp_high_bar

                final_high_close = max(
                    close,
                    state.temp_high_close,
                )

                point = WavePoint(
                    trade_id=state.next_trade_id,
                    bar_index=final_high_bar,
                    time=df.iloc[
                        final_high_bar
                    ]["time"],
                    price=final_high,
                    is_q_low=False,
                    q_high_close=final_high_close,
                    confirmed=True,
                    confirmed_bar=bar_index,
                )

                state.points.append(point)

                state.next_trade_id += 1

            state.temp_low = low
            state.temp_low_bar = bar_index

            state.temp_high = None
            state.temp_high_close = None
            state.temp_high_bar = None

            state.in_bullish = False

        # Keep tracking current wave extremes.
        #
        # This intentionally matches your Pine,
        # including updating temp_*_bar every bar.

        if state.in_bullish:
            if (
                state.temp_high is None
                or high > state.temp_high
            ):
                state.temp_high = high

            if (
                state.temp_high_close is None
                or close > state.temp_high_close
            ):
                state.temp_high_close = close

            state.temp_high_bar = bar_index

        else:
            if (
                state.temp_low is None
                or low < state.temp_low
            ):
                state.temp_low = low

            state.temp_low_bar = bar_index

        # ==================================================
        # Need at least:
        #
        # point i
        # point i+1
        #
        # to define a completed wave.
        # ==================================================

        if len(state.points) < 2:
            continue

        first_idx = max(
            0,
            len(state.points)
            - config.max_waves_to_check,
        )

        last_start_idx = len(state.points) - 2

        # ==================================================
        # 2. INVALIDATION
        # Pine does this BEFORE trigger detection.
        # ==================================================

        for i in range(
            first_idx,
            last_start_idx + 1,
        ):
            point = state.points[i]

            if (
                point.confirmed
                and not point.invalidated
                and not point.triggered
            ):
                if point.is_q_low:
                    # Bull wave
                    if low < point.price:
                        point.invalidated = True

                else:
                    # Bear wave
                    if high > point.price:
                        point.invalidated = True

        # ==================================================
        # 3. STRICT + MOMENTUM ENTRY CHECK
        # ==================================================

        for i in range(
            first_idx,
            last_start_idx + 1,
        ):
            point = state.points[i]
            next_point = state.points[i + 1]

            is_bull = point.is_q_low

            # ----------------------------------------------
            # Direction filter
            # ----------------------------------------------

            direction = config.trade_direction.lower()

            direction_allowed = (
                direction == "both"
                or (
                    direction in {"long", "long only"}
                    and is_bull
                )
                or (
                    direction in {"short", "short only"}
                    and not is_bull
                )
            )

            if not direction_allowed:
                continue

            # ----------------------------------------------
            # Construct wave
            # ----------------------------------------------

            wave_start = point.price

            if is_bull:
                # Your Pine specifically uses qHighClose
                # for bullish wave end.
                wave_end = next_point.q_high_close

                if wave_end is None:
                    continue

            else:
                # Bear wave uses Q-low price.
                wave_end = next_point.price

            wave_length = abs(
                wave_end - wave_start
            )

            if wave_length <= 0:
                continue

            # ----------------------------------------------
            # Entry price
            # ----------------------------------------------

            if is_bull:
                trigger_price = (
                    wave_start
                    + wave_length
                    * config.entry_ratio
                )
            else:
                trigger_price = (
                    wave_start
                    - wave_length
                    * config.entry_ratio
                )

            # ----------------------------------------------
            # Strict TP
            #
            # Matches:
            #
            # waveStart +
            # waveLen * (entryRatio * (1 + RR))
            # ----------------------------------------------

            if is_bull:
                normal_tp = (
                    wave_start
                    + wave_length
                    * (
                        config.entry_ratio
                        * (1 + config.manual_rr)
                    )
                )
            else:
                normal_tp = (
                    wave_start
                    - wave_length
                    * (
                        config.entry_ratio
                        * (1 + config.manual_rr)
                    )
                )

            # ----------------------------------------------
            # Optional min wave move filter
            # ----------------------------------------------

            move_to_1 = wave_length

            pct_move = (
                move_to_1
                / wave_start
                * 100
            )

            min_move_pass = (
                not config.enable_min_move_filter
                or pct_move
                >= config.min_move_pct
            )

            # ----------------------------------------------
            # Optional max stop-distance filter
            # ----------------------------------------------

            sl_distance = abs(
                trigger_price
                - wave_start
            )

            sl_move_pct = (
                sl_distance
                / trigger_price
                * 100
            )

            max_sl_pass = (
                not config.enable_max_sl_move_filter
                or sl_move_pct
                <= config.max_sl_move_pct
            )

            # ----------------------------------------------
            # Valid / invalid wave option
            # ----------------------------------------------

            if config.wave_trigger_type == "Both":
                trigger_allowed = True

            elif (
                config.wave_trigger_type
                == "Valid Only"
            ):
                trigger_allowed = (
                    not point.invalidated
                )

            elif (
                config.wave_trigger_type
                == "Invalidated Only"
            ):
                trigger_allowed = (
                    point.invalidated
                )

            else:
                raise ValueError(
                    "wave_trigger_type must be "
                    "'Valid Only', "
                    "'Invalidated Only' or 'Both'"
                )

            # ----------------------------------------------
            # RSI filter for THIS BAR
            # ----------------------------------------------

            if not config.enable_rsi_filter:
                rsi_pass = True

            elif is_bull:
                rsi_pass = rsi_mode == 1

            else:
                rsi_pass = rsi_mode == -1

            confirm_bar = point.confirmed_bar

            if confirm_bar is None:
                continue

            # ==================================================
            # FIRST WICK TEST
            # ==================================================

            if point.first_test_bar is None:

                # Pine:
                #
                # rel =
                # bar_index - confirmBar > 0
                # ? 0
                # : na
                #
                # So first test cannot happen on
                # confirmation bar itself.

                if bar_index <= confirm_bar:
                    continue

                if is_bull:
                    wick_test = (
                        high >= trigger_price
                    )
                else:
                    wick_test = (
                        low <= trigger_price
                    )

                if not wick_test:
                    continue

                # Remember the FIRST touch forever.

                point.first_test_bar = bar_index
                point.rsi_passed_first_test = (
                    rsi_pass
                )

                point.rescue_momentum_triggered = (
                    False
                )

                # ==================================================
                # STRICT ENTRY
                # ==================================================

                if (
                    rsi_pass
                    and trigger_allowed
                    and min_move_pass
                    and max_sl_pass
                    and not point.triggered
                ):
                    point.triggered = True

                    setup = TradeSetup(
                        trade_id=point.trade_id,
                        signal_type="STRICT",
                        side=(
                            "BUY"
                            if is_bull
                            else "SELL"
                        ),
                        trigger_bar=bar_index,
                        trigger_time=row.time,
                        entry_price=trigger_price,
                        stop_loss=wave_start,
                        take_profit=normal_tp,
                        wave_start=wave_start,
                        wave_length=wave_length,
                        invalidated=point.invalidated,
                        rsi=rsi,
                        rsi_mode=rsi_mode,
                    )

                    setups.append(setup)

            # ==================================================
            # MOMENTUM / RESCUE ENTRY
            # ==================================================

            elif (
                not point.triggered
                and not point.rescue_momentum_triggered
            ):
                if (
                    config.enable_momentum_entry
                    and not point.rsi_passed_first_test
                    and rsi_pass
                ):
                    entry_price = close

                    stop_price = wave_start

                    distance_for_tp = abs(
                        entry_price
                        - stop_price
                    )

                    # ==========================================
                    # Optional Pine:
                    # "Next Same Dir Wave"
                    # ==========================================

                    if (
                        config.momentum_stop_mode
                        == "Next Same Dir Wave"
                    ):
                        next_same = None

                        for j in range(
                            i + 1,
                            len(state.points),
                        ):
                            candidate = (
                                state.points[j]
                            )

                            if (
                                candidate.is_q_low
                                == is_bull
                                and candidate.confirmed
                            ):
                                next_same = candidate
                                break

                        if next_same is not None:
                            stop_price = (
                                next_same.price
                            )

                            distance_for_tp = abs(
                                entry_price
                                - stop_price
                            )

                    sl_distance_m = abs(
                        entry_price
                        - stop_price
                    )

                    sl_move_pct_m = (
                        sl_distance_m
                        / entry_price
                        * 100
                    )

                    max_sl_pass_m = (
                        not config.enable_max_sl_move_filter
                        or sl_move_pct_m
                        <= config.max_sl_move_pct
                    )

                    if max_sl_pass_m:

                        if is_bull:
                            momentum_tp = (
                                entry_price
                                + distance_for_tp
                                * config.manual_rr
                            )
                        else:
                            momentum_tp = (
                                entry_price
                                - distance_for_tp
                                * config.manual_rr
                            )

                        point.triggered = True

                        point.rescue_momentum_triggered = (
                            True
                        )

                        setup = TradeSetup(
                            trade_id=point.trade_id,
                            signal_type="MOMENTUM",
                            side=(
                                "BUY"
                                if is_bull
                                else "SELL"
                            ),
                            trigger_bar=bar_index,
                            trigger_time=row.time,
                            entry_price=entry_price,
                            stop_loss=stop_price,
                            take_profit=momentum_tp,
                            wave_start=wave_start,
                            wave_length=wave_length,
                            invalidated=point.invalidated,
                            rsi=rsi,
                            rsi_mode=rsi_mode,
                        )

                        setups.append(setup)

                # ==============================================
                # This odd-looking behavior exists in your Pine:
                #
                # Invalid Valid-Only waves eventually get marked
                # triggered even without producing a trade.
                #
                # We preserve it for compatibility.
                # ==============================================

                if (
                    config.wave_trigger_type
                    == "Valid Only"
                    and point.invalidated
                    and not point.triggered
                ):
                    point.triggered = True

    return setups