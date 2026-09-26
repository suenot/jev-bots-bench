import unittest
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from benchmark.run import build_pair, evaluate, prepare, read_jsonl, replay, valid_decision, write_jsonl


class BenchmarkTests(unittest.TestCase):
    def synthetic(self):
        start = datetime(2023, 2, 1, tzinfo=timezone.utc)
        end = start + timedelta(days=90)
        days, fills = {}, {}
        for offset in range(91):
            day = start + timedelta(days=offset)
            key = day.strftime("%Y-%m-%d")
            close = 100 + offset
            days[key] = {"open": close - 0.5, "high": close + 1, "low": close - 1,
                         "close": close, "volume": 10.0}
            fills[key] = close + 0.2
        return start, end, days, fills

    def test_requests_are_private_and_prefix_invariant(self):
        start, end, days, fills = self.synthetic()
        events, settlements, _ = build_pair("SOLUSDT", days, fills, start, end)
        self.assertGreaterEqual(len(events), 3)
        for event in events:
            self.assertEqual(set(event), {"id", "state"})
            self.assertNotIn("SOLUSDT", event["state"])
            self.assertNotIn("2023", event["state"])
        mutated_days = {key: dict(value) for key, value in days.items()}
        mutated_fills = dict(fills)
        cutoff = start + timedelta(days=65)
        for key in days:
            if key >= cutoff.strftime("%Y-%m-%d"):
                mutated_days[key]["close"] *= 7
                mutated_fills[key] *= 7
        changed_events, changed_settlements, _ = build_pair("SOLUSDT", mutated_days, mutated_fills, start, end)
        event_prefix = lambda rows: [row for row in rows if row["id"].split(":")[-1] < cutoff.strftime("%Y-%m-%d")]
        settled_prefix = lambda rows: [row for row in rows if row["exit_at"][:10] < cutoff.strftime("%Y-%m-%d")]
        self.assertEqual(event_prefix(events), event_prefix(changed_events))
        self.assertEqual(settled_prefix(settlements), settled_prefix(changed_settlements))

    def test_replay_costs_and_gap_liquidation(self):
        rows = [{"id": "a", "pair": "SOLUSDT", "asof": "2023-03-01", "fill_at": "2023-03-01",
                 "exit_at": "2023-03-08", "fill_open": 100, "exit_open": 110, "up": 1},
                {"id": "b", "pair": "SOLUSDT", "asof": "2023-03-15", "fill_at": "2023-03-15",
                 "exit_at": "2023-03-22", "fill_open": 100, "exit_open": 90, "up": 0}]
        decisions = {key: {"target_weight": 1.0, "prob_up": 0.8} for key in ("a", "b")}
        metrics, ledger = replay(rows, decisions, 5, 4)
        self.assertEqual(metrics["trade_count"], 4)
        self.assertLess(metrics["return_pct"], 0)
        self.assertEqual(len(ledger), 2)

    def test_prediction_contract(self):
        self.assertEqual(valid_decision({"id": "a", "prediction": "up",
                                         "probabilities": {"up": 0.7, "down": 0.3}})["target_weight"], 1)
        with self.assertRaises(ValueError):
            valid_decision({"id": "a", "prediction": "down",
                            "probabilities": {"up": 0.7, "down": 0.3}})
        self.assertEqual(valid_decision({"id": "a", "prediction": "down",
                                         "probabilities": {"up": 0.5, "down": 0.5}})["target_weight"], 0)

    def test_prepare_and_evaluate_without_future_selection(self):
        start, end, days, fills = self.synthetic()
        # One future week cannot be scored, but its causal request must remain.
        broken = (start + timedelta(days=50)).strftime("%Y-%m-%d")
        del days[broken]
        with TemporaryDirectory() as directory, patch("benchmark.run.daily_warehouse") as warehouse:
            warehouse.return_value = (days, fills, {"complete_days": len(days)})
            base = Path(directory)
            args = Namespace(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
                             pairs="SOLUSDT", root=base, events=base / "events.jsonl",
                             settlements=base / "settlements.jsonl", coverage=base / "coverage.json")
            prepare(args)
            events, settlements = read_jsonl(args.events), read_jsonl(args.settlements)
            self.assertGreater(len(events), len(settlements))
            self.assertEqual(set(events[0]), {"id", "state"})
            self.assertTrue(events[0]["id"].startswith("e"))
            responses = base / "responses.jsonl"
            write_jsonl(responses, [{"id": row["id"], "prediction": "up"} for row in events])
            result = base / "summary.json"
            evaluate(Namespace(events=args.events, settlements=args.settlements,
                               models=Path(__file__).resolve().parents[1] / "models.json",
                               responses=[f"gliner25={responses}"], fee_bps=5.0,
                               slippage_bps=4.0, ledger=base / "ledger.jsonl", output=result))
            import json
            summary = json.loads(result.read_text())
            self.assertEqual(summary["status"], "running")
            self.assertTrue(summary["runs"])
            self.assertTrue(summary["baselines"])
            self.assertEqual(len(summary["models"]), 16)


if __name__ == "__main__":
    unittest.main()
