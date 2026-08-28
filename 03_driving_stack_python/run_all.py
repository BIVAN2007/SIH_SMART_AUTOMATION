"""
run_all.py
Headless runner: executes all 5 scenarios and prints summary metrics.
This is your quick correctness check / CI smoke test, and also the basis
for the metrics table in your SIH technical report.

Usage:
    python run_all.py
    python run_all.py --scenario village_road --trials 3
"""
from __future__ import annotations
import argparse
import statistics as stats

from scenarios import ALL_SCENARIOS
from pipeline import DrivingPipeline

MAX_STEPS = 300  # 30s of sim time at dt=0.1


def run_one(scenario_name: str, seed: int) -> dict:
    pipe = DrivingPipeline(scenario_name, seed=seed)
    latencies = []
    telem = None
    for _ in range(MAX_STEPS):
        telem = pipe.step()
        if telem.replan_latency_ms > 0:
            latencies.append(telem.replan_latency_ms)
        if telem.done:
            break

    return {
        "scenario": scenario_name,
        "completed": telem.done and not telem.collision,
        "collision": telem.collision,
        "sim_time_s": telem.t,
        "min_clearance_m": telem.min_clearance_m,
        "mean_replan_latency_ms": round(stats.mean(latencies), 3) if latencies else 0,
        "p95_replan_latency_ms": round(sorted(latencies)[int(0.95 * len(latencies))], 3) if latencies else 0,
        "path_smoothness": telem.path_smoothness,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", choices=ALL_SCENARIOS, default=None)
    ap.add_argument("--trials", type=int, default=3)
    args = ap.parse_args()

    scenarios = [args.scenario] if args.scenario else ALL_SCENARIOS
    all_rows = []

    for name in scenarios:
        print(f"\n=== {name} ===")
        rows = [run_one(name, seed=100 * i + 7) for i in range(args.trials)]
        for r in rows:
            print(f"  trial: completed={r['completed']!s:5} collision={r['collision']!s:5} "
                  f"t={r['sim_time_s']:5.1f}s minClear={r['min_clearance_m']:5.2f}m "
                  f"meanLatency={r['mean_replan_latency_ms']:6.3f}ms "
                  f"p95Latency={r['p95_replan_latency_ms']:6.3f}ms "
                  f"smoothness={r['path_smoothness']:.3f}")
        all_rows.extend(rows)

        completion_rate = 100 * sum(r["completed"] for r in rows) / len(rows)
        collision_rate = 100 * sum(r["collision"] for r in rows) / len(rows)
        print(f"  -> completion={completion_rate:.0f}%  collision={collision_rate:.0f}%")

    print("\n=== Aggregate across all scenarios/trials ===")
    print(f"  Completion rate: {100 * sum(r['completed'] for r in all_rows) / len(all_rows):.1f}%")
    print(f"  Collision rate:  {100 * sum(r['collision'] for r in all_rows) / len(all_rows):.1f}%")
    print(f"  Mean replan latency: {stats.mean(r['mean_replan_latency_ms'] for r in all_rows):.3f} ms")


if __name__ == "__main__":
    main()
