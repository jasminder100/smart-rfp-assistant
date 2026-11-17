# Smart RFP Response Assistant

A small RAG application that drafts answers to RFP questionnaires from a company's past proposals. You ask a question like "What is your data encryption policy?", and it answers from the documents it has been given, names the file each fact came from, and says so plainly when the documents don't contain the answer.

I built this as a proof of concept for an IT services company. The documents in `data/sample_docs/` are nine made-up proposal sections for a fictional company called NimbusEdge Technologies: a company profile, a security policy, a cloud migration methodology, a disaster recovery plan, a privacy and governance policy, an SLA, DevOps practices, a bank migration case study and a GenAI services page.

## What it does

The backend is a FastAPI service with three endpoints: `/health`, `/ask` and `/upload`. The UI is a Streamlit page that talks to it. Documents are split into chunks, embedded with an Amazon Bedrock embedding model, and stored in a local ChromaDB database. The answer itself comes from a Bedrock chat model, called through LangChain.

You can upload a new document from the UI and ask questions about it straight away, without restarting anything.

## How a question is answered

The pipeline has three stages, and most of the interesting work went into the first two.

First, the question is searched two ways at once. A vector search finds chunks that mean something similar to the question, and a BM25 keyword search finds chunks that share its words. The two rankings are merged with reciprocal rank fusion. On top of that, the three best vector hits and the two best keyword hits are always included, so a chunk that is excellent on one ranking can't be crowded out by chunks that are merely average on both. Up to six chunks go to the model.

Second, the model is not asked to simply write an answer. It has to return a small JSON object that names the subject of the question, quotes the sentences from the context that state a fact about exactly that subject, says whether the context really covers it, and only then gives the answer. The code checks that every quote appears word for word in the retrieved text. If the model says the context doesn't cover the subject, or its quotes can't be found, the system returns "No relevant information found in historical proposals." without looking at the draft answer.

Third, the answer is cited. Only files that are actually named in the answer are shown as sources, so an answer can't look sourced when it isn't.

 ## Filling a whole questionnaire (Excel)

Real RFPs usually arrive as a spreadsheet with dozens of questions. The **Fill a questionnaire** tab answers the whole sheet in one go.

![Fill a questionnaire tab](docs/fill-tab.png)

**How to use it**

1. Open the **Fill a questionnaire** tab.
2. Upload an `.xlsx` file with a `Question` column. The app finds the header row automatically and shows a preview with the number of questions found.
3. Click **Fill answers**. Each question is answered from the indexed proposals.
4. Click **Download filled questionnaire**.

The downloaded file gets three new columns next to each question:

| Column | Meaning |
|---|---|
| Answer | The drafted answer, or "No relevant information found in historical proposals." |
| Source | The document(s) the answer came from. Empty for refused questions. |
| Status | `Answered`, `Refused` or `Error` |

On the included sample sheet (`sample_rfp_questionnaire.xlsx`, 20 questions) the app answers 16 with the correct source and refuses the 4 that the proposals do not cover (revenue, Singapore, Pune, blockchain), matching the answer key.

**API:** the same feature is available at `POST /fill`. Upload the file as `file`. The filled workbook is returned, and the counts are in the `X-Total`, `X-Answered`, `X-Refused` and `X-Errors` response headers.

**Limits:** `.xlsx` only, at most 200 questions per sheet, and the upload size limit set by `MAX_UPLOAD_MB`. A row that fails is marked `Error` and does not stop the rest of the sheet.

**Tip:** if many rows come back as Refused, the answer is probably missing from the knowledge base. Add the relevant past proposal from the sidebar, then run the sheet again.

## Running it

You need Docker, and an AWS account with access to the Bedrock models you want to use. The project calls Bedrock for both embeddings and answer generation, so it costs a small amount of AWS credit per question and per ingested document.

Create a `.env` file in the project root with:

```
AWS_REGION=ap-south-1
LLM_MODEL_ID=apac.amazon.nova-lite-v1:0
EMBED_MODEL_ID=amazon.titan-embed-text-v2:0
MAX_DISTANCE=1.8
```

The code reads AWS credentials the usual way. With Docker, `docker-compose.override.yml` mounts your `~/.aws` folder into the API container read-only, which is fine for local development. If you sign in with SSO, run `aws sso login` first, because the tokens expire. On a server such as EC2, drop that mount and use an IAM role instead.

Then:

```bash
docker compose up --build
docker compose exec api python -m scripts.ingest
docker compose restart api
```

The API is on http://localhost:8000 and the UI on http://localhost:8501. The restart after ingesting matters: the API process caches its view of the vector store, so documents ingested from the command line only show up after a restart. Uploads through the UI don't have this problem.

The vector database and the documents folder are mounted as volumes, so everything survives `docker compose down`.

To run without Docker, create a virtual environment, install `requirements.txt`, and start the two processes yourself:

```bash
PYTHONPATH=. python scripts/ingest.py
uvicorn app.main:app --port 8000
API_URL=http://127.0.0.1:8000 streamlit run ui/app.py
```

## Evaluation

`eval/questions.json` holds 20 questions. Each has the source document it should be answered from, a few keywords that must appear in a correct answer, and a flag for whether the system should answer or refuse. Most test straightforward lookups across the nine documents, a couple need facts from more than one document, and several should be refused because the documents don't say.

Run it with:

```bash
PYTHONPATH=. python eval/run_eval.py
```

This writes `eval/results.md` and `eval/results.csv`, with the question, expected source, cited source and the model's answer side by side.

I added the retrieval and gating changes one at a time and ran the evaluation after each, so I could see what each one actually did. The two switches are environment variables, `USE_HYBRID` and `USE_GATE`, and the full result tables are saved as `eval/results_baseline.md`, `results_hybrid.md`, `results_gate.md` and `results_final.md`.

| Configuration | Score | Failures |
|---|---|---|
| Vector search only, no gate | 18/20 | #17, #20 |
| Hybrid search only | 19/20 | #14 |
| Gate only | 17/20 | #17, #18, #20 |
| Hybrid search and gate | 20/20 | none |

Two of the failures are about finding the right chunk. #17 asks "Do you work with open-source models?" and #20 asks which AI platforms and models the company works with. The answer sits in a single list-style sentence inside a short document, and with vector search alone that chunk ranked 43rd out of 47 for the first question, so the model never saw it. Keyword search ranks it first, because "open-source" appears in it word for word.

The other failures are about answering when the documents don't actually say. #18 asks how many engineers work in the Bengaluru delivery centre. The documents only give a company-wide headcount of about 1,850, and a prompt rule telling the model not to answer from related facts didn't stop it from returning that number. #14 asks for GenAI pricing, which isn't in any document. Hybrid search pulled in the GenAI chunks on keywords alone, and without the gate the model answered from them. So the two changes work as a pair: hybrid search finds more, and the gate makes sure the extra material doesn't turn into invented answers. The gate on its own wasn't enough either, since it still let #18 through in that run.

One regression is worth mentioning because it was my own doing. After the first version of hybrid search, #10 (experience migrating banks to the cloud) started failing. The case study chunk was the second-best vector match, but my keyword tokenizer didn't stem words, so "migrating" and "banks" never matched "migration" and "bank" in the text, and the fusion scores pushed the chunk out of the six sent to the model. The fix was to always include the top three vector hits and to add light stemming to the keyword search.

## Limitations

The 20/20 result needs a caveat. I looked at failures on this same set of questions and tuned the system until they passed, so the score shows that the fixes work on those cases, not that the system will do equally well on questions it hasn't seen. A fresh set of held-out questions is the obvious next step.

Short, keyword-style questions against list-style chunks are still the weak spot for the embedding model. The keyword search covers most of that gap, but it is a patch, and a reranker would be a more principled fix.

The gate fails closed. If the model returns JSON that can't be parsed, the system refuses instead of guessing, and prints a warning. That is the safer behaviour for an RFP tool, but it can occasionally refuse a question it could have answered.

Finally, the answer step is a single model call over at most six chunks. It hasn't been tested on large document collections, long documents with complex tables, or scanned PDFs.

## Project layout

```
app/          FastAPI service, ingestion, retrieval and answer logic
ui/           Streamlit interface
scripts/      Ingestion script and Bedrock connectivity checks
eval/         Evaluation questions, runner, threshold sweep and saved results
data/         Sample documents
Dockerfile, docker-compose.yml, docker-compose.override.yml
```
