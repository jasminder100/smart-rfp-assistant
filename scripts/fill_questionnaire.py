"""Fill an Excel RFP questionnaire using the existing RAG pipeline.

Usage (from the project root):
    python scripts/fill_questionnaire.py samples/sample_rfp_questionnaire.xlsx
    python scripts/fill_questionnaire.py in.xlsx -o out.xlsx --sheet "Questionnaire"
    python scripts/fill_questionnaire.py in.xlsx --no-check   # skip the answer-key grading

The original file is never modified. In the saved copy:
  * the "Answer" column is filled (it is created if the sheet has none)
  * "Source" and "Status" (Answered / Refused / Error) columns are added
  * if the workbook has a "Test key" sheet, the run is graded against it
"""
import argparse
import re
import sys
import time
from pathlib import Path

# Let this script import the `app` package when run from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font

from app.rag import answer_question

REFUSAL_PHRASE = "no relevant information found"
KEY_SHEET = "Test key"


def is_question_header(text: str) -> bool:
    """True for 'Question', 'Questions', 'Question text'... but not 'Questionnaire'."""
    return re.match(r"^questions?\b", text) is not None


def find_header(ws, max_scan: int = 15):
    """Find the header row: the first row that has a cell containing 'question'.

    Returns (header_row, {lowercase header text: column index}).
    """
    for r in range(1, min(ws.max_row, max_scan) + 1):
        headers = {
            str(c.value).strip().lower(): c.column
            for c in ws[r]
            if c.value is not None and str(c.value).strip()
        }
        if len(headers) >= 2 and any(is_question_header(h) for h in headers):
            return r, headers
    sys.exit("Could not find a header row containing a 'Question' column in the first "
             f"{max_scan} rows.")


def get_or_create_column(ws, header_row, headers, name, width):
    """Reuse a column with this header if it exists, otherwise add it at the end."""
    col = headers.get(name.lower())
    if col is None:
        col = max(headers.values()) + 1
        # make sure we don't land on a column that already holds anything in the header row
        while ws.cell(row=header_row, column=col).value is not None:
            col += 1
        headers[name.lower()] = col
    cell = ws.cell(row=header_row, column=col, value=name)
    cell.font = Font(bold=True)
    ws.column_dimensions[cell.column_letter].width = width
    return col


def load_key(wb):
    """Read the 'Test key' sheet -> {question number: expected text}."""
    if KEY_SHEET not in wb.sheetnames:
        return None
    ws = wb[KEY_SHEET]
    header_row, headers = find_header(ws)
    no_col = next((c for h, c in headers.items() if h.startswith("no")), 1)
    exp_col = next((c for h, c in headers.items() if "expected" in h), None)
    if exp_col is None:
        return None
    key = {}
    for r in range(header_row + 1, ws.max_row + 1):
        no, exp = ws.cell(row=r, column=no_col).value, ws.cell(row=r, column=exp_col).value
        if no is not None and exp:
            key[str(no).strip()] = str(exp).strip()
    return key


def grade(expected: str, status: str, sources: list) -> tuple:
    """Return (passed, note)."""
    if expected.upper().startswith("SHOULD REFUSE"):
        return status == "Refused", "expected refusal"
    wanted = [s.strip() for s in expected.split(";") if s.strip()]
    if status != "Answered":
        return False, f"expected answer from {', '.join(wanted)}"
    hit = [w for w in wanted if w in sources]
    return bool(hit), f"expected {', '.join(wanted)}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-fill an RFP questionnaire.")
    parser.add_argument("input", type=Path, help="Path to the .xlsx questionnaire")
    parser.add_argument("-o", "--output", type=Path, help="Where to save the filled file")
    parser.add_argument("--sheet", help="Sheet name (default: first sheet)")
    parser.add_argument("--no-check", action="store_true", help="Skip grading against the Test key sheet")
    args = parser.parse_args()

    if not args.input.exists():
        sys.exit(f"File not found: {args.input}")
    output = args.output or args.input.with_name(args.input.stem + "_filled.xlsx")

    wb = load_workbook(args.input)
    ws = wb[args.sheet] if args.sheet else wb.worksheets[0]

    header_row, headers = find_header(ws)
    q_col = next(c for h, c in headers.items() if is_question_header(h))
    no_col = next((c for h, c in headers.items() if h.startswith("no")), None)

    ans_col = get_or_create_column(ws, header_row, headers, "Answer", 70)
    src_col = get_or_create_column(ws, header_row, headers, "Source", 35)
    status_col = get_or_create_column(ws, header_row, headers, "Status", 12)

    rows = [r for r in range(header_row + 1, ws.max_row + 1) if ws.cell(row=r, column=q_col).value]
    key = None if args.no_check else load_key(wb)
    print(f"Header in row {header_row}; {len(rows)} questions in column {q_col}. Starting...\n")

    counts = {"Answered": 0, "Refused": 0, "Error": 0}
    graded = []  # (no, passed, note, question)
    start = time.time()

    for i, r in enumerate(rows, start=1):
        question = str(ws.cell(row=r, column=q_col).value).strip()
        no = str(ws.cell(row=r, column=no_col).value).strip() if no_col else str(i)
        try:
            result = answer_question(question)
            answer = result["answer"]
            sources = list(result.get("sources", []))
            status = "Refused" if REFUSAL_PHRASE in answer.lower() else "Answered"
        except Exception as e:  # one bad row must not kill the whole run
            answer, sources, status = f"ERROR: {e}", [], "Error"

        counts[status] += 1
        ws.cell(row=r, column=ans_col, value=answer)
        ws.cell(row=r, column=src_col, value=", ".join(sources))
        ws.cell(row=r, column=status_col, value=status)
        for col in (ans_col, src_col):
            ws.cell(row=r, column=col).alignment = Alignment(wrap_text=True, vertical="top")

        line = f"[{i}/{len(rows)}] {status:9} {question[:60]}"
        if key and no in key:
            passed, note = grade(key[no], status, sources)
            graded.append((no, passed, note, question))
            line += f"  -> {'PASS' if passed else 'FAIL'}"
        print(line)

    wb.save(output)
    print(f"\nDone in {time.time() - start:.0f}s. "
          f"Answered: {counts['Answered']}, Refused: {counts['Refused']}, Errors: {counts['Error']}")

    if graded:
        passed = sum(1 for g in graded if g[1])
        print(f"Graded against '{KEY_SHEET}': {passed}/{len(graded)} correct")
        for no, ok, note, q in graded:
            if not ok:
                print(f"  FAIL #{no}: {q[:60]}  ({note})")
    print(f"Saved to: {output}")


if __name__ == "__main__":
    main()