# Agentic AI Software Company – Starter Repository

Starter repository for the HAW Hamburg elective project **Agentic AI / Human–Agent Software Company**.

The repository provides a deliberately small, common technical baseline so that teams can focus on engineering a mixed human–agent software company instead of spending the first sessions resolving incompatible frameworks.

## Course Documents / Kursunterlagen

- Project briefing: [English](task%20sheets/01_Project_Briefing_en.md) / [Deutsch](task%20sheets/01_Projektbriefing_de.md)
- Tasks for Sessions 1 and 2: [English](task%20sheets/Tasks_Session_1_and_2_en.md) / [Deutsch](task%20sheets/Aufgaben_Termin_1_und_2_de.md)
- Evaluation rubric: [English](task%20sheets/Evaluation_Rubric_Sessions_1_and_2_en.md) / [Deutsch](task%20sheets/03_Bewertungsraster_GitHub_Termin_1_und_2.md)
- **Session 3 / Termin 3 (26 October):** customer assignment [EN](task%20sheets/session-03/01_Customer_Assignment_en.md) / [DE](task%20sheets/session-03/01_Kundenauftrag_de.md); tasks [EN](task%20sheets/session-03/02_Tasks_Session_3_en.md) / [DE](task%20sheets/session-03/02_Aufgaben_Termin_3_de.md); rubric [EN](task%20sheets/session-03/03_Evaluation_Rubric_Session_3_en.md) / [DE](task%20sheets/session-03/03_Bewertungsraster_Termin_3_de.md)
- Session 3 technical notes / technische Hinweise: [bilingual](docs/SESSION_03_TECHNICAL_NOTES.md); [evidence templates / Evidenzvorlagen](docs/templates/session-03/)
- Session 2 guide and update instructions: [English](docs/SESSION_02_EN.md) / [Deutsch](docs/SESSION_02_DE.md)
- Setup instructions: [English](docs/SETUP_LOCAL_EN.md) / [Deutsch](docs/SETUP_LOCAL_DE.md)

The sessions run on Mondays from **10:00 to 15:00**. Assessment evaluates the team's changes to the starter, not the supplied examples and tests.

## What is fixed

- GitHub + GitHub Issues + GitHub Actions
- Python **3.12**
- LangChain + LangGraph
- FastAPI + Pydantic
- Docker + Docker Compose
- pytest
- PostgreSQL + pgvector
- LLM via either
  - local Ollama, or
  - an OpenAI-compatible HAW ICC endpoint
- structured local trace and cost data

Additional frameworks, databases, vector stores, workflow engines, or observability platforms require prior approval.

## Important: starter code does not count as team work

Code under `examples/` and tests under `tests/starter/` are reference implementations supplied with the course.
They exist to verify that the stack is wired correctly.

For project evaluation:

> **Do not count files under `examples/` or `tests/starter/` as evidence for an implemented company agent.**

Teams must implement their own agents under `src/agents/`.

Role staffing is also part of the project. During Session 1, teams distinguish `current_actor_type` from `target_actor_type`: a role can still be performed by a human while an agent implementation is planned. Session 1 requires one own operational LangGraph agent. By the end of Session 2, at least `12 - number of human team members` roles must be operationally supported by an agent or hybrid implementation. One agent implementation may support multiple roles only when role-specific behavior and outputs are technically distinguishable and traceable.

See [`docs/STARTER_BOUNDARY.md`](docs/STARTER_BOUNDARY.md).

---

## Repository structure

```text
.
├── .github/
│   ├── workflows/ci.yml
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── costs/
│   ├── cost-model.yaml
│   └── usage.csv
├── db/
│   └── init.sql
├── docs/
│   ├── architecture.md
│   ├── ICC_CONFIGURATION.md
│   ├── STARTER_BOUNDARY.md
│   ├── SETUP_LOCAL_DE.md
│   └── SETUP_LOCAL_EN.md
├── examples/
│   └── file_review_agent.py
├── organization/
│   ├── company.md
│   └── roles.yaml
├── src/
│   ├── agents/
│   ├── app/
│   ├── llm/
│   ├── observability/
│   └── rag/
├── task sheets/
│   ├── project briefings (German / English)
│   ├── assignments (German / English)
│   └── evaluation rubric (German)
├── tests/
│   └── starter/
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

# Quick start: local Python + Docker database + native Ollama

## 1. Prerequisites

- Git
- Python 3.12
- Docker Desktop / Docker Engine with Compose
- Ollama if you want to run the LLM locally

> **Docker must be running before you use `docker compose`.**  
> On macOS and Windows, start **Docker Desktop** first. On Linux, make sure the Docker Engine/daemon is running.
>
> Verify Docker before continuing:
>
> ```bash
> docker info
> ```
>
> If this command cannot connect to the Docker daemon, `docker compose up` will fail as well.

The recommended local setup is:

- run **Ollama natively on the host machine**, and
- use **Docker Compose for PostgreSQL/pgvector** and, if desired later, application services.

This is particularly useful on macOS, where native Ollama can use Apple Metal acceleration while Docker Desktop does not provide the same GPU access to Ollama containers.

## 2. Clone and configure

```bash
git clone <YOUR-REPOSITORY-URL>
cd <YOUR-REPOSITORY>
cp .env.example .env
```

## 3. Create a Python environment

macOS / Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Start PostgreSQL + pgvector

Make sure Docker is running first:

```bash
docker info
```

Then start the database:

```bash
docker compose up -d db
```

Check it:

```bash
docker compose ps
```

## 5. Check and start Ollama locally

The starter assumes a **recent Ollama version**. Before pulling the course model, check your installed version:

```bash
ollama --version
```

Then pull the example model used by `.env.example`:

```bash
ollama pull qwen3:4b
```

### If `ollama pull` fails with HTTP 412

A message such as:

```text
Error: pull model manifest: 412:
The model you are attempting to pull requires a newer version of Ollama.
```

means that the locally installed Ollama version is too old for the current model manifest. Update Ollama using the official installer for your operating system, restart Ollama, and verify the installed version again:

```bash
ollama --version
ollama pull qwen3:4b
```

Do not work around this error by changing the project dependencies or Docker configuration. It is an Ollama client/runtime version issue.

After the model has been downloaded successfully, verify that it can be started:

```bash
ollama run qwen3:4b
```

Exit the interactive model session with `Ctrl+D` or `/bye`.

Ollama usually starts its background service automatically when the desktop application is running. If no Ollama service is active, start it manually:

```bash
ollama serve
```

If Ollama is already running, `ollama serve` is unnecessary and may report that port `11434` is already in use.

## 6. Start FastAPI locally

For local Python execution, set the Ollama URL in `.env` to:

```text
LLM_BASE_URL=http://localhost:11434
EMBEDDING_BASE_URL=http://localhost:11434
```

Then:

```bash
python -m uvicorn src.app.main:app --reload
```

Open:

- API docs: `http://localhost:8000/docs`
- service health: `http://localhost:8000/health`
- database health: `http://localhost:8000/db/health`

## 7. Run the starter tests

Run the tests through the active Python interpreter:

```bash
python -m pytest
```

The repository contains a `pytest.ini` that adds the repository root to Python's import path. This allows the starter tests to import `src` and `examples` consistently. Using `python -m pytest` is recommended because it also ensures that pytest is executed from the same Python environment in which the project dependencies were installed.

## 8. Run the supplied LangGraph reference example

This verifies LangGraph + LangChain + LLM + local trace logging:

```bash
python -m examples.file_review_agent --input src/app/main.py
```

The example writes a separate trace to `logs/<run_id>.jsonl` using `TRACE_FILE=logs/RUN_ID.jsonl`. Existing `.env` files must be updated manually. See the Session 2 guide for evidence export and costs.

Remember: this supplied example does **not** count as a team agent.

---

# Quick start: application in Docker

Copy `.env.example` to `.env` and keep:

```text
LLM_BASE_URL=http://host.docker.internal:11434
EMBEDDING_BASE_URL=http://host.docker.internal:11434
```

Then:

```bash
docker compose up --build
```

Docker Compose maps `host.docker.internal` to the Docker host also on Linux through `host-gateway`.

---

# Switching to HAW ICC

If the provided ICC service exposes an OpenAI-compatible API, configure:

```text
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://<ICC-ENDPOINT>/v1
LLM_API_KEY=<TOKEN-IF-REQUIRED>
LLM_MODEL=<ICC-MODEL-NAME>
```

The agent code should not need to change. The same principle is used for embeddings.

The exact ICC URL, model name and authentication method must be supplied by the course before use.
See [`docs/ICC_CONFIGURATION.md`](docs/ICC_CONFIGURATION.md).

---

# LangSmith

LangSmith is **not required** by this repository and is not part of the assessment baseline.

If a team has permission to use it, LangChain/LangGraph tracing can be enabled through standard LangSmith environment variables. Local JSONL tracing remains mandatory for comparable project evidence.

Do not send customer data, secrets, or protected data to an external tracing service.

---

## Detailed Setup Instructions

Installing Python, Docker, and Ollama, as well as connection tests
and troubleshooting: [Lokales Setup](docs/SETUP_LOCAL_DE.md) / [Local setup](docs/SETUP_LOCAL_EN.md).

---

# First team tasks

The starter deliberately leaves these areas incomplete:

1. complete `organization/company.md`
2. assign all roles in `organization/roles.yaml`
3. adapt `docs/architecture.md` to the team's real architecture
4. use the common course rates in `costs/cost-model.yaml` and record actual usage
5. implement at least one **team-owned** agent under `src/agents/`
6. add meaningful tests outside `tests/starter/`
7. create GitHub Issues for the work
8. produce team-owned execution traces and cost evidence

---

## Team setup

- Operating system / environment: Windows PowerShell on Sebastian's local
  machine; project path `C:\AgenticAi\agentic_ai_haw_2627`.
- Python version: Python 3.12.0 in `.venv`.
- LLM access: local Ollama with model `qwen3:4b`.
- Database: Docker Compose service `db`, PostgreSQL 17.11 with pgvector 0.8.6,
  reachable on localhost port 5432.
- Setup deviations: `LLM_MAX_OUTPUT_TOKENS` is available through settings and
  defaults to 256 so local Ollama runs have a bounded output budget. The own QA
  agent also treats an LLM timeout as a structured `needs_review` result.
- Known limitations: local qwen3:4b on CPU is slow for QA summarization. The
  evidence includes one timeout escalation and later successful runs; the agent
  has a structured timeout path so this does not block human review.
- Starter tests: `python -m pytest` completed with 6 passed tests after adding
  the team-owned QA agent tests.
- Database check: `database: ok`, PostgreSQL 17.11, pgvector 0.8.6.
- Reference model availability: `ollama list` shows `qwen3:4b`.
- Team-owned agent evidence: `evidence/session-01/qa-test-agent-trace.jsonl`
  contains three `SESSION-01-QA` runs for `qa-test-agent`, including successful
  runs with token metadata where Ollama provided it.
- Usage / credits: `costs/usage.csv` records human time, one own agent run,
  local test verification, zero observed CI runs, and calculated course credits.
- GitHub issues: three Termin 1 issue drafts are documented in
  `docs/session-01-github-issues.md`; create them in GitHub if the CLI/API is
  not authenticated on the local machine.

# Compatibility policy

The core dependency versions are pinned in `requirements.txt` to create the same baseline for all teams.
Teams should not upgrade individual LangChain/LangGraph packages independently.

If a package change is necessary:

1. create an Issue,
2. explain why the baseline is insufficient,
3. document compatibility implications,
4. request approval before merging the change.


## Termin 2: Operations & Observability Agent (Mirko)

Team-eigener LangGraph-Agent `ops-agent` zur **read-only** Unterstützung der Rollen `devops_engineer` und `cost_observability_engineer`. Er führt Docker-/CI-Konfigurationschecks durch, wertet lokale Ausführungstraces und Credits auf Task-Ebene aus und erstellt JSON-Reports/JSONL-Traces mit explizitem Human-Review-Punkt. Deployment erfolgt **nicht** automatisch. Siehe [`docs/OPS_AGENT.md`](docs/OPS_AGENT.md) für Setup, Testaufruf, CLI und Grenzen. Ein echter Ollama-/ICC-Lauf muss für die Termin-2-Evidenz separat ausgeführt werden.


## Termin 6: Zweiter Kunde (`quotation-02` / HansePack) – Dieselbe Software Factory

In Termin 6 wurde die bestehende Software Factory über die Projektkonfiguration [`config/projects/quotation-02.yaml`](config/projects/quotation-02.yaml) (mit ausgelagertem Projekttemplate [`config/projects/templates/quotation_02_calculator.py.tpl`](config/projects/templates/quotation_02_calculator.py.tpl) und generischem Python-AST-Pre-Gate sowie Pre-QA-Short-Circuit in [`src/agents/customer_delivery_workflow.py`](src/agents/customer_delivery_workflow.py)) auf das zweite, separate Kundenprodukt **HansePack Handelsgesellschaft** (`../client-02-quotation`, GitHub: [`minhnyn/client-02-quotation`](https://github.com/minhnyn/client-02-quotation), GitHub Issue: [`client-02-quotation#1`](https://github.com/minhnyn/client-02-quotation/issues/1) / [`agentic_ai_haw_2627#4`](https://github.com/mfadhilahm/agentic_ai_haw_2627/issues/4)) geschaltet, ohne das erste Kundenprodukt **Nordwerk Industrie-Service** (`../client-01-website`, GitHub: [`mfadhilahm/client-01-website`](https://github.com/mfadhilahm/client-01-website)) zu verändern. Alle Nachweise, Run-Artefakte und Kosten sind in [`evidence/session-06.md`](evidence/session-06.md) verlinkt.

### 1. HansePack-Produkt unabhängig starten und testen (`../client-02-quotation`, `HP-AC01`–`HP-AC04`)

Das gelieferte HansePack-Produkt (`quotation/calculator.py` + `main.py`, Commit `724cfe72a1758e40346d77afd4b2cc4fbe7eb57d`) arbeitet deterministisch in Python (`Decimal` mit `ROUND_HALF_UP`, Ganzzahl-Cent) ohne Laufzeitabhängigkeit zur Factory oder einem LLM:

```powershell
cd ../client-02-quotation

# Q01: HP-BOX x 1 (Warenwert 250, Versand 1200, Gesamt 1450 Cent)
python main.py --sku HP-BOX --quantity 1

# Q03: HP-BOX x 50 (Listenbetrag 12500, 5% Rabatt 625, Warenwert 11875, Versand 1200, Gesamt 13075 Cent)
python main.py --sku HP-BOX --quantity 50

# E01: Menge 0 (verständlicher Validierungsfehler, Exit-Code 1, kein Angebot)
python main.py --sku HP-BOX --quantity 0

# Separater automatisierter Produkttest (gegen unveränderte Kundenfixtures in data/)
python -m pytest tests/test_quotation_s6.py -q
python -m unittest discover -s tests -p "test_*.py" -v
```

### 2. Factory-Tests inkl. deterministischer Projekttrennung & Pre-QA-Short-Circuit (`A1`, `A4`)

```powershell
# Standardlauf bzw. S3–S6 Factory- & Projekttrennungstests im Factory-Repository
python -m pytest tests/test_session_03_factory.py tests/test_session_04_factory.py tests/test_session_05_factory.py tests/test_session_06_factory.py -q
```

### 3. Gesicherter Nordwerk-Produktstand aus Termin 5 (`../client-01-website`, `84d5baf`, `B5`)

Das Altprodukt Nordwerk bleibt auf dem finalen Termin-5-Release-Stand **`84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f`** (`R-S5-FINAL` / `v1.0.0-s5-rc`, einschließlich deutscher Hauptseite `site/index.html` und englischer Einstiegsseite `site/en.html` sowie `docs/security-advisory-sr01.md`) völlig unverändert (`git status --porcelain` leer, `10/10` Tests bestanden) und separat ausführbar:

```powershell
cd ../client-01-website
python -m http.server 8080 --directory site
python -m unittest discover -s tests -p "test_*.py" -v
```
