from pathlib import Path

from eval.run_eval import run_eval

THRESHOLDS = [1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.0]
SWEEP_MD = Path("eval/sweep_results.md")

lines = [
    "# Threshold Sweep",
    "",
    "| MAX_DISTANCE | Total | Answered correctly | Refused correctly | Failed questions |",
    "|---|---|---|---|---|",
]

for t in THRESHOLDS:
    print(f"Running at MAX_DISTANCE={t} ...")
    rows = run_eval(max_distance=t, quiet=True, delay=2)

    n_ans = sum(r["answerable"] for r in rows)
    n_ref = len(rows) - n_ans
    answered = sum(r["passed"] for r in rows if r["answerable"])
    refused = sum(r["passed"] for r in rows if not r["answerable"])
    fails = ", ".join(f"#{r['id']}" for r in rows if not r["passed"]) or "-"

    lines.append(f"| {t} | {answered + refused}/{len(rows)} | {answered}/{n_ans} | "
                 f"{refused}/{n_ref} | {fails} |")

SWEEP_MD.write_text("\n".join(lines) + "\n")
print("\n" + "\n".join(lines))
print(f"\nSaved to {SWEEP_MD}")