from eval.run_eval import grade

NO_INFO = "No relevant information found in historical proposals."

ANSWERABLE = {
    "answerable": True,
    "expected_sources": ["security.md"],
    "keywords": ["AES-256"],
}
UNANSWERABLE = {"answerable": False, "expected_sources": [], "keywords": []}


def test_correct_answer_passes():
    result = {"answer": "We use AES-256 at rest.", "sources": ["security.md"]}
    assert grade(ANSWERABLE, result) == (True, "correct")


def test_wrong_source_fails():
    result = {"answer": "We use AES-256.", "sources": ["other.md"]}
    assert grade(ANSWERABLE, result) == (False, "wrong or missing source")


def test_missing_keyword_fails():
    result = {"answer": "We encrypt data.", "sources": ["security.md"]}
    passed, reason = grade(ANSWERABLE, result)
    assert not passed and "AES-256" in reason


def test_wrongly_refusing_an_answerable_question_fails():
    result = {"answer": NO_INFO, "sources": []}
    assert grade(ANSWERABLE, result) == (False, "wrongly refused")


def test_correctly_refusing_passes():
    result = {"answer": NO_INFO, "sources": []}
    assert grade(UNANSWERABLE, result) == (True, "correctly refused")


def test_answering_an_unanswerable_question_fails():
    result = {"answer": "Revenue was $10M.", "sources": ["finance.md"]}
    assert grade(UNANSWERABLE, result) == (False, "should have refused")