# Gemeinsames Task-/State-Modell: Vorbereitung im Quality-Agenten

Das gemeinsame Pydantic-Modell steht in `src/models/tasks.py` und kann ohne Import von
Agentenimplementierungen verwendet werden:

```python
from src.models.tasks import EngineeringTask

task = EngineeringTask(
    task_id="WORK-ITEM-001",
    task_type="quality_review",
    description="Prüfe die geänderte API und ihre Regressionstests.",
    assigned_role="quality",
    input_files=["src/app/main.py"],
)
```

## Felder und Validierung

| Feld | Bedeutung |
|---|---|
| `task_id` | Gemeinsame Kennung für Code, Tests, Traces und Review |
| `task_type` | Technische Auftragsart |
| `description` | Beschreibung des Prüfauftrags |
| `assigned_role` | Empfängerbereich; beim Quality-Agenten `quality` |
| `input_files` | Zu prüfende Dateien; eigene leere Liste pro Task |
| `workflow_id` | Gemeinsame Ablaufkennung, automatisch erzeugt oder explizit übergeben |

Die Beschreibung bleibt im Task, State, Bericht und Trace erhalten. Der QA-Zusammenfassung
wird sie bewusst nicht als LLM-Prompt übergeben: angeforderte Arbeit ist kein Nachweis
ausgeführter Prüfungen. Die Zusammenfassung erhält die tatsächliche pytest-Ausgabe.

Leere Pflichtfelder, unbekannte Zusatzfelder und ungültige Workflow-IDs werden abgewiesen.
Eine Task-Nachricht darf keine menschliche Freigabe hinzufügen. Pfadberechtigungen prüfen
weiterhin die jeweiligen Tools. `assigned_role` ist ein technisches Nachrichtenfeld;
es ändert weder `organization/roles.yaml` noch menschliche Zuständigkeiten.

`QualityTask` erweitert `EngineeringTask` um `pytest_target` und `timeout_seconds` und
begrenzt die Auftragsart auf `quality_review`. Es liefert Vorgaben für den Quality-Bereich.
Das frühere Eingabefeld `artifacts` wird als Alias akzeptiert; Ausgaben verwenden `input_files`.
Auch die bisherigen QA-Aufrufe über `QATestRequest` funktionieren weiter.

## Tatsächliche Verwendung in deinem Agenten

`run_quality_agent` akzeptiert einen `EngineeringTask`, einen spezialisierten `QualityTask`
oder dessen Dictionary-Darstellung. Ein allgemeiner Task wird einmal am Eingang zum
QualityTask ergänzt und validiert. Danach läuft derselbe Task durch den Workflow:

1. Der QA-Prüfschritt erhält das vollständige typisierte Task-Objekt und führt pytest aus.
2. Der Security-Prüfschritt erhält dasselbe Objekt und das QA-Ergebnis aus dem State.
3. Das Human Gate übernimmt den Task mit beiden Ergebnissen in den Bericht.

`EngineeringState` definiert den gemeinsamen LangGraph-Kanal `task`. `QAState` und
`QualityState` erweitern diesen State um ihre Ergebnisfelder. Die Prüfschritte protokollieren
den normalisierten Task sowie dieselbe Task-/Workflow-ID. Die Objektidentität innerhalb
des Workflows und die JSON-Übergabe werden durch eigene Tests geprüft.

Dein **Quality-Agent bleibt ein Agent mit zwei Rollen/Prüfschritten**. Ein zweiter
eigenständiger Team-Agent wurde auf Wunsch noch nicht angebunden. Die Kursanforderung
„mindestens zwei Agenten verwenden das Modell tatsächlich“ ist daher durch diese lokale
Vorbereitung allein noch nicht vollständig nachgewiesen.

## Spätere Übergabe aus einem anderen Team-Agenten

Nach dessen tatsächlicher Implementierung kann er den oben erzeugten gemeinsamen Task
technisch weitergeben, beispielsweise innerhalb eines gemeinsamen LangGraph-Workflows:

```python
from src.agents.quality_agent import run_quality_agent

report = run_quality_agent(task)
```

Für explizite Quality-Optionen:

```python
from src.models.tasks import QualityTask

quality_task = QualityTask(
    **task.model_dump(),
    pytest_target="tests/test_quality_policy.py",
    timeout_seconds=60,
)
report = run_quality_agent(quality_task)
```

Alternativ ist `task.model_dump_json()` eine validierbare Nachrichtengrenze;
`EngineeringTask.model_validate_json(...)` liest sie wieder ein. Das ist eine vorbereitete
Schnittstelle und noch kein Nachweis eines zweiten Team-Agenten oder einer automatischen Queue.
Gemeinsame Erfolgs-/Fehlertraces aus dem späteren Team-Workflow müssen das tatsächliche
Zusammenspiel zeigen. Menschliche Freigaben bleiben separate Review-Artefakte.

## Ausführen und prüfen

Alle Befehle im Projektverzeichnis `C:\AgenticAi\agentic_ai_haw_2627`:

```powershell
# Nur das gemeinsame Modell und seine tatsächliche Verwendung testen (ohne Ollama)
.\.venv\Scripts\python.exe -m pytest tests/test_shared_task.py -v

# Vollständige Regression
.\.venv\Scripts\python.exe -m pytest -v

# Quality-Agent über das aktualisierte Task-Beispiel starten (mit Ollama)
.\.venv\Scripts\python.exe -m src.agents.quality_agent run --task-file docs/examples/quality-task.json --report logs/quality-report.json
```
