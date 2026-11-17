from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field
from app.questionnaire import QuestionnaireError, fill_questionnaire

from app.ingest import DOCS_DIR, SUPPORTED, add_file
from app.rag import answer_question



MAX_UPLOAD_MB = 10
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


app = FastAPI(
    title="Smart RFP Response Assistant",
    description="Answers RFP questions from past proposals, with source citations.",
    version="0.1.0",
)


# ---------- Request / response shapes ----------
class AskRequest(BaseModel):
    question: str = Field(
        ..., min_length=3, max_length=1000,
        examples=["What is your data encryption policy?"],
    )
    
class UploadResponse(BaseModel):
    filename: str
    chunks_added: int
    message: str


class Match(BaseModel):
    source: str
    distance: float


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    matches: list[Match]


# ---------- Endpoints ----------
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    try:
        return answer_question(req.question.strip())
    except Exception as e:
        # e.g. Bedrock is down or credentials expired
        raise HTTPException(status_code=502, detail=f"Answer generation failed: {e}")
    
@app.post("/upload", response_model=UploadResponse)
def upload(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name          # strip any folder paths, for safety
    if Path(filename).suffix.lower() not in SUPPORTED:
        raise HTTPException(400, f"Unsupported file type. Allowed: {', '.join(sorted(SUPPORTED))}")

    data = file.file.read()
    if not data:
        raise HTTPException(400, "The file is empty.")
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File too large. Max {MAX_UPLOAD_MB} MB.")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    dest = DOCS_DIR / filename
    dest.write_bytes(data)

    try:
        n = add_file(dest)
    except Exception as e:
        raise HTTPException(500, f"Could not process the file: {e}")

    if n == 0:
        dest.unlink()
        raise HTTPException(422, "No text could be extracted. Is it a scanned/image-only PDF?")

    return UploadResponse(
        filename=filename,
        chunks_added=n,
        message="Indexed. You can ask questions about it now.",
    )
    
@app.post("/fill")
def fill(file: UploadFile = File(...)):
    """Upload an Excel questionnaire, get it back with Answer / Source / Status filled in."""
    filename = Path(file.filename or "").name
    if Path(filename).suffix.lower() != ".xlsx":
        raise HTTPException(400, "Please upload an .xlsx Excel file.")

    data = file.file.read()
    if not data:
        raise HTTPException(400, "The file is empty.")
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File too large. Max {MAX_UPLOAD_MB} MB.")

    try:
        filled, summary = fill_questionnaire(data)
    except QuestionnaireError as e:
        raise HTTPException(422, str(e))

    out_name = f"{Path(filename).stem}_filled.xlsx"
    return Response(
        content=filled,
        media_type=XLSX_MIME,
        headers={
            "Content-Disposition": f'attachment; filename="{out_name}"',
            "X-Total": str(summary["total"]),
            "X-Answered": str(summary["answered"]),
            "X-Refused": str(summary["refused"]),
            "X-Errors": str(summary["errors"]),
        },
    )
