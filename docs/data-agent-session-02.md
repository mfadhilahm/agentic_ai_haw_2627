# Data-Agent – Beitrag zu Termin 2, Aufgabe 2

Verantwortlich: Saad. Branch: `feature/data-agent`.

Der Data-Agent ist eine eigene Fähigkeit: Er liest ausschließlich
`organization/company.md`, zerlegt den Text mit Quellenangabe und erstellt
über einen eigenen LangGraph eine deutsche Zusammenfassung. Der Ablauf hat
zwei Knoten, keine Schleife und höchstens einen Modellaufruf.

## Start unter Windows

```powershell
.\.venv\Scripts\python.exe -m src.agents.data_agent --task-id data-summary-session02 --timeout 300
.\.venv\Scripts\python.exe -m pytest -q
```

Lokale `.env`: `LLM_MODEL=qwen3:4b-instruct-2507-q4_K_M` (eindeutiger Instruct-Tag).
Standardzeitgrenze: 120 Sekunden; explizit änderbar bis 600 Sekunden.
`run_data_agent(DataTask(...))` ist eine asynchrone Python-Schnittstelle.
`DataTask` ist ein vorläufiger lokaler Adapter, kein abgestimmtes Teammodell.

## Verhalten und Grenzen

- Nur die fest erlaubte Firmenbeschreibung; keine frei wählbaren Dateipfade.
- Höchstens 12000 Zeichen Eingabe, Abschnitte höchstens 2000 Zeichen.
- Bestehende Überschriften bleiben beim ersten Teil eines Abschnitts erhalten.
- Ollama erhält `think=False` über die gemeinsame Factory; andere Nutzer der
  Factory behalten ihre bisherige Voreinstellung. ICC erhält diese Option nicht.
- Leere, nicht textuelle, abgeschnittene Antworten und enthaltene Think-Tags
  werden als Fehler gemeldet. Keine Verwendung interner Reasoning-Metadaten.
- Async-Zeitgrenze beendet das Warten auf das LLM, auch bei Streaming.
  Sie ist keine harte Betriebssystem-Prozessgrenze und garantiert nicht,
  dass Ollama serverseitige Berechnung sofort einstellt. Dateilesen und
  Trace-Schreiben sind lokale synchrone Operationen.
- Traces enthalten IDs, Rolle, Tools, Modell, Status, Laufzeit, Calls,
  verfügbare Tokens, Credits sowie Commit, Dirty-Status und Code-Hash.
  Dokumentinhalt, Provider-Fehlertexte und Zugangsdaten werden nicht geloggt.
- Kosten ohne Tokenzahlen sind unvollständige Schätzungen. Menschliche
  Implementierungs- und Reviewzeiten sind noch offen und werden nicht erfunden.
- Keine Datenbankablage oder Retrieval-Funktion in diesem Arbeitsschritt.
- Keine Agent-to-Agent-Integration und kein gemeinsames Human Gate:
  Schnittstelle und Issue sind laut Saad noch nicht abgestimmt.
  Die Ausgabe ist ein Artefakt zur menschlichen Prüfung, keine Freigabe.

## Verifikation

Die eigenen FakeLLM-Tests prüfen Erfolg, Lesefehler, Eingabelimit, leere und
ungültige Antwort, Modellfehler, Abschneiden, Reasoning-Ablehnung, Zeitgrenze,
Vertragsvalidierung und Provider-Weitergabe. Diese Tests sind kein echter
Modellnachweis.

Zwei echte Ollama-Läufe erreichten das 120-Sekunden-Zeitlimit und wurden als
Fehler protokolliert. Das bestätigt die Abbruchbehandlung, aber für diese beiden Läufe keine
erfolgreiche Zusammenfassung. Erfolgreiche Folgeläufe stehen unten.

PostgreSQL wurde als healthy beobachtet. `nomic-embed-text` wurde heruntergeladen;
Embeddings und DB-Persistenz des Data-Agenten wurden noch nicht ausgeführt.

Die gemeinsame Termin-2-Abgabe (drei Fähigkeiten, sechs operative Rollen,
Work-Item-API und Workflow) ist dadurch nicht als vollständig nachgewiesen.

### Diagnose des Modellfehlers

`ollama show qwen3:4b` meldet lokal Modell-ID `359d7dd4bcda`,
Thinking-Level ausschließlich `true`. Das Template hängt unabhängig vom
Thinking-Schalter `<think>` an den Assistant-Anfang. Die offizielle
[Tag-Liste](https://ollama.com/library/qwen3/tags) führt dieselbe ID für
`qwen3:4b`, `qwen3:4b-thinking` und `qwen3:4b-thinking-2507-q4_K_M`.
Der Adapter übersetzt `reasoning=False` korrekt in `think=False`; das behebt
jedoch nicht die Wahl eines ausschließlich denkenden Modells.

Der dritte echte Lauf endete nach 199,829 Sekunden mit `done_reason=length`:
382 Input- und 768 Output-Tokens, 3,0367 Kurscredits. Die Antwort wurde als
Fehler verworfen. Nachweis: `evidence/session-02/13dba66d-323c-4541-8c14-39beb9d6da3d.jsonl`.
Die beiden früheren Abbrüche kosten zusammen geschätzt 4,4134 Credits;
deren Tokenverbrauch ist unbekannt. Das sind zusätzliche Läufe, keine
Summenzeile zur erneuten Abrechnung.

Abschließender Standard-Testlauf: **33 passed, 1 skipped**. Der übersprungene
Test ist der opt-in Starter-Datenbanktest, kein eigener Data-Agent-Test.


### Erfolgreicher Abschluss mit Instruct-Modell

Die lokale `.env` wurde ausschließlich im Feld `LLM_MODEL` auf den oben
angegebenen Instruct-Tag umgestellt und bleibt von Git ignoriert. Keine
Frameworks, Bibliotheksversionen oder Zugangsdaten wurden verändert.

Der erste Instruct-Lauf (`6d82cfcb-503e-40fd-b0cd-22ff54e6e71a`) war technisch
erfolgreich (58,593 s, 380/82 Tokens, 1,5968 Credits). Die anschließende
agentische Inhaltsprüfung fand jedoch eine unbelegte Vermischung der Regeln
zu Kosten und Zustimmung. Das ist keine menschliche Freigabe. Der Prompt
wurde entsprechend präzisiert.

Der finale echte Lauf ist erfolgreich:

- Run: `ca2b4646-28e0-4880-884a-d2835afb3366`
- Modell: `qwen3:4b-instruct-2507-q4_K_M`
- Dauer: 47.563 Sekunden
- Calls: 1
- Input-/Output-Tokens: 412/84
- Kurscredits: 1.4872
- Ergebnis: `evidence/session-02/ca2b4646-28e0-4880-884a-d2835afb3366-result.json`
- Trace: `evidence/session-02/ca2b4646-28e0-4880-884a-d2835afb3366.jsonl`

Die fünf finalen Aussagen wurden durch den Entwicklungsagenten mit
`organization/company.md` verglichen und sind dort ausdrücklich enthalten.
Eine menschliche Prüfung durch Saad bleibt offen; es wurde keine menschliche
Freigabe behauptet. Auch zukünftige Modellantworten benötigen Inhaltsprüfung.

Der finale Standard-Testlauf: **33 passed, 1 skipped**. `git diff --check`
meldet keine Formatfehler. Kein Commit, Push oder Merge wurde ausgeführt.
Saads zuvor uncommitteter LangGraph-/Zusammenfassungsansatz wurde weitergeführt;
eine Sicherung des Eingangstands liegt lokal unter
`%TEMP%/data_agent_before_codex_20261019.py`.
