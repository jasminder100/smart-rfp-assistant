from io import BytesIO

import pytest
from openpyxl import Workbook, load_workbook

from app import questionnaire
from app.questionnaire import QuestionnaireError, fill_questionnaire

NO_INFO = "No relevant information found in historical proposals."


def make_xlsx(rows):
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    out = BytesIO()
    wb.save(out)
    return out.getvalue()


# A sheet shaped like the real sample: title rows, a gap, then the header
SAMPLE = [
    ["Vendor Questionnaire"],
    ["Please answer every question."],
    [],
    ["Section", "Question", "No."],
    ["Security", "Describe your encryption policy", 1],
    ["Company", "What was your revenue last year?", 2],
]


def read_back(data):
    ws = load_workbook(BytesIO(data)).worksheets[0]
    return [[c.value for c in row] for row in ws.iter_rows()]


def test_finds_header_below_title_rows_and_fills_columns(monkeypatch):
    def fake_answer(q):
        if "revenue" in q:
            return {"answer": NO_INFO, "sources": []}
        return {"answer": "AES-256 at rest.", "sources": ["security.md"]}

    monkeypatch.setattr(questionnaire, "answer_question", fake_answer)
    filled, summary = fill_questionnaire(make_xlsx(SAMPLE))

    assert summary == {"total": 2, "answered": 1, "refused": 1, "errors": 0}
    rows = read_back(filled)
    header = rows[3]
    assert header[-3:] == ["Answer", "Source", "Status"]
    assert rows[4][-3:] == ["AES-256 at rest.", "security.md", "Answered"]
    assert rows[5][-1] == "Refused"
    assert rows[5][-2] in (None, "")  # no source for a refusal


def test_one_failing_row_does_not_stop_the_run(monkeypatch):
    def flaky(q):
        if "revenue" in q:
            raise RuntimeError("boom")
        return {"answer": "ok", "sources": ["a.md"]}

    monkeypatch.setattr(questionnaire, "answer_question", flaky)
    _, summary = fill_questionnaire(make_xlsx(SAMPLE))
    assert summary == {"total": 2, "answered": 1, "refused": 0, "errors": 1}


def test_progress_callback_is_called_per_question(monkeypatch):
    monkeypatch.setattr(questionnaire, "answer_question", lambda q: {"answer": "ok", "sources": []})
    calls = []
    fill_questionnaire(make_xlsx(SAMPLE), on_progress=lambda done, total: calls.append((done, total)))
    assert calls == [(1, 2), (2, 2)]


def test_missing_question_column_is_rejected():
    with pytest.raises(QuestionnaireError):
        fill_questionnaire(make_xlsx([["Name", "Notes"], ["a", "b"]]))


def test_header_only_sheet_is_rejected():
    with pytest.raises(QuestionnaireError):
        fill_questionnaire(make_xlsx([["Section", "Question"]]))


def test_non_xlsx_bytes_are_rejected():
    with pytest.raises(QuestionnaireError):
        fill_questionnaire(b"this is not an excel file")


def test_too_many_questions_are_rejected(monkeypatch):
    monkeypatch.setattr(questionnaire, "MAX_QUESTIONS", 1)
    with pytest.raises(QuestionnaireError):
        fill_questionnaire(make_xlsx(SAMPLE))


def test_questionnaire_is_not_mistaken_for_a_question_header():
    assert questionnaire._is_question_header("question text")
    assert questionnaire._is_question_header("questions")
    assert not questionnaire._is_question_header("questionnaire")