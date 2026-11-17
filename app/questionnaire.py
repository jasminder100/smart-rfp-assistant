"""Fill an Excel RFP questionnaire using the RAG pipeline.

Used by the /fill API endpoint. (scripts/fill_questionnaire.py has its own
copy of this logic for now; we can slim it down to call this module later.)
"""
import re
from io import BytesIO

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font

from app.rag import answer_question

REFUSAL_PHRASE = "no relevant information found"
MAX_QUESTIONS = 200  # protects your Bedrock bill from a huge upload


class QuestionnaireError(ValueError):
    """The uploaded workbook can't be processed (bad layout, too many rows...)."""


def _is_question_header(text: str) -> bool:
    """True for 'Question', 'Questions', 'Question text'... but not 'Questionnaire'."""
    return re.match(r"^questions?\b", text) is not None


def _find_header(ws, max_scan: int = 15):
    for r in range(1, min(ws.max_row, max_scan) + 1):
        headers = {
            str(c.value).strip().lower(): c.column
            for c in ws[r]
            if c.value is not None and str(c.value).strip()
        }
        if len(headers) >= 2 and any(_is_question_header(h) for h in headers):
            return r, headers
    raise QuestionnaireError(
        "Could not find a header row with a 'Question' column in the first 15 rows."
    )


def _get_or_create_column(ws, header_row, headers, name, width):
    col = headers.get(name.lower())
    if col is None:
        col = max(headers.values()) + 1
        while ws.cell(row=header_row, column=col).value is not None:
            col += 1
        headers[name.lower()] = col
    cell = ws.cell(row=header_row, column=col, value=name)
    cell.font = Font(bold=True)
    ws.column_dimensions[cell.column_letter].width = width
    return col


def fill_questionnaire(data: bytes, on_progress=None) -> tuple[bytes, dict]:
    """Take the bytes of an .xlsx file, return (filled .xlsx bytes, summary dict).

    on_progress(done, total) is called after each question, if given.
    """
    try:
        wb = load_workbook(BytesIO(data))
    except Exception:
        raise QuestionnaireError("That doesn't look like a valid .xlsx file.")

    ws = wb.worksheets[0]
    header_row, headers = _find_header(ws)
    q_col = next(c for h, c in headers.items() if _is_question_header(h))

    ans_col = _get_or_create_column(ws, header_row, headers, "Answer", 70)
    src_col = _get_or_create_column(ws, header_row, headers, "Source", 35)
    status_col = _get_or_create_column(ws, header_row, headers, "Status", 12)

    rows = [r for r in range(header_row + 1, ws.max_row + 1)
            if ws.cell(row=r, column=q_col).value]
    if not rows:
        raise QuestionnaireError("No questions found under the 'Question' header.")
    if len(rows) > MAX_QUESTIONS:
        raise QuestionnaireError(
            f"Too many questions ({len(rows)}). The limit is {MAX_QUESTIONS}."
        )

    counts = {"answered": 0, "refused": 0, "errors": 0}
    for i, r in enumerate(rows, start=1):
        question = str(ws.cell(row=r, column=q_col).value).strip()
        try:
            result = answer_question(question)
            answer = result["answer"]
            sources = list(result.get("sources", []))
            if REFUSAL_PHRASE in answer.lower():
                status, key = "Refused", "refused"
            else:
                status, key = "Answered", "answered"
        except Exception as e:  # one bad row must not kill the whole run
            answer, sources, status, key = f"ERROR: {e}", [], "Error", "errors"

        counts[key] += 1
        ws.cell(row=r, column=ans_col, value=answer)
        ws.cell(row=r, column=src_col, value=", ".join(sources))
        ws.cell(row=r, column=status_col, value=status)
        for col in (ans_col, src_col):
            ws.cell(row=r, column=col).alignment = Alignment(wrap_text=True, vertical="top")
        if on_progress:
            on_progress(i, len(rows))

    out = BytesIO()
    wb.save(out)
    return out.getvalue(), {"total": len(rows), **counts}