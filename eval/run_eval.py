import argparse
import csv
import json
import time
from pathlib import Path

from app.rag import MAX_DISTANCE, NO_INFO, answer_question

QUESTIONS = Path("eval/questions.json")
RESULTS_CSV = Path("eval/results.csv")
RESULTS_MD = Path("eval/results.md")


def grade(item, result):
    refused = result["answer"] == NO_INFO
    if not item["answerable"]:
        return (True, "correctly refused") if refused else (False, "should have refused")
    if refused:
        return False, "wrongly refused"
    if not any(s in result["sources"] for s in item["expected_sources"]):
        return False, "wrong or missing source"
    missing = [k for k in item["keywords"] if k.lower() not in result["answer"].lower()]
    if missing:
        return False, f"missing facts: {', '.join(missing)}"
    return True, "correct"


def run_eval(max_distance=None, quiet=False, delay=0.0):
    items = json.loads(QUESTIONS.read_text())
    rows = []
    for item in items:
        result = answer_question(item["question"], max_distance=max_distance)
        passed, reason = grade(item, result)
        rows.append({
            "id": item["id"],
            "question": item["question"],
            "answerable": item["answerable"],
            "expected_sources": "; ".join(item["expected_sources"]) or "(none: should refuse)",
            "cited_sources": "; ".join(result["sources"]) or "-",
            "top_distance": result["matches"][0]["distance"] if result["matches"] else None,
            "passed": passed,
            "reason": reason,
            "answer": result["answer"],
        })
        if not quiet:
            print(f"{'PASS' if passed else 'FAIL'}  #{item['id']:>2}  {item['question']}  ({reason})")
        time.sleep(delay)
    return rows


def write_reports(rows, threshold):
    with RESULTS_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    score = sum(r["passed"] for r in rows)
    lines = [
        "# Evaluation Results",
        "",
        f"**Score: {score}/{len(rows)}** (MAX_DISTANCE = {threshold})",
        "",
        "| # | Question | Expected source | Cited source | Result | AI answer (short) |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        short = r["answer"].replace("\n", " ").replace("|", "/")[:180]
        result = ("✅ " if r["passed"] else "❌ ") + r["reason"]
        lines.append(f"| {r['id']} | {r['question']} | {r['expected_sources']} | "
                     f"{r['cited_sources']} | {result} | {short}... |")
    RESULTS_MD.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-distance", type=float, default=None)
    args = parser.parse_args()

    threshold = args.max_distance if args.max_distance is not None else MAX_DISTANCE
    rows = run_eval(max_distance=args.max_distance)
    write_reports(rows, threshold)

    score = sum(r["passed"] for r in rows)
    print(f"\nScore: {score}/{len(rows)} at MAX_DISTANCE={threshold}")
    print(f"Reports written to {RESULTS_MD} and {RESULTS_CSV}")