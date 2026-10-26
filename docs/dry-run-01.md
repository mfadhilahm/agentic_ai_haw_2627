# Dry Run 01 – Persistente Work-Item-Funktion, End-to-End-Workflow & Kostenanalyse

**Stand:** 26. Oktober 2026 (Aktualisiert nach Auswertung von Termin 2 zur Vorbereitung auf Termin 3).

---

## 1. Was wurde umgesetzt und mit echter PostgreSQL-Persistenz verifiziert?

Im Rahmen des Dry Runs wurde der FastAPI-Service um eine **persistente Work-Item-Verwaltung auf PostgreSQL** erweitert und über einen durchgängigen, mehrstufigen Agentic-Development-Workflow (`WF-WORKITEMS-E2E-001` / `DRYRUN-WORKITEMS-E2E`) geprüft:

- **Datenbank-Schema & PostgreSQL-Persistenz (`db/init.sql`, `src/app/db.py`):**
  - Tabelle `work_items` (`id`, `title`, `description`, `status` [`open`/`done`], `assigned_role`, `created_at`, `completed_at`).
  - Persistenzfunktionen `init_work_items_schema()`, `create_work_item()`, `list_work_items()`, `complete_work_item()` und `delete_work_item()`.
- **FastAPI-Endpunkte (`src/app/main.py`):**
  - `POST /work-items` (Work Item anlegen, `201 Created`)
  - `GET /work-items` (Work Items auflisten, optional gefiltert nach `status`)
  - `PATCH /work-items/{item_id}/complete` (Work Item als erledigt markieren)
  - `DELETE /work-items/{item_id}` (Work Item löschen, `204 No Content`)
- **Vollständiger Testnachweis mit laufender PostgreSQL-Datenbank (0 Skips):**
  - Mit laufendem Container `pgvector/pgvector:0.8.6-pg17-bookworm` und `STARTER_DATABASE_TEST=1` bestehen **alle 123 Tests ohne einen einzigen Skip** (**123 passed, 0 skipped** in [`evidence/session-02/pytest.txt`](../evidence/session-02/pytest.txt) und [`evidence/session-02/pytest.xml`](../evidence/session-02/pytest.xml)).
  - Der Persistenztest `tests/test_work_items_api.py::test_work_items_postgresql_persistence` führt echte HTTP-Requests (`POST`, `PATCH`, `DELETE`) gegen FastAPI aus und verifiziert über eine separate `psycopg.connect()`-Verbindung, dass die Datensätze tatsächlich in der PostgreSQL-Tabelle `work_items` committet wurden.

### Durchgängige Nachweiskette (End-to-End Workflow `WF-WORKITEMS-E2E-001`)
1. **Task & Spezifikation (`dev_architect_agent.py` mit `qwen3:4b`):**
   - `SESSION-02-ARCH-002` (`software_architect`, Minh) $\rightarrow$ Artefakt [`evidence/session-02/arch-work-items.md`](../evidence/session-02/arch-work-items.md)
   - `SESSION-02-DEV-002` (`backend_api_engineer`, Mirko) $\rightarrow$ Artefakt [`evidence/session-02/backend-work-items.md`](../evidence/session-02/backend-work-items.md)
   - Trace: [`evidence/session-02/dev-architect-agent-trace.jsonl`](../evidence/session-02/dev-architect-agent-trace.jsonl)
2. **Agent-to-Agent-Handover (`platform_agent.py` $\rightarrow$ `qa_test_agent.py`):**
   - `DRYRUN-WORKITEMS-E2E` (`workflow_id=WF-WORKITEMS-E2E-001`): `platform-agent` (`integration_engineer`) prüft per Python-AST die FastAPI-Endpunkte und Agenten-Signaturen, erstellt das typisierte `HandoverPayload` und übergibt es als `QualityTask` (`pytest_target="tests/test_work_items_api.py"`) an `qa-test-agent`.
   - `qa-test-agent` führt die PostgreSQL-Tests aus (`3 passed`) und fasst das Ergebnis über `qwen3:4b` zusammen.
   - Bericht: [`evidence/session-02/platform-qa-workflow-report.json`](../evidence/session-02/platform-qa-workflow-report.json) (endet zwingend bei `human_gate_status="pending_approval"` und `approved_by_human=null`).
   - **Separates menschliches Review:** [`evidence/session-02/platform-qa-workflow-report.review.json`](../evidence/session-02/platform-qa-workflow-report.review.json) (durch `saad` über `record_platform_human_review()` mit `report_sha256` protokolliert).
3. **Quality- & deterministischer Security-Workflow (`quality_agent.py`):**
   - Kombiniert `qa-test-agent` und den deterministischen Python-AST-Security-Checker `security-agent` (`inspect_python` auf `src/app/main.py`, `src/app/db.py`, `src/agents/platform_agent.py`).
   - Bericht: [`evidence/session-02/work-items-quality-report.json`](../evidence/session-02/work-items-quality-report.json) (`status="awaiting_human_review"`, `human_decision="pending"`).
   - Trace: [`evidence/session-02/work-items-quality-trace.jsonl`](../evidence/session-02/work-items-quality-trace.jsonl).
   - **Separates menschliches Review:** `evidence/session-02/work-items-quality-report.review-*.json` (durch `felix` über `quality_agent.record_human_review()`).
4. **Operations & Cost Observability (`ops_agent.py` mit `qwen3:4b`):**
   - `SESSION-02-OPS-DEVOPS` (`devops_engineer`, inkl. bestandenem `docker compose config --quiet`) und `SESSION-02-OPS-COST` (`cost_observability_engineer`, Kosten- und Trace-Prüfung für `DRYRUN-WORKITEMS-E2E`).
   - Trace: [`evidence/session-02/ops-agent-trace.jsonl`](../evidence/session-02/ops-agent-trace.jsonl), Berichte & separate Reviews (`mirko`) unter [`evidence/session-02/ops-reports/`](../evidence/session-02/ops-reports/).

---

## 2. Beteiligte Menschen, Agenten und Unterstützungsarten

| Rolle | Accountable Human | Technische Unterstützung | Art der Unterstützung & Nachweis |
| :--- | :--- | :--- | :--- |
| **Software Architect** | Minh Phan | `dev_architect_agent` (`sa-agent`) | **Hybrid (LLM-Agent, `qwen3:4b`):** Liest Repo-Kontext und erstellt Architekturentwürfe (`arch-work-items.md`). |
| **Backend / API Engineer** | Mirko Löhden | `dev_architect_agent` (`bae-agent`) | **Hybrid (LLM-Agent, `qwen3:4b`):** Prüft API-/DB-Code und dokumentiert Implementierungsverträge (`backend-work-items.md`). |
| **Data & RAG Engineer** | Yaw Poku | `data-agent` | **Hybrid (LLM-Agent, `qwen3:4b`):** Dokument-Ingestion, Markdown-Abschnitt-Chunking und strukturierte Zusammenfassung (`ca2b4646...jsonl`). |
| **Agent Engineer** | Muhammad Masduki | `platform-agent` (`agent_engineer`) | **Hybrid (AST-Tool + LLM `qwen3:4b`):** Prüft LangGraph-Aufbau, State-Schemas, Tracing und LLM-Factory-Nutzung (`inspect_agent_architecture_tool`). |
| **Integration Engineer** | Saad Alaoui-Mdaghri | `platform-agent` (`integration_engineer`) | **Hybrid (AST-Tool + LLM `qwen3:4b`):** Prüft FastAPI-Routen/Pydantic-Modelle und erzeugt `HandoverPayload` (`inspect_integration_contracts_tool`). |
| **QA & Test Engineer** | Felix Hauschild | `qa-test-agent` | **Hybrid (`pytest`-Subprocess + LLM `qwen3:4b`):** Führt echte Tests aus; technischer Exit-Code bestimmt unveränderbar den Status. |
| **AI Safety & Security Engineer** | Mirko Löhden | `security-agent` (`quality-security-checker`) | **Hybrid (Deterministischer Python-AST- & Policy-Checker ohne LLM):** Statische Codeanalyse (`inspect_python`) auf `eval`/`exec`, `shell=True`, literale Credentials, Pfadgrenzen und QA-Status-Integrität. |
| **DevOps Engineer** | Mirko Löhden | `ops-agent` (`devops`) | **Hybrid (Statisches Audit + `docker compose config --quiet` + LLM `qwen3:4b`):** Prüft Dockerfile, Compose-Healthchecks, CI-Pipeline und gepinnte Dependencies. |
| **Cost & Observability Engineer** | Mirko Löhden | `ops-agent` (`observability`) | **Hybrid (Deterministische Trace-/CSV-Aggregation + LLM `qwen3:4b`):** Berechnet Agenten-, Mensch- und CI-Credits inkl. Fehlversuchen und Review-Stunden. |

---

## 3. Wo musste ein Mensch korrigieren oder freigeben?

1. **Trennung von automatisiertem Lauf und menschlicher Freigabe im `platform-agent`:**
   - In der ersten Fassung von `run_platform_to_qa_workflow` waren `human_decision="approved"` und ein Reviewer-Name als Default-Parameter vorbelegt.
   - **Korrektur:** `run_platform_to_qa_workflow` besitzt keine Freigabe-Parameter mehr, sondern endet zwingend bei `human_gate_status="pending_approval"` (bzw. `"changes_requested"` / `"escalate_to_human"`) und `approved_by_human=None`. `PlatformAgentResult` erzwingt `human_approval_required: Literal[True] = True`, und `_parse_result()` überschreibt jeden LLM-Versuch einer Selbstfreigabe. Die menschliche Entscheidung wird ausschließlich nachträglich über `record_platform_human_review()` in eine separate `.review.json`-Datei mit `report_sha256` geschrieben und durch eigene Unit-Tests (`tests/test_platform_agent.py`) abgesichert.
2. **Korrektur der Multiline-AST-Erkennung im `platform-agent`:**
   - Ein erster E2E-Lauf (`run_id=cbfb8627...`) meldete `status="failed"` (`human_gate_status="changes_requested"`), weil `inspect_integration_contracts_tool` mehrzeilig formatierte `@app.post(\n "/work-items", ...)`-Dekoratoren zeilenweise abschnitt (`"@app.post("`) und `qwen3:4b` dies als Syntaxfehler interpretierte. Unser neues Review-Gate verhinderte daraufhin korrekt die Freigabe (`ValueError: Only workflows in 'pending_approval' state can be approved`).
   - **Korrektur:** Umstellung von `inspect_integration_contracts_tool` auf vollständige Python-AST-Auswertung (`ast.FunctionDef` / `ast.unparse`). Der darauffolgende Retry (`run_id=e4da7b40...`) lief sauber durch (`status="passed"`, `human_gate_status="pending_approval"`) und konnte nach menschlicher Prüfung freigegeben werden.
3. **Klärung und Korrektur des Modellpfads im `dev_architect_agent` (`gemini-3.5-flash-lite` $\rightarrow$ `qwen3:4b`):**
   - Am 19.10.2026 lief ein Teammitglied bei `dev_architect_agent` ohne deaktiviertes Thinking in das 60s-Timeout (`run_id=424c6466...`) und testete lokal über den `openai_compatible`-Pfad in `.env` ein externes Modell (`gemini-3.5-flash-lite`).
   - **Korrektur:** Umstellung in `dev_architect_agent.py` auf `get_chat_model(json_mode=True)` (setzt für Ollama automatisch `reasoning=False`) und erneute Ausführung beider Rollen (`SESSION-02-ARCH-002` und `SESSION-02-DEV-002`) mit dem lokalen Kurs-Standardmodell `qwen3:4b` über Ollama.

---

## 4. Vollständige Kostenübersicht (inkl. Fehlversuchen, Retries und menschlichem Review-/Korrekturaufwand)

Gemäß Kurs-Kostenmodell ([`costs/cost-model.yaml`](../costs/cost-model.yaml) und [`costs/usage.csv`](../costs/usage.csv)):

| Task-ID | Akteur / Rolle | Läufe (davon Fehlversuche / Retries) | Dauer gesamt | Credits |
| :--- | :--- | :--- | ---: | ---: |
| `SESSION-02-PLAT-AE` | `platform-agent` (`agent_engineer`) | 2 Runs (1 Fallback `needs_review` + 1 `passed`) | 31,22 s | **2,3544** |
| `SESSION-02-PLAT-IE` | `platform-agent` (`integration_engineer`) | 1 Run (1 Fallback vor Ollama-Start) | 10,84 s | **1,1084** |
| `DRYRUN-WORKITEMS-IE` | `platform-agent` (`integration_engineer`) | 3 Runs (1 Fallback + 2 `passed`) | 49,10 s | **3,5692** |
| `SESSION-02-QUALITY` | `qa-test-agent` + `security-agent` | 5 Workflows (2 LLM-Timeouts + 3 `passed` Retries) | 145,28 s | **6,5913** |
| `SESSION-02-ARCH-001` / `DEV-001` | `dev_architect_agent` (Historischer Testlauf + Timeout + Retry) | 3 Runs (inkl. 1 Timeout 60,21 s) | 71,71 s | **3,8766** |
| `data-summary-session02` | `data-agent` (`data_rag_engineer`) | 5 Runs (2 Timeouts + 1 Truncate + 2 `success`) | 547,33 s | **10,5341** |
| `SESSION-02-ARCH-002` / `DEV-002` | `dev_architect_agent` (`qwen3:4b` kursvorgabenkonform) | 3 Runs (1 `completed` Arch + 1 `needs_review` + 1 `completed` Dev) | 29,95 s | **3,4477** |
| `DRYRUN-WORKITEMS-E2E` | E2E (`platform-agent` + `qa-test-agent` + `security-agent`) | 5 Runs (1 abgelehnter `failed`-Run + 4 `passed`-Runs) | 54,65 s | **4,5991** |
| `SESSION-02-OPS-DEVOPS` / `COST` | `ops-agent` (`devops` + `observability` auf `qwen3:4b`) | 4 Runs (2 initiale `needs_review` + 2 `passed` Retries) | ~55,0 s | **~4,6500** |
| **Menschlicher Review- & Korrekturaufwand** | Team (`muhammad`, `saad`, `felix`, `mirko`, `yaw`) | Explizite Code-Korrekturen, Prompt-/AST-Fixes & Review-Freigaben | 5,75 h | **575,0000** |
| **CI-Läufe** | GitHub Actions | 3 CI-Verifikationsläufe | – | **3,0000** |

---

## 5. Erprobte Optimierung & Ausblick für Termin 3 (Kundenauftrag)

Die in Dry Run 01 formulierte Hypothese – Aktivierung von `get_chat_model(json_mode=True)` (`reasoning=False`) und kompakten JSON-Schemata in `platform-agent`, `dev_architect_agent` und `ops-agent` – wurde umgesetzt und gemessen:
- **Vorher:** `platform-agent` schöpfte 768 Output-Tokens voll aus (~20,4 s Laufzeit); `dev_architect_agent` lief ohne `reasoning=False` in das 60s-Timeout.
- **Nachher (verifiziert in `DRYRUN-WORKITEMS-E2E` und `SESSION-02-DEV-002`):** `platform-agent` benötigt nur noch **250 Output-Tokens in 13,08 s** (~36 % schneller, 67 % weniger Output-Tokens); `dev_architect_agent` antwortet mit `qwen3:4b` in **6,30 s** (159 Output-Tokens) mit 100 % validem JSON.
