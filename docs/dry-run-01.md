# Dry Run 01 – Persistente Work-Item-Funktion & Agentic Workflow

## 1. Was wurde umgesetzt?
Im Rahmen des internen Dry Runs für Termin 2 wurde der FastAPI-Starter-Service um eine persistente **Work-Item-Verwaltung** mit PostgreSQL-Anbindung erweitert und über unseren mehrstufigen Agentic-Development-Workflow geprüft:

- **Datenbank-Schema & Persistenz (`db/init.sql`, `src/app/db.py`):**
  - Tabelle `work_items` (`id`, `title`, `description`, `status` [`open`/`done`], `assigned_role`, `created_at`, `completed_at`).
  - Persistenzfunktionen `init_work_items_schema()`, `create_work_item()`, `list_work_items()`, `complete_work_item()` und `delete_work_item()`.
- **FastAPI-Endpunkte (`src/app/main.py`):**
  - `POST /work-items` (Work Item anlegen)
  - `GET /work-items` (Work Items auflisten, optional gefiltert nach `status`)
  - `PATCH /work-items/{item_id}/complete` (Work Item als erledigt markieren)
  - `DELETE /work-items/{item_id}` (Work Item löschen)
- **Automatisierte Tests (`tests/test_work_items_api.py`, `tests/test_platform_agent.py`, `tests/test_quality_workflow.py`):**
  - End-to-End CRUD-Tests der Work-Item-API, Validierungstests sowie Agent-to-Agent-Handover-Tests.

**Nachweiskette (Traceability):**
`Task (DRYRUN-WORKITEMS-IE / SESSION-02-PLAT-AE)` $\rightarrow$ `platform-agent` (`agent_engineer` & `integration_engineer`) $\rightarrow$ `HandoverPayload` / `QualityTask` (`src/models/tasks.py`) $\rightarrow$ `qa-test-agent` & `security-agent` (`quality_agent.py`) $\rightarrow$ `Human Review Gate`.

---

## 2. Welche Menschen und Agenten waren beteiligt?

| Rolle | Accountable Human | Beteiligter Agent | Beitrag im Dry Run |
| :--- | :--- | :--- | :--- |
| **Agent Engineer** | Muhammad Masduki | `platform-agent` (`agent_engineer`) | AST-Inspektion der LangGraph-Workflows, State-Schemas und Tracing-Anbindung (`inspect_agent_architecture_tool`). |
| **Integration Engineer** | Saad Alaoui-Mdaghri | `platform-agent` (`integration_engineer`) | Prüfung der FastAPI-Endpunkte (`src/app/main.py`), Pydantic-Verträge und Erstellung des strukturierten `HandoverPayload` (`inspect_integration_contracts_tool`). |
| **Backend / Architect** | Mirko Löhden / Minh Phan | `dev_architect_agent` | Entwurf und Implementierung der Work-Item-Endpunkte und DB-Anbindung. |
| **QA & Security** | Felix Hauschild / Mirko Löhden | `qa-test-agent`, `security-agent` | Ausführung der `pytest`-Suite (`run_pytest_tool`), statische Sicherheitsprüfung (`inspect_python`) und Bündelung im `QualityReport`. |
| **DevOps & Cost** | Mirko Löhden / Minh Phan | `ops-agent` | Überwachung der CI-/Laufzeitkonfiguration und Kosten-/Trace-Auswertung. |

---

## 3. Wo musste ein Mensch korrigieren oder freigeben?
1. **Korrektur nach Branch-Merge (`src/llm/factory.py`):**
   Beim Zusammenführen der Team-Branches ging kurzzeitig das Keyword-Argument `json_mode: bool = False` in `get_chat_model()` verloren, wodurch ein Test in `tests/test_quality_workflow.py` fehlschlug. Menschlicher Eingriff stellte die Kompatibilität für beide Modi (`reasoning` und `json_mode`) wieder her.
2. **Lokale Infrastruktur-Eskalation (`escalate_to_human`):**
   Ein erster Lauf des `platform-agent` ohne gestarteten lokalen Ollama-Dienst wurde vom Agenten sauber als `needs_review` mit `human_gate_status: "escalate_to_human"` abgefangen (`run_id=3c0be835-a69d-4dba-8ea3-ce50573953bd`), bevor nach Verifikation des laufenden Ollama-Dienstes die regulären Läufe (`status: "passed"`) durchgeführt wurden.
3. **Verbindliches Human Approval Gate:**
   Sowohl `run_platform_to_qa_workflow` (`platform_agent.py`) als auch `run_quality_agent` (`quality_agent.py`) stoppen vor einer Freigabe bei `pending_approval` bzw. `awaiting_human_review`. Erst die explizite menschliche Entscheidung (`approved` durch Accountable Human) gibt das Artefakt frei.

---

## 4. Was kostete der Workflow?
Gemäß Kurs-Kostenmodell (`costs/cost-model.yaml` & `costs/usage.csv`, lokales Modell `qwen3:4b` über Ollama):

| Task-ID | Akteur / Rolle | Calls / Dauer | Tokens (In / Out) | Credits |
| :--- | :--- | :--- | :--- | ---: |
| `SESSION-02-PLAT-AE` | `platform-agent` (`agent_engineer`) | 1 Call / 20,26 s | 573 / 768 | **1,2448** |
| `DRYRUN-WORKITEMS-IE` | `platform-agent` (`integration_engineer`) | 1 Call / 20,43 s | 418 / 768 | **1,2434** |
| `SESSION-02-QUALITY` | `qa-test-agent` + `security-agent` | 1 LLM-Call + Tool-Run | siehe `evidence/session-02/` | **~1,2500** |
| `SESSION-02-PLATFORM` | Mensch (Implementierung & Review) | 1,5 Stunden | – | **150,0000** |

*Beobachtung:* Die reinen Agentenläufe kosten jeweils nur ca. **1,24 Credits** (~20 s Laufzeit dank deaktiviertem Thinking-Modus `reasoning=False` und `LLM_MAX_OUTPUT_TOKENS=768`), während die menschliche Entwicklungs- und Review-Zeit (100 Credits/h) den Großteil der Gesamtkosten ausmacht.

---

## 5. Welche konkrete Änderung würdet ihr beim nächsten Task ausprobieren?
**Hypothese für Termin 3 (Token- & Laufzeit-Optimierung bei `platform-agent`):**
In beiden erfolgreichen Läufen (`SESSION-02-PLAT-AE` und `DRYRUN-WORKITEMS-IE`) hat `qwen3:4b` das Ausgabelimit von `output_tokens = 768` vollständig ausgeschöpft, wodurch der JSON-Parser teilweise auf das strukturierte Tool-Fallback zurückgreifen musste.
- **Konkrete Maßnahme:** Wir aktivieren auch im `platform-agent` standardmäßig `get_chat_model(json_mode=True)` (wie bereits im `qa-test-agent` erprobt) und begrenzen das JSON-Antwortschema auf kurze Befunde (`max 300 Output-Tokens`).
- **Erwarteter Effekt:** Reduktion der LLM-Antwortzeit von ~20 s auf <8 s, 100 % valides JSON ohne Parser-Fallback und ~50 % weniger Output-Token-Kosten.
