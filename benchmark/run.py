#!/usr/bin/env python3
"""Point-in-time weekly decision benchmark on the existing minute-candle warehouse."""

from __future__ import annotations

import argparse
from collections import deque
import json
import math
import os
import select
import statistics
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
DEFAULT_ROOT = Path("/mnt/second/trender/backtests/data")
START = "2023-02-01"
END = "2026-03-01"
PAIRS = "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,LINKUSDT,DOTUSDT,TRXUSDT,BCHUSDT,UNIUSDT"


def stamp(day: datetime) -> str:
    return day.strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_day(value: str) -> datetime:
    day = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return day.replace(tzinfo=UTC) if day.tzinfo is None else day.astimezone(UTC)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as out:
        for row in rows:
            out.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    with path.open() as src:
        return [json.loads(line) for line in src if line.strip()]


def months(start: datetime, end: datetime):
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        yield f"{year:04d}-{month:02d}.parquet"
        month += 1
        if month == 13:
            year, month = year + 1, 1


def daily_warehouse(root: Path, pair: str, start: datetime, end: datetime):
    """Return complete UTC days and hour-1 opens; reject duplicate/nonminute rows."""
    import pyarrow.parquet as pq  # Required only for prepare, on server1.

    directory = root / pair / "klines_1m"
    daily: dict[str, dict] = {}
    fills: dict[str, float] = {}
    seen: set[int] = set()
    for month in months(start, end):
        path = directory / month
        if not path.is_file():
            continue
        table = pq.read_table(path, columns=["timestamp", "open", "high", "low", "close", "volume"])
        columns = {name: table[name].to_pylist() for name in table.column_names}
        for ts, op, hi, lo, cl, vol in zip(*(columns[n] for n in ("timestamp", "open", "high", "low", "close", "volume"))):
            ts = int(ts)
            if not int(start.timestamp()) <= ts < int(end.timestamp()):
                continue
            if ts in seen or ts % 60:
                raise ValueError(f"{pair}: duplicate or unaligned minute {ts} in {path}")
            seen.add(ts)
            day = datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")
            bar = daily.setdefault(day, {"count": 0, "first": ts, "last": ts, "open": float(op),
                                         "high": float(hi), "low": float(lo), "close": float(cl), "volume": 0.0})
            bar["count"] += 1
            bar["first"] = min(bar["first"], ts)
            if ts > bar["last"]:
                bar["last"] = ts
                bar["close"] = float(cl)
            bar["high"] = max(bar["high"], float(hi))
            bar["low"] = min(bar["low"], float(lo))
            bar["volume"] += float(vol)
            if ts % 86400 == 3600:
                fills[day] = float(op)
    complete = {}
    for day, bar in daily.items():
        midnight = int(utc_day(day).timestamp())
        if bar["count"] == 1440 and bar["first"] == midnight and bar["last"] == midnight + 86340:
            complete[day] = {k: v for k, v in bar.items() if k not in ("count", "first", "last")}
    return complete, fills, {"minutes": len(seen), "complete_days": len(complete),
                              "incomplete_days": len(daily) - len(complete), "files_found": sum((directory / m).is_file() for m in months(start, end))}


def build_pair(pair: str, days: dict[str, dict], fills: dict[str, float], start: datetime, end: datetime):
    events, settlements = [], []
    decision = start
    while decision.weekday() != 0:
        decision += timedelta(days=1)
    decision = max(decision, start + timedelta(days=28))
    while decision.weekday() != 0:
        decision += timedelta(days=1)
    skipped = 0
    while decision + timedelta(days=7) < end:
        history = [(decision - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(28, 0, -1)]
        key, next_key = decision.strftime("%Y-%m-%d"), (decision + timedelta(days=7)).strftime("%Y-%m-%d")
        if all(day in days for day in history):
            closes = [days[day]["close"] for day in history]
            log_returns = [math.log(b / a) for a, b in zip(closes[:-1], closes[1:])]
            event_id = f"{pair}:{key}"  # Replaced by opaque sequential ID before export.
            return_7d = closes[-1] / closes[-8] - 1
            return_27d = closes[-1] / closes[0] - 1
            volatility = statistics.stdev(log_returns)
            state = ("Classify whether the next seven-day return is up or down. "
                     "Use only these completed daily candles, expressed as relative returns. "
                     f"Trailing 7-day return: {return_7d:+.6f}; trailing 27-day return: {return_27d:+.6f}; "
                     f"27-day daily log-return volatility: {volatility:.6f}. "
                     "Daily log returns oldest to newest: " + ", ".join(f"{value:+.6f}" for value in log_returns) + ".")
            events.append({"id": event_id, "state": state})
            # The outcome needs only the two scheduled minute opens. Requiring
            # complete future daily bars would select weeks using information
            # unavailable at decision time and bias the scored sample.
            if key in fills and next_key in fills:
                settlements.append({"id": event_id, "pair": pair, "asof": stamp(decision),
                                    "fill_at": stamp(decision + timedelta(hours=1)), "fill_open": fills[key],
                                    "exit_at": stamp(decision + timedelta(days=7, hours=1)),
                                    "exit_open": fills[next_key], "up": int(fills[next_key] > fills[key]),
                                    "momentum_7d": return_7d})
            else:
                skipped += 1
        else:
            skipped += 1
        decision += timedelta(days=7)
    return events, settlements, skipped


def prepare(args):
    start, end = utc_day(args.start), utc_day(args.end)
    if start.time() != datetime.min.time() or end.time() != datetime.min.time() or end - start < timedelta(days=43):
        raise ValueError("start/end must be UTC midnight with at least 43 days between them")
    events, settlements, coverage = [], [], {}
    for pair in args.pairs.split(","):
        pair = pair.strip().upper()
        if not pair or not pair.endswith("USDT"):
            raise ValueError("pairs must be comma-separated USDT symbols")
        days, fills, counts = daily_warehouse(args.root, pair, start - timedelta(days=29), end + timedelta(days=1))
        pair_events, pair_settlements, skipped = build_pair(pair, days, fills, start, end)
        events.extend(pair_events)
        settlements.extend(pair_settlements)
        coverage[pair] = {**counts, "eligible_decisions": len(pair_events),
                          "scored_decisions": len(pair_settlements),
                          "unscorable_events": len(pair_events) - len(pair_settlements),
                          "excluded_weeks": skipped}
    if not events:
        raise ValueError("no complete decision windows; check warehouse path and date coverage")
    # Adapters see every decision eligible from past data, even if a future gap
    # makes its outcome unscorable. Pair and timestamp stay private.
    events.sort(key=lambda row: (row["id"].split(":")[1], row["id"].split(":")[0]))
    id_map = {event["id"]: f"e{index:06d}" for index, event in enumerate(events, 1)}
    for event in events:
        event["id"] = id_map[event["id"]]
    for settlement in settlements:
        settlement["id"] = id_map[settlement["id"]]
    settlements.sort(key=lambda row: row["id"])
    write_jsonl(args.events, events)
    write_jsonl(args.settlements, settlements)
    write_json(args.coverage, {"source_root": str(args.root), "start": stamp(start), "end": stamp(end),
                               "pairs": coverage, "events": len(events)})
    print(f"prepared {len(events)} decisions; coverage: {args.coverage}")


def read_adapter_line(stream, timeout_seconds: float, event_id: str) -> str:
    """Read one complete UTF-8 line without allowing a partial line to bypass timeout."""
    deadline = time.monotonic() + timeout_seconds
    data = bytearray()
    while b"\n" not in data:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([stream], [], [], remaining)[0]:
            raise TimeoutError(f"adapter timed out for {event_id} after {timeout_seconds}s")
        chunk = os.read(stream.fileno(), 65536)
        if not chunk:
            raise RuntimeError(f"adapter exited before responding to {event_id}")
        data.extend(chunk)
        if len(data) > 1_000_000:
            raise ValueError(f"adapter response too large for {event_id}")
    line, extra = bytes(data).split(b"\n", 1)
    if extra.strip():
        raise ValueError(f"adapter emitted unsolicited output after {event_id}")
    return line.decode("utf-8")


def invoke(args):
    """Stream one causal JSON request per line to an adapter, timing each response."""
    events = read_jsonl(args.events)
    existing = read_jsonl(args.output) if getattr(args, "resume", False) and args.output.exists() else []
    if args.output.exists() and not getattr(args, "resume", False):
        raise FileExistsError(f"response file exists; use --resume to continue: {args.output}")
    if [row.get("id") for row in existing] != [row.get("id") for row in events[:len(existing)]]:
        raise ValueError("existing responses are not an exact event prefix")
    if len(existing) == len(events):
        print(f"already recorded {len(existing)} responses: {args.output}")
        return
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise ValueError("command after -- is required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None,
                          bufsize=0) as process:
        try:
            with args.output.open("a" if existing else "w") as output:
                for event in events[len(existing):]:
                    started = time.perf_counter()
                    process.stdin.write((json.dumps(event, allow_nan=False) + "\n").encode("utf-8"))
                    process.stdin.flush()
                    line = read_adapter_line(process.stdout, args.timeout_seconds, event["id"])
                    response = json.loads(line)
                    if response.get("id") != event["id"]:
                        raise ValueError(f"adapter response id mismatch for {event['id']}")
                    response["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
                    output.write(json.dumps(response, sort_keys=True, allow_nan=False) + "\n")
                    output.flush()
                    os.fsync(output.fileno())
            process.stdin.close()
            if process.wait() != 0:
                raise RuntimeError(f"adapter exited {process.returncode}")
        except BaseException:
            process.kill()
            process.wait()
            raise
    print(f"recorded {len(events)} responses: {args.output}")


def valid_decision(row: dict) -> dict:
    if "prediction" in row:
        if row["prediction"] not in ("up", "down"):
            raise ValueError(f"{row['id']}: prediction must be up or down")
        probabilities = row.get("probabilities")
        if probabilities is not None:
            up, down = float(probabilities["up"]), float(probabilities["down"])
            if not all(math.isfinite(value) and 0 <= value <= 1 for value in (up, down)) or abs(up + down - 1) > 1e-6:
                raise ValueError(f"{row['id']}: probabilities must sum to 1")
            if row["prediction"] != ("up" if up > down else "down"):
                raise ValueError(f"{row['id']}: prediction disagrees with probabilities")
            row = {**row, "target_weight": float(up > down), "prob_up": up}
        else:
            row = {**row, "target_weight": float(row["prediction"] == "up")}
    result = {"id": row["id"], "target_weight": float(row["target_weight"])}
    if not math.isfinite(result["target_weight"]) or not 0 <= result["target_weight"] <= 1:
        raise ValueError(f"{row['id']}: target_weight must be finite in [0,1]")
    if "prob_up" in row and row["prob_up"] is not None:
        result["prob_up"] = float(row["prob_up"])
        if not math.isfinite(result["prob_up"]) or not 0 <= result["prob_up"] <= 1:
            raise ValueError(f"{row['id']}: prob_up must be finite in [0,1]")
    if "latency_ms" in row:
        result["latency_ms"] = float(row["latency_ms"])
        if not math.isfinite(result["latency_ms"]) or result["latency_ms"] < 0:
            raise ValueError(f"{row['id']}: invalid latency_ms")
    return result


def replay(rows: list[dict], decisions: dict[str, dict], fee_bps: float, slippage_bps: float):
    """Long/cash portfolio, rebalanced at delayed minute open and liquidated at last exit."""
    cash, units, turnover, trades = 1.0, 0.0, 0.0, 0
    curve, ledger = [1.0], []
    cost = (fee_bps + slippage_bps) / 10000
    for index, row in enumerate(rows):
        price = row["fill_open"]
        decision = decisions[row["id"]]
        before = cash + units * price
        desired = before * decision["target_weight"]
        delta_value = desired - units * price
        # Exact cash-feasible buy; sell proceeds pay the same one-way cost.
        if delta_value > 0:
            bought = min(delta_value / (1 + cost), cash / (1 + cost))
            units += bought / price
            cash -= bought * (1 + cost)
            traded = bought
        else:
            sold = min(-delta_value, units * price)
            units -= sold / price
            cash += sold * (1 - cost)
            traded = sold
        if traded > 1e-12:
            trades += 1
            turnover += traded
        exit_equity = cash + units * row["exit_open"]
        # Liquidate only after the final scored interval or a skipped week.
        last_segment = index == len(rows) - 1 or rows[index + 1]["fill_at"] != row["exit_at"]
        if last_segment and units:
            exit_equity -= units * row["exit_open"] * cost
            turnover += units * row["exit_open"]
            trades += 1
            cash, units = exit_equity, 0.0
        curve.append(exit_equity)
        ledger.append({"id": row["id"], "pair": row["pair"], "asof": row["asof"],
                       "fill_at": row["fill_at"], "exit_at": row["exit_at"],
                       "target_weight": decision["target_weight"], "equity": exit_equity,
                       "trade_value": traded})
    peak, drawdown = 1.0, 0.0
    for value in curve:
        peak = max(peak, value)
        drawdown = max(drawdown, 1 - value / peak)
    up_rows = [(d["target_weight"] > 0.5, r["up"]) for r in rows for d in [decisions[r["id"]]]]
    probability_rows = [(d["prob_up"], r["up"]) for r in rows for d in [decisions[r["id"]]] if "prob_up" in d]
    latencies = sorted(d["latency_ms"] for r in rows for d in [decisions[r["id"]]] if "latency_ms" in d)
    percentile = lambda p: latencies[math.ceil(p * len(latencies)) - 1] if latencies else None
    metrics = {"n_decisions": len(rows), "accuracy": sum(p == bool(y) for p, y in up_rows) / len(up_rows),
               "brier": sum((p - y) ** 2 for p, y in probability_rows) / len(probability_rows) if len(probability_rows) == len(rows) else None,
               "return_pct": (curve[-1] - 1) * 100, "max_drawdown_pct": drawdown * 100,
               "trade_count": trades, "latency_ms_p50": percentile(0.5), "latency_ms_p95": percentile(0.95)}
    return metrics, ledger


def grouped(settlements: list[dict]):
    groups = {}
    for row in settlements:
        for period in ("full", row["asof"][:4]):
            groups.setdefault((row["pair"], period), []).append(row)
    for rows in groups.values():
        rows.sort(key=lambda row: row["asof"])
    return groups


def check_model_deadlines(events: list[dict], choices: dict[str, dict], simultaneous: int) -> None:
    """Conservatively bound serial completion of potentially simultaneous requests."""
    window = deque()
    total = 0.0
    for event in events:
        latency = choices[event["id"]].get("latency_ms")
        if latency is None or latency > 3_600_000:
            raise ValueError("all responses need measured latency within the one-hour fill delay")
        window.append(latency)
        total += latency
        if len(window) > simultaneous:
            total -= window.popleft()
        if total > 3_600_000:
            raise ValueError("a group of potentially simultaneous responses misses the one-hour fill delay")


def evaluate(args):
    events = read_jsonl(args.events)
    settlements = read_jsonl(args.settlements)
    event_ids = {row["id"] for row in events}
    settlement_ids = {row["id"] for row in settlements}
    if len(event_ids) != len(events) or len(settlement_ids) != len(settlements) or not settlement_ids <= event_ids:
        raise ValueError("settlements must be a unique subset of event ids")
    if not settlements:
        raise ValueError("no scorable settlement rows")
    models = json.loads(args.models.read_text())["models"]
    model_map = {model["id"]: model for model in models}
    if len(model_map) != len(models):
        raise ValueError("duplicate model id")
    responses = {}
    for spec in args.responses:
        model_id, separator, filename = spec.partition("=")
        if not separator or model_id not in model_map or model_id in responses:
            raise ValueError(f"invalid response spec: {spec}")
        rows = read_jsonl(Path(filename))
        by_id = {row["id"]: valid_decision(row) for row in rows}
        if len(by_id) != len(rows) or set(by_id) != event_ids:
            raise ValueError(f"{model_id}: response ids must match all prepared events exactly")
        try:
            check_model_deadlines(events, by_id, len({row["pair"] for row in settlements}))
        except ValueError as error:
            raise ValueError(f"{model_id}: {error}") from error
        responses[model_id] = by_id
    groups = grouped(settlements)
    baselines, runs, ledgers = [], [], []
    for (pair, period), rows in sorted(groups.items()):
        for name in ("hold", "momentum_7d"):
            choices = {r["id"]: {"target_weight": 1.0 if name == "hold" or
                       r["momentum_7d"] > 0 else 0.0} for r in rows}
            metrics, _ = replay(rows, choices, args.fee_bps, args.slippage_bps)
            baselines.append({"name": name, "pair": pair, "period": period,
                              **{key: metrics[key] for key in ("return_pct", "max_drawdown_pct", "trade_count")}})
        for model_id, choices in responses.items():
            metrics, ledger = replay(rows, choices, args.fee_bps, args.slippage_bps)
            runs.append({"model_id": model_id, "pair": pair, "period": period, **metrics})
            if period == "full":
                ledgers.extend({"model_id": model_id, **entry} for entry in ledger)
    public_models = [{key: model.get(key) for key in ("id", "name", "source_url", "source_sha", "weights_url", "weights_sha") if key in model}
                     | {"status": "measured" if model["id"] in responses else model.get("status", "pending"),
                        "reason": None if model["id"] in responses else model.get("reason")}
                     for model in models]
    summary = {"schema_version": 1, "generated_at": stamp(datetime.now(UTC)),
               "status": "complete" if len(responses) == len(models) else "running",
               "methodology": {"decision_schedule": "Monday 00:00 UTC, nonoverlapping 7-day intervals",
                               "features": "28 complete UTC daily candles ending Sunday 23:59 UTC",
                               "fills": "open of Monday 01:00 UTC minute; exit at next Monday 01:00 UTC",
                               "max_model_latency_ms": 3_600_000,
                               "simultaneous_request_rule": "sum of every rolling group of up to the number of scored pairs must fit within one hour under serial execution",
                               "drawdown_sampling": "weekly exit equity marks; intraweek excursions not measured",
                               "policy": "long/cash target weight in [0,1]; independent pair portfolios; reset at year boundaries for yearly rows",
                               "fee_bps_per_side": args.fee_bps, "slippage_bps_per_side": args.slippage_bps,
                               "market": "legacy Binance USDT perpetual futures candle proxy; funding and spread unavailable"},
               "models": public_models, "runs": runs, "baselines": baselines,
               "provenance": {"event_count": len(events), "model_count": len(models), "measured_model_count": len(responses)}}
    write_json(args.output, summary)
    if args.ledger:
        write_jsonl(args.ledger, ledgers)
    print(f"summary: {len(runs)} model rows, {len(baselines)} baseline rows, status={summary['status']}")


def audit(args):
    """Check that future settlement changes do not alter previous decisions or equity."""
    events, settlements = read_jsonl(args.events), read_jsonl(args.settlements)
    if any(set(event) != {"id", "state"} for event in events):
        raise ValueError("model-facing events may contain only id and state")
    if not {row["id"] for row in settlements} <= {event["id"] for event in events}:
        raise ValueError("settlement IDs are absent from events")
    groups = grouped(settlements)
    checked = 0
    for (pair, period), rows in groups.items():
        if period != "full" or len(rows) < 3:
            continue
        choices = {row["id"]: {"target_weight": float(row["momentum_7d"] > 0)} for row in rows}
        for length in sorted({1, len(rows) // 2, len(rows) - 1}):
            original, original_ledger = replay(rows, choices, args.fee_bps, args.slippage_bps)
            changed = [dict(row) for row in rows]
            for row in changed[length:]:
                row["fill_open"] *= 7
                row["exit_open"] *= 7
                row["up"] = 1 - row["up"]
            altered, altered_ledger = replay(changed, choices, args.fee_bps, args.slippage_bps)
            if original_ledger[:length] != altered_ledger[:length]:
                raise AssertionError(f"future mutation affected prefix: {pair} {length}")
            # Truncation can force a liquidation at the boundary; earlier marks must agree.
            _, truncated_ledger = replay(rows[:length], choices, args.fee_bps, args.slippage_bps)
            if original_ledger[:length - 1] != truncated_ledger[:length - 1]:
                raise AssertionError(f"truncation affected earlier marks: {pair} {length}")
            checked += 1
    if not checked:
        raise ValueError("audit needs at least one pair with 3 decisions")
    print(f"passed {checked} prefix/future-mutation checks")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command_name", required=True)
    prep = commands.add_parser("prepare", help="read warehouse on server1 and create causal inputs plus private settlements")
    prep.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    prep.add_argument("--start", default=START)
    prep.add_argument("--end", default=END)
    prep.add_argument("--pairs", default=PAIRS)
    prep.add_argument("--events", type=Path, required=True)
    prep.add_argument("--settlements", type=Path, required=True)
    prep.add_argument("--coverage", type=Path, required=True)
    prep.set_defaults(func=prepare)
    inv = commands.add_parser("invoke", help="run an adapter over causal JSONL requests")
    inv.add_argument("--events", type=Path, required=True)
    inv.add_argument("--output", type=Path, required=True)
    inv.add_argument("--resume", action="store_true", help="continue an exact response prefix after interruption")
    inv.add_argument("--timeout-seconds", type=float, default=900.0)
    inv.add_argument("command", nargs=argparse.REMAINDER)
    inv.set_defaults(func=invoke)
    ev = commands.add_parser("evaluate", help="score response JSONL and publish aggregate summary")
    ev.add_argument("--events", type=Path, required=True)
    ev.add_argument("--settlements", type=Path, required=True)
    ev.add_argument("--models", type=Path, default=Path(__file__).with_name("models.json"))
    ev.add_argument("--responses", nargs="*", default=[], metavar="MODEL_ID=FILE")
    ev.add_argument("--fee-bps", type=float, default=5.0)
    ev.add_argument("--slippage-bps", type=float, default=4.0)
    ev.add_argument("--ledger", type=Path)
    ev.add_argument("--output", type=Path, required=True)
    ev.set_defaults(func=evaluate)
    aud = commands.add_parser("audit", help="verify replay prefix invariance")
    aud.add_argument("--events", type=Path, required=True)
    aud.add_argument("--settlements", type=Path, required=True)
    aud.add_argument("--fee-bps", type=float, default=5.0)
    aud.add_argument("--slippage-bps", type=float, default=4.0)
    aud.set_defaults(func=audit)
    args = parser.parse_args()
    if hasattr(args, "fee_bps") and (args.fee_bps < 0 or args.slippage_bps < 0):
        parser.error("costs must be nonnegative")
    if args.command_name == "invoke" and args.timeout_seconds <= 0:
        parser.error("timeout-seconds must be positive")
    if args.command_name == "invoke" and args.command[:1] == ["--"]:
        args.command.pop(0)
    args.func(args)


if __name__ == "__main__":
    main()
