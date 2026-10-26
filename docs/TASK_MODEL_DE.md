# Gemeinsames Task-/State-Modell (`src/models/tasks.py` & `src/agents/task_models.py`)

Das gemeinsame Pydantic-Modell steht in `src/models/tasks.py` (erweitert in `src/agents/task_models.py`) und wird teamweit über Agentengrenzen hinweg eingesetzt:

```python
from src.models.tasks import EngineeringTask

task = EngineeringTask(
    task_id="DRYRUN-WORKITEMS-E2E",
    workflow_id="WF-WORKITEMS-E2E-001",
    task_type="quality_review",
    description="Prüfe die geänderte Work-Item-API und ihre PostgreSQL-Regressionstests.",
    assigned_role="quality",
    input_files=["src/app/main.py", "src/app/db.py"],
)
```

## Felder und Validierung

| Feld | Bedeutung |
|---|---|
| `task_id` | Gemeinsame Kennung für Code, Tests, Traces und Review |
| `task_type` | Technische Auftragsart |
| `description` | Beschreibung des Prüfauftrags |
| `assigned_role` | Empfängerbereich (`agent_engineer`, `integration_engineer`, `quality`, `devops_engineer`, `cost_observability_engineer`, etc.) |
| `input_files` | Zu prüfende Dateien; eigene leere Liste pro Task |
| `workflow_id` | Gemeinsame Ablaufkennung, automatisch erzeugt oder explizit übergeben |

Leere Pflichtfelder, unbekannte Zusatzfelder (`extra="forbid"`) und ungültige Workflow-IDs werden abgewiesen. Eine Task-Nachricht darf keine menschliche Freigabe hinzufügen.

Spezialisierte Erweiterungen desselben Modells:
- `QualityTask` (`src/models/tasks.py`): Erweitert `EngineeringTask` um `pytest_target` und `timeout_seconds`.
- `PlatformTask` & `HandoverPayload` (`src/agents/task_models.py`): Erweitert `EngineeringTask` für `platform-agent` und kapselt die typisierte Agent-to-Agent-Übergabe (`to_quality_task()`) an den `qa-test-agent` bzw. `quality_agent`.

## Tatsächliche teamweite Verwendung über mehrere Agenten

Das gemeinsame Task- und State-Modell (`EngineeringTask` / `EngineeringState`) ist in mehreren eigenständigen Team-Agenten aktiv angebunden und durch Tests (`tests/test_shared_task.py`, `tests/test_platform_agent.py`, `tests/test_ops_agent.py`) sowie echte Ausführungstraces (`evidence/session-02/`) nachgewiesen:

1. **`platform-agent` (`src/agents/platform_agent.py`):** Akzeptiert `EngineeringTask` / `PlatformTask`, führt die rollenspezifische AST-Inspektion (`agent_engineer` oder `integration_engineer`) aus und erzeugt ein `HandoverPayload`, das über `.to_quality_task()` mit identischer `task_id` und `workflow_id` direkt an `qa-test-agent` / `quality_agent` übergeben wird (`run_platform_to_qa_workflow`).
2. **`quality_agent` (`src/agents/quality_agent.py`, `qa_test_agent.py`, `security_agent.py`):** Akzeptiert `EngineeringTask` oder `QualityTask` und reicht dasselbe Task-Objekt im `EngineeringState` durch den QA-Prüfschritt (`pytest` + LLM) und den deterministischen Security-Prüfschritt (`inspect_python`) bis zum Human Gate.
3. **`ops-agent` (`src/agents/ops_agent.py`):** Nutzt `EngineeringTask` in `OpsRequest` sowohl für `devops_engineer` als auch für `cost_observability_engineer`.

## Ausführen und prüfen

```powershell
# Gemeinsames Modell und Agent-to-Agent-Übergabe testen
.\.venv\Scripts\python.exe -m pytest tests/test_shared_task.py tests/test_platform_agent.py -v

# Vollständige Regression inkl. PostgreSQL-Persistenztests
$env:STARTER_DATABASE_TEST = "1"
.\.venv\Scripts\python.exe -m pytest -v
```
