# Quality-Agent: lokale Ausführungsevidenz, 19. Oktober 2026

## Aktueller Nachweis nach Ollama-Korrektur

Die Dateien `ollama-fix-report.json` und `ollama-fix-trace.jsonl` dokumentieren einen
erfolgreichen echten Modelllauf mit `qwen3:4b`: `summary_status=ok`,
`llm_response_received=true`, 180 Input- und 44 Output-Tokens. pytest bestand alle
21 Policytests; der begrenzte Security-Check war erfolgreich. Die menschliche Freigabe
steht weiterhin aus. Ollama meldete rund 10,03 Sekunden Gesamtzeit, davon rund
4,60 Sekunden Laden und 3,45 Sekunden Generierung; der QA-Schritt insgesamt dauerte 22,12 Sekunden.

Die LLM-Wartezeit ist jetzt unabhängig vom pytest-Zeitlimit (lokal 180 Sekunden).
Thinking ist über die API ausgeschaltet und QA fordert kurze JSON-Ausgabe an
(lokales Ausgabelimit: 384 Tokens). Der Quellhash dieses Laufs lautet
`39f15ef099e37b760df217e6e89dadb44aeff2c523642dd348a1d55f9372b282`.

`ollama-fix-pytest.xml` und `ollama-fix-pytest.txt` belegen den vollständigen anschließenden
Regressionstest: **59 passed, 1 skipped**, Laufzeit rund 11,88 Sekunden.
Neue Fälle prüfen die getrennten Zeitlimits, Thinking-/JSON-Konfiguration und die sichere
Weitergabe der Laufzeit-Metadaten. Der optionale Datenbanktest bleibt übersprungen.

Die nachfolgenden Abschnitte beschreiben die vorherigen Läufe vor dieser Korrektur.

Diese Nachweise betreffen ausschließlich QA/Security. Rollen- und Organisationsdateien
wurden nicht geändert. Es wurde keine tatsächliche menschliche Sicherheitsfreigabe erteilt.

## Abschließender Standard-Testlauf

```powershell
Set-Location 'C:\AgenticAi\agentic_ai_haw_2627'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=evidence/session-02/pytest.xml
```

- Ergebnis: **55 passed, 1 skipped**; 56 erfasste Fälle, keine Fehler oder Fehlschläge.
- `pytest.xml`: JUnit-Nachweis; `pytest.txt`: Textausgabe des abschließenden Laufs.
- Übersprungen: optionaler Starter-PostgreSQL-Test, da `STARTER_DATABASE_TEST` nicht gesetzt war.
  Docker Desktop war nicht erreichbar. Eine echte PostgreSQL-Persistenzprüfung wurde nicht durchgeführt.
- Modellantworten in Unit-/Regressionstests sind simuliert. Echte Unterprozessausführung wird
  unter anderem im bestehenden QA-Integrationstest und im neuen Timeouttest geprüft.
- Die temporären Review-Entscheidungen der Tests sind Testdaten, keine menschliche Freigabe.

## Abschließender echter Quality-Workflow

```powershell
.\.venv\Scripts\python.exe -m src.agents.quality_agent run --task-file docs/examples/quality-task.json --trace-file evidence/session-02/final-quality-trace.jsonl --report evidence/session-02/final-quality-report.json
```

- `final-quality-report.json`: strukturierter Abschlussbericht.
- `final-quality-trace.jsonl`: zwei Ausführungsrecords mit eigener Run-ID und gemeinsamer
  Task-/Workflow-ID; Security verweist auf den vorausgehenden QA-Run.
- pytest: **21 passed**, tatsächlicher Exit-Code 0.
- Security: ausgewählte Datei `src/app/main.py` geprüft, keine Befunde innerhalb des begrenzten Prüfumfangs.
- Tatsächlich konfigurierter Modellpfad: Ollama / `qwen3:4b`, kein FakeLLM.
- LLM-Zusammenfassung: **Zeitlimit erreicht**, `summary_status=unavailable`.
  Damit ist ein echter Aufrufversuch, aber keine erfolgreiche Modellantwort belegt.
  Es liegen dafür keine Tokenmetadaten vor; sie werden nicht als gemessene Null ausgegeben.
- Workflow endet mit `awaiting_human_review`, `human_decision=pending`.
  Der erfolgreiche technische Teststatus bleibt trotz LLM-Timeout erhalten.

HEAD während der Läufe: `be9fe194df18b7e3ddfb46bc67baab644f1eebe6`, Arbeitsbaum geändert.
Der HEAD-SHA allein ist daher kein Snapshot der Erweiterung. Python-Quellen und Tests des
abschließenden Laufs sind über `source_sha256` identifiziert:
`585fe7ee0fe9acaf3b63ece2bb1b0e29cc5a91ebf51988be947245a7e054b276`.
Die Änderungen sind nicht committet. Nach weiteren Codeänderungen oder einem Abgabe-Commit neu ausführen.

`quality-report.json` und `quality-trace.jsonl` sind ein früherer Zwischenlauf mit 30 Sekunden
LLM-Wartezeit und einem anderen Quellstand. Sie sind ebenfalls als Timeout dokumentiert und
werden nicht als Nachweis des abschließenden Quellstands behandelt.

## Grenzen und nächste Schritte

Kein GitHub-Actions-Lauf wurde ausgelöst oder bestätigt. Der CI-Workflow wurde um die
Speicherung von Testprotokollen ergänzt und lokal als YAML geparst. Ein tatsächlicher CI-Lauf
ist erst nach Push/PR nachweisbar. Kein vollständiger Secrets-/Historien-/Dependency-Scan,
kein Deployment und keine Work-Item-API-Persistenzprüfung. Der Security-Check ist heuristisch.

Bericht und Testausgabe durch Sebastian prüfen; erst danach eine explizite Entscheidung über
die Review-CLI festhalten. Anweisungen stehen in `docs/QUALITY_AGENT_DE.md`.
Menschliche Implementierungs-/Reviewzeit ist hier nicht geschätzt oder als echte Messung eingetragen.
