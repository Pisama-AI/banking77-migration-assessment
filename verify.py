#!/usr/bin/env python3
"""Recompute the published comparison table from the per-case verdicts.

Reads data/verdicts.csv (one row per case per model) and checks every recomputed
metric against data/comparison.csv, the table published with the report.
Standard library only. Exit code 0 means every number matched.

    python verify.py
"""

import csv
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INCUMBENT = "incumbent-o4"


def load(name):
    with open(HERE / "data" / name, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def quantile(values, q):
    """Linear interpolation between closest ranks (numpy's default)."""
    v = sorted(values)
    pos = (len(v) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def mcnemar_exact(b, c):
    n, k = b + c, min(b, c)
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)


def recompute(rows, phase):
    by_arm = {}
    for r in rows:
        if r["phase"] == phase:
            by_arm.setdefault(r["arm_id"], {})[r["case_id"]] = r
    inc = by_arm[INCUMBENT]
    out = {}
    for arm, cases in by_arm.items():
        m = {}
        ok = {c: r["correct"] == "1" for c, r in cases.items()}
        inc_ok = {c: inc[c]["correct"] == "1" for c in cases}
        valid = {c: r["status"] == "valid" for c, r in cases.items()}
        m["correct"] = sum(ok.values())
        m["wrong_labels"] = sum(1 for c, r in cases.items() if valid[c] and not ok[c])
        m["invalid_outputs"] = sum(1 for r in cases.values() if r["status"] == "invalid")
        m["unresolved"] = sum(1 for r in cases.values() if r["status"] == "unresolved")
        m["both_correct"] = sum(1 for c in cases if ok[c] and inc_ok[c])
        m["corrections"] = sum(1 for c in cases if ok[c] and not inc_ok[c])
        both_valid = [c for c in cases if valid[c] and inc[c]["status"] == "valid"]
        # Published definition: a regression is a readable wrong label where the incumbent was
        # right. Unreadable replies are counted under invalid_outputs instead.
        m["regressions"] = sum(1 for c in both_valid if inc_ok[c] and not ok[c])
        # For the significance test every newly wrong case counts, readable or not.
        m["newly_wrong_any"] = sum(1 for c in cases if inc_ok[c] and not ok[c])
        m["both_valid_pairs"] = len(both_valid)
        m["agreement_count"] = sum(1 for c in both_valid if cases[c]["predicted_intent"] == inc[c]["predicted_intent"])
        m["same_wrong"] = sum(1 for c in both_valid if not ok[c] and not inc_ok[c]
                              and cases[c]["predicted_intent"] == inc[c]["predicted_intent"])
        m["different_wrong"] = sum(1 for c in both_valid if not ok[c] and not inc_ok[c]
                                   and cases[c]["predicted_intent"] != inc[c]["predicted_intent"])
        priced = [r for r in cases.values() if r["all_attempt_costs_known"] == "1" and r["cost_usd"]]
        m["fully_priced_cases"] = len(priced)
        m["known_charge_subtotal_usd"] = sum(float(r["cost_usd"]) for r in priced)
        if len(priced) == len(cases):
            m["cost_per_1000_cases_usd"] = m["known_charge_subtotal_usd"] / len(cases) * 1000
        times = [float(r["duration_seconds"]) for r in cases.values() if r["duration_seconds"]]
        m["p50_cumulative_http_seconds"] = quantile(times, 0.5)
        m["p95_cumulative_http_seconds"] = quantile(times, 0.95)
        m["mcnemar_p_vs_incumbent"] = mcnemar_exact(m["corrections"], m["newly_wrong_any"])
        out[arm] = m
    return out


def main():
    rows = load("verdicts.csv")
    published = load("comparison.csv")
    checked, failures = 0, []
    results = {}
    for phase in ("primary", "challenge"):
        results[phase] = recompute(rows, phase)
        for pub in (p for p in published if p["phase"] == phase):
            mine = results[phase][pub["arm_id"]]
            for key, value in mine.items():
                if key not in pub or pub[key] == "":
                    continue
                want = float(pub[key])
                tol = 1e-9 if key.endswith("_usd") else (1e-6 if "seconds" in key else 0)
                checked += 1
                if abs(value - want) > tol:
                    failures.append(f"{phase} {pub['arm_id']} {key}: recomputed {value}, published {want}")

    prim = results["primary"]
    print(f"{'model':<20}{'correct':>8}{'fixed':>7}{'broke':>7}{'unreadable':>11}{'p (McNemar)':>13}")
    for arm, m in sorted(prim.items(), key=lambda kv: -kv[1]["correct"]):
        print(f"{arm:<20}{m['correct']:>8}{m['corrections']:>7}{m['newly_wrong_any']:>7}{m['invalid_outputs']:>11}{m['mcnemar_p_vs_incumbent']:>13.3g}")
    print(f"\n{checked} published values checked, {len(failures)} mismatches")
    for f in failures:
        print("  MISMATCH", f)
    return 1 if failures or checked == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
