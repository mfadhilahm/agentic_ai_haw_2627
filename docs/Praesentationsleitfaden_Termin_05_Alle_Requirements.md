# Komplett-Erklärung & Präsentationsleitfaden für Termin 5 (Alle Requirements & Ergebnisse)

- **Projekt:** `website-01` – **Nordwerk Industrie-Service**
- **Software Factory Repository:** `agentic_ai_haw_2627` (`https://github.com/mfadhilahm/agentic_ai_haw_2627`)
  - Baseline-Commit (`F-BASE`, Termin 4): `54a626b18e0ce4a58142468a820e4626bd536de0`
  - Verbesserter Factory-Commit (`F-NEW`, Termin 5): `5f3b49e215f1b9e60c487c7015d26e7c68372107` (Tag: `F-NEW`)
  - Finaler Evidence-Commit (Termin 5): `d16a14e31b2b69765b5b7824dbc16b36a9a56f60`
- **Kundenprodukt Repository:** `client-01-website` (`https://github.com/mfadhilahm/client-01-website`)
  - Baseline-Commit (`R-BASE`, Termin 4): `ecb598140d0b2d0778d891f9bc1acc8c36295a93` (Tag: `R-BASE`)
  - Input-Commit vor dem `CR-01`-Lauf (Termin 5): `c3866e164d89a19bc83557058318319765b339b3`
  - Finaler Release-Commit (Termin 5): `84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f` (Tags: `R-S5-FINAL`, `v1.0.0-s5-rc`)
- **Lokales Sprachmodell (LLM):** Ollama `qwen3:4b@359d7dd4bcda` (`temperature = 0.0`, `json_mode = True`)

---

## 1. Was wurde aus dem Feedback zu Termin 4 korrigiert? (`Feedback_Session_04_Team_1-1.md`)

| Feedback-Punkt aus Termin 4 | Was war das Problem? | Was ist genau passiert / wie wurde es gelöst? | Nachweis-Datei |
|---|---|---|---|
| **1. `costs/usage.csv` unquoted commas & fehlende CI-Runs vom `2026-11-02`** | In `costs/usage.csv` enthielten `notes`-Felder Kommas ohne Anführungszeichen (`"`), wodurch Standard-CSV-Parser mehr als 8 Spalten lasen. Zudem waren am `2026-11-02` nur `2` statt aller `4` GitHub-Actions-Läufe verbucht. | Alle `notes`-Felder in `costs/usage.csv` sind jetzt strikt nach **RFC-4180 in doppelte Anführungszeichen (`"..."`)** eingeschlossen. Die CI-Zeile vom `2026-11-02` wurde auf **`4` Runs (`4.0` Credits)** (`46ed1f9`, `6393ebf`, `54a626b`, `a03d3be`) korrigiert. Ein neuer Unit-Test (`test_session_04_feedback_usage_csv_and_worktree_commit_distinction`) prüft bei jedem Testlauf, dass jede CSV-Zeile exakt 8 Spalten hat. | [`costs/usage.csv`](../costs/usage.csv), [`costs/cost-model.yaml`](../costs/cost-model.yaml), [`tests/test_session_04_factory.py`](../tests/test_session_04_factory.py) |
| **2. `product_output_commit` vs. `uncommitted_worktree` & lokale `C:\`-Pfade** | Während eines Laufs schreibt der Agent in `site/`, macht aber keinen `git commit`. Dadurch war `product_output_commit` identisch mit `product_input_commit`, während in `review.json` der spätere Commit (`ecb5981`) stand. Außerdem standen lokale Windows-Pfade (`C:\Hochschule\...`, `C:\Users\...`) in den JSON-Artefakten. | `run_customer_delivery_workflow` setzt nach dem Lauf explizit **`product_worktree_state: "uncommitted_worktree"`** und **`product_output_commit: "uncommitted_worktree"`**. Erst wenn nach dem menschlichen Review im Produkt-Repo committet und `record_customer_human_review(..., tested_source_commit="<sha>")` aufgerufen wird, werden **`product_worktree_state: "committed_after_review"`** und **`subsequent_product_commit: "<sha>"`** gesetzt. Alle lokalen `C:\`-Pfade wurden durch portable relative POSIX-Pfade ersetzt. | [`src/agents/customer_delivery_workflow.py`](../src/agents/customer_delivery_workflow.py), `runs/website-01/*/{manifest,workflow-report,review}.json` |
| **3. Direkte GitHub-Links für Produkt-Commits** | In `evidence/session-04.md` waren Produkt-Commits teilweise nur auf `../client-01-website` verlinkt. | Alle Commit- und Datei-Referenzen in `evidence/session-03.md`, `evidence/session-04.md`, `evidence/session-05.md` und den Run-Manifesten verlinken direkt auf `https://github.com/mfadhilahm/client-01-website/commit/<sha>` bzw. `blob/<sha>/...`. | [`evidence/session-04.md`](../evidence/session-04.md), [`evidence/session-05.md`](../evidence/session-05.md) |

---

## 2. Alle Kunden-Requirements (`AC-01` bis `AC-10`) – Was war gefordert und was ist passiert?

### `AC-01` – Unternehmensidentität & Kernaussage (`N-01`, `N-02`)
- **Anforderung:** Die Website muss den Namen `Nordwerk Industrie-Service` (`N-01`) und das Leistungsversprechen `Praktische Unterstützung für Ihren technischen Betrieb.` (`N-02`) klar sichtbar auf der Startseite zeigen.
- **Was ist passiert:** Im Header (`.brand-name`) und im `<section class="hero" id="start">` von `site/index.html` werden `N-01` als `<h1>` und `N-02` als `.lead`-Absatz ausgegeben. In Termin 5 wurde durch die Regressionstests (`test_website_s3.py`, `test_website_s4.py`, `test_website_s5.py`) verifiziert, dass diese Inhalte nach der `CR-01`-Änderung unverändert vorhanden sind.

### `AC-02` – Drei Kernleistungen im exakten Wortlaut (`N-03`, `N-04`, `N-05`)
- **Anforderung:** Alle drei Leistungen müssen mit Titel und Beschreibung wortwörtlich dargestellt werden:
  1. `Wartungsplanung` – `Wir strukturieren Wartungsaufgaben und dokumentieren Zuständigkeiten für kleine technische Betriebe.` (`N-03`)
  2. `Ersatzteilkoordination` – `Wir unterstützen bei der Abstimmung von Ersatzteilbedarfen und Lieferterminen.` (`N-04`)
  3. `Betriebsdokumentation` – `Wir bringen technische Unterlagen in eine nachvollziehbare und nutzbare Struktur.` (`N-05`)
- **Was ist passiert:** Unter `<section class="services" id="leistungen">` werden alle drei Leistungen als semantische `<article class="service-card">`-Karten gerendert. In Termin 5 wurden diese Texte über das **Delta-Key-Merging (`F-NEW`)** aus dem verifizierten `R-BASE`-Stand übernommen, sodass das LLM sie nicht erneut fehleranfällig abtippen musste.

### `AC-03` – Zielgruppen (`N-06`), Arbeitsweise (`N-07`) & Verbot unbelegter Aussagen
- **Anforderung:** Nennung der Zielgruppen `Kleine Produktionsbetriebe` und `Technische Serviceunternehmen` (`N-06`), des Arbeitsweise-Satzes `Ein fester Ansprechpartner, ein gemeinsam vereinbarter Leistungsumfang und nachvollziehbare Ergebnisse.` (`N-07`) sowie Verbot erfundener Zertifikate/Versprechen (`ISO 9001`, `TÜV`, `24/7`).
- **Was ist passiert:** `#zielgruppen` und `#arbeitsweise` sind eigene Sektionen in `site/index.html`. Zusätzlich prüft seit Termin 5 der deterministische **Pre-Gate-Validator (`validate_rendered_html_pre_gate`)** bereits im Speicher des Implementierungs-Agenten, dass keines der verbotenen Wörter (`ISO 9001`, `TÜV`, `24/7`, `TODO_FACTORY_GENERATION`) im HTML vorkommt.

### `AC-04` – Kontaktmöglichkeit (`N-08`), kein `<form>` & fiktiver Kurshinweis (`N-09`)
- **Anforderung:** Kontaktaufnahme ausschließlich über `mailto:kontakt@nordwerk.example` mit dem Text `Anfrage stellen` (`N-08`), **kein** HTML-Formular (`<form>`) und sichtbarer Hinweis `Fiktives Unternehmen – Lehrprojekt der HAW Hamburg. Keine realen Angebote oder Kontaktaufnahme.` (`N-09`).
- **Was ist passiert:** Sowohl im Hero-Bereich als auch unter `#kontakt` befindet sich der `<a class="cta-link" href="mailto:kontakt@nordwerk.example">Anfrage stellen</a>`-Link; ganz oben auf der Seite steht das gelbe Hinweisbanner (`.course-notice`, `role="note"`). Sowohl der Pre-Gate-Validator als auch `test_website_s5.py` prüfen auf Abwesenheit von `<form`.

### `AC-05` – Semantische Struktur, funktionierende `#`-Ankernavigation & lokale Assets
- **Anforderung:** Sinnvolle HTML5-Struktur (`header`, `nav`, `main`, `section`, `footer`), funktionierende interne Sprungmarken (`href="#..."` muss auf existierende `id="..."` zeigen) und ausschließlich lokale Dateien (keine externen CDNs, Webfonts oder Tracker).
- **Was ist passiert:** Alle Navigationslinks (`#leistungen`, `#zielgruppen`, `#arbeitsweise`, `#kontakt`, `#en` auf `index.html` sowie `#services`, `#target-groups`, `#approach`, `#contact` auf `en.html`) wurden durch den neuen Pre-Gate-Anker-Check (`validate_rendered_html_pre_gate`) und `test_website_s5.py` mittels Regex-Abgleich aller `href="#..."`- und `id="..."`-Attribute verifiziert. Es wird ausschließlich die lokale `styles.css` geladen (`0` externe Requests).

### `AC-06` – Responsives Layout bei `375 px` (Mobile) und `1280 px` (Desktop)
- **Anforderung:** Saubere Darstellung auf Mobilgeräten (`375 px`) und Desktop (`1280 px`) ohne horizontales Scrollen.
- **Was ist passiert:** `site/styles.css` nutzt `box-sizing: border-box`, `overflow-x: hidden`, ein responsives CSS-Grid (`repeat(auto-fit, minmax(16rem, 1fr))`) und eine `@media (max-width: 480px)`-Regel, die bei `375 px` auf 1 Spalte (`grid-template-columns: 1fr`) und volle Button-Breite umschaltet – sowohl für `site/index.html` als auch für `site/en.html`.

### `AC-07` – Tastaturbedienbarkeit & Barrierearmut
- **Anforderung:** Vollständige Bedienbarkeit per Tastatur (`Tab`, `Shift+Tab`, `Enter`), sichtbarer Fokus-Indikator (`:focus-visible`), `<html lang="...">`, `<title>` und korrekte Überschriftenhierarchie (`h1` $\rightarrow$ `h2` $\rightarrow$ `h3`).
- **Was ist passiert:** Beide Seiten (`index.html` mit `lang="de"` und `en.html` mit `lang="en"`) besitzen einen `.skip-link` (`Zum Hauptinhalt springen` / `Skip to main content`) und einen `3px solid #005fcc` Fokus-Rahmen (`a:focus-visible`) auf allen Links und Sprachumschaltern.

### `AC-08` – Reproduzierbarer Start, README & automatisierte Produkttests
- **Anforderung:** Klare Start- und Testanleitung im Produkt-Repository sowie automatisierte Produkttests.
- **Was ist passiert:** `client-01-website/README.md` und `docs/release-s5-handover.md` dokumentieren den Startbefehl (`python -m http.server 8080 --directory site`) und den Testbefehl (`python -m unittest discover -s tests -p "test_*.py" -v`), der alle 10 Produkttests aus Termin 3, 4 und 5 in `0,003 s` ausführt.

---

### `AC-09` (**NEU in Termin 5**) – Kundenänderung `CR-01` (`NW-S5-CR01`): 3. Zielgruppe & Englische Einstiegsseite
- **Anforderung laut Aufgabenblatt Termin 5:**
  1. Auf der deutschen Seite (`site/index.html`) unter Zielgruppen zusätzlich **`Technische Einkaufsabteilungen`** ergänzen; alle bisherigen deutschen Inhalte erhalten.
  2. Eine klar gekennzeichnete englische Einstiegsseite (`site/en.html` mit `<html lang="en">` und `<title>`) sowie einen erreichbaren Sprachwechsel Deutsch $\leftrightarrow$ Englisch bereitstellen, inklusive aller 9 englischen Pflichttexte im Wortlaut:
     - Titel: `Nordwerk Industrie-Service`
     - Kernaussage: `Practical support for your technical operations.`
     - Leistungen: `Maintenance planning`, `Spare parts coordination`, `Operational documentation`
     - Zusätzliche Zielgruppe: `Technical purchasing departments`
     - Kontakt: `Request information` (`mailto:kontakt@nordwerk.example`)
     - Hinweis: `Fictional company – HAW Hamburg course project. No real offers or contact.`
- **Was ist genau passiert:**
  1. **Anforderungs- & Impact-Analyse erstellt:** In `client-01-website/docs/issue-03-session-05-cr01.md` wurden alle 10 Delta-Keys (`N-06_group_3` + 9 `EN_*`-Keys), betroffene Dateien und Regressionsrisiken dokumentiert.
  2. **Factory-Konfiguration & Renderer erweitert:** `config/projects/website-01.yaml` wurde um `cr01_change_task` ergänzt; `src/agents/customer_delivery_workflow.py` rendert bei vorhandenen `EN_*`-Feldern sowohl die erweiterte `site/index.html` (mit 3. Zielgruppe `Technische Einkaufsabteilungen`, Sprachumschalter `href="en.html"` und `<section id="en" lang="en">`) als auch die eigenständige englische Seite `site/en.html` (`<html lang="en">`, `<title>Nordwerk Industrie-Service – Practical support for your technical operations.</title>`, Rücklink `href="index.html"`).
  3. **Realer Multi-Agenten-Lauf `WF-WEBSITE01-S5-CR01` ausgeführt:**
     - **Schritt 1 (Architect `minh`, Run `6fa3d659`):** Las `docs/issue-03-session-05-cr01.md` und `site/index.html`, erkannte den verifizierten 14-Key-`R-BASE`-Stand und übergab die 10 `CR-01`-`delta_keys` an den Implementierungs-Agenten.
     - **Schritt 2 (Implementation Iter 1 `mirko`, Run `670390c0`):** `qwen3:4b` gab beim ersten Versuch nur 4 der 10 Delta-Keys zurück. Unser strikter `F-NEW`-Validator warf sofort einen `ValueError` mit den 6 fehlenden Keys (`EN_service_2, EN_service_3, EN_target_group, EN_contact_label, EN_contact_href, EN_notice`), ohne die bestehende `site/index.html` zu überschreiben.
     - **Schritt 3 (QA Iter 1 `felix`, Run `390e1270`):** Führte `tests/test_website_s5.py` aus (`exit_code=1`) und reichte die exakte Fehlermeldung in die begrenzte Korrekturschleife (`route_after_qa -> implementation`) weiter.
     - **Schritt 4 (Implementation Iter 2 `mirko`, Run `cbcfecf4`):** Anhand des Feedbacks lieferte `qwen3:4b` in `6,75 s` alle 10 Delta-Keys vollständig aus, führte sie mit `R-BASE` zusammen, bestand `validate_rendered_html_pre_gate` und schrieb `site/index.html` (`6ebd91ed...`) sowie `site/en.html` (`8b43eaa3...`).
     - **Schritt 5 (QA Iter 2 `felix`, Run `ec9d30b1`):** `tests/test_website_s5.py` lief mit `exit_code=0` durch (`status: "passed"`), woraufhin das Human Gate auf `pending_approval` ging und nach Prüfung durch `saad` als Commit `84d5baf` (`R-S5-FINAL`) freigegeben wurde.

---

### `AC-10` (**NEU in Termin 5**) – Sicherheitsanfrage `SR-01` & Komponenteninventar
- **Anforderung laut Aufgabenblatt Termin 5:**
  - Der Kunde fragt nach der ENISA-Warnung vom `21.10.2026` zu `CVE-2026-109618` und `CVE-2026-109619` in PHP, weil im Hosting-Panel `"PHP 8.2"` steht und dort noch ein älteres CMS mit Kontaktformular liegt.
  - Gefordert sind ein separates **Komponenteninventar (`B4`)** und eine **ca. 1-seitige Kundenantwort (`B5`)** mit Quellenangabe + Abrufdatum, Trennung Bekanntes vs. Ungeklärtes, Hoster-Fragen, Empfehlung + Optionenvergleich, Erklärung warum `"statisch != automatisch sicher"` gilt, wegfallenden Altfunktionen, Pflegezuständigkeit und menschlichem Faktencheck (`D1`).
- **Was ist genau passiert:**
  - Erstellt in `client-01-website/docs/security-advisory-sr01.md`:
    1. **Teil A – Komponenteninventar (`B4`):** Trennt tabellarisch zwischen:
       - *Gelieferten Produkt-Laufzeitkomponenten:* `site/index.html` (HTML5), `site/en.html` (HTML5), `site/styles.css` (CSS3), optional `python -m http.server` nur für lokale Vorschau. Explizit als **`not used` (nicht verwendet)** ausgewiesen: PHP, CMS, Datenbank, serverseitiges Kontaktformular.
       - *Ungeklärtem Altsystem des Kunden:* Hosting-Eintrag `"PHP 8.2"`, altes CMS, altes Kontaktformular.
       - *Build-/Test-/Factory-Komponenten (nicht im Kunden-Hosting):* Python `3.12.10`, `pytest 9.1.1`, `langgraph`, `qwen3:4b@359d7dd4bcda`.
    2. **Teil B – Kundenantwort `SR-01` (`B5`):**
       - **Quellen:** ENISA Joint Statement vom `21.10.2026` (`https://www.enisa.europa.eu/news/joint-statement-on-critical-php-vulnerabilities`, Abrufdatum `2026-11-09`, mit Hinweis auf die Lehrprojekt-CVEs `CVE-2026-109618` & `CVE-2026-109619`) und PHP 8.2 ChangeLog (`https://www.php.net/ChangeLog-8.php#PHP_8_2`, Abrufdatum `2026-11-09`).
       - **Warum `"PHP 8.2"` allein nichts beweist:** Es fehlt der exakte Patchstand (`8.2.x` bzw. Distributions-Backports des Hosters) sowie die Information, ob der PHP-Interpreter für die Domain aktiv ist und ob alte `.php`-Dateien im öffentlichen `DocumentRoot` verbleiben.
       - **4 Hoster-Rückfragen:** (1) Exakte `php -v`-Version & Patchstatus für `CVE-2026-109618`/`109619`, (2) komplette Abschaltung von PHP für die Domain, (3) vollständige Entfernung alter `.php`-CMS-/Formulardateien aus dem Webroot, (4) Prüfung der Access-Logs auf Zugriffe seit Oktober 2026.
       - **Optionenvergleich & Empfehlung:** Vergleich von *Option 1 (In-Place-Update PHP/CMS)*, *Option 2 (Temporäre Isolierung/Sperrung)* und *Option 3 (Statische Ablösung + PHP-Deaktivierung + Löschen alter `.php`-Dateien – Empfohlen)*.
       - **Warum `"statisch != automatisch sicher"` gilt:** Selbst wenn `index.html` statisch ist, bleibt der Server verwundbar, falls alte `.php`-Dateien des CMS im selben Verzeichnis liegen bleiben und PHP aktiv ist! Außerdem bleiben TLS/HTTPS, Webserver-Updates, Security-Header und sichere SFTP-/Hosting-Zugänge Pflicht.
       - **Wegfallende Funktionen & Zuständigkeit:** Kein Web-CMS-Login (Änderungen erfolgen versioniert über Git + Tests) und kein serverseitiges Kontaktformular (ersetzt durch `mailto:kontakt@nordwerk.example`). Hosting/TLS/PHP-Abschaltung liegt beim Hoster; HTML/CSS-Pflege und Tests beim Technik-/Factory-Team (`mirko`, `felix`).
    3. **Teil C – Menschlicher Faktencheck (`D1`):** Dokumentierter Prüfvermerk durch `muhammad`, `mirko` und `saad` am `2026-11-09`.

---

## 3. Bewertungsraster Termin 5 (`A1`–`D2`) – Punkt-für-Punkt-Zuordnung für die Vorführung

### Kategorie A: Factory-Betrieb, Änderungsfähigkeit und gezielte Verbesserung (25 Punkte)

| Kriterium | Punkte | Was ist genau passiert & wo liegt der Beweis? |
|---|---:|---|
| **`A1` Trennung und Wiederverwendung der Factory** | 5 | `agentic_ai_haw_2627` enthält keinerlei Nordwerk-HTML im Python-Code, sondern steuert `../client-01-website` über `config/projects/website-01.yaml` und die Sandbox-Tools (`validate_product_workspace_path`, erlaubt Schreibzugriffe nur in `site/`). |
| **`A2` Kundenänderung `CR-01` über den Workflow** | 7 | `CR-01` wurde als Issue `#3` (`docs/issue-03-session-05-cr01.md`) erfasst, über `cr01_change_task` in `website-01.yaml` konfiguriert und im realen Multi-Agenten-Lauf `WF-WEBSITE01-S5-CR01` (`Architect -> Implementation -> Product QA -> Human Gate`) mit `qwen3:4b@359d7dd4bcda` ausgeführt. |
| **`A3` Regression und Änderungsabsicherung** | 6 | `client-01-website/tests/test_website_s5.py` prüft sowohl die neuen `CR-01`-Anforderungen (`test_01`, `test_02`) als auch die vollständige Regression `AC-01`–`AC-08` (`test_03`). Alle 10 Tests in `test_website_s3.py`, `test_website_s4.py` und `test_website_s5.py` laufen in `0,003 s` auf `OK`. |
| **`A4` Gezielte Factory-Verbesserung & Fehlerbehandlung (`F-NEW`)** | 7 | `F-NEW` (`5f3b49e`) implementiert **(1) Delta-Key-Merging** (`extract_verified_baseline_from_product_html`) und **(2) deterministische Pre-Gate-Validierung** (`validate_rendered_html_pre_gate`), ist durch `tests/test_session_05_factory.py` getestet und wurde sowohl auf `R-01` (`R-01-FNEW-001`, `R-01-FNEW-002`) als auch auf `CR-01` (`WF-WEBSITE01-S5-CR01`) real ausgeführt. |

### Kategorie B: Kundenprodukt Release, `CR-01` und `SR-01` (35 Punkte)

| Kriterium | Punkte | Was ist genau passiert & wo liegt der Beweis? |
|---|---:|---|
| **`B1` Englische Einstiegsansicht (`CR-01`)** | 7 | `site/en.html` (`<html lang="en">`, `<title>`) + `#en`-Sektion auf `site/index.html` enthalten alle 9 englischen Pflichtstrings wortgetreu. |
| **`B2` Zielgruppenerweiterung und Konsistenz** | 5 | `Technische Einkaufsabteilungen` ist unter `#zielgruppen` auf `site/index.html` ergänzt; alle bisherigen Inhalte (`N-01`–`N-09`) sind vollständig erhalten. |
| **`B3` Sprachwechsel, Navigation und Kontakt** | 5 | Direkter Sprachwechsel `index.html` $\leftrightarrow$ `en.html` im Header, Hero und Footer; `Request information` verweist auf `mailto:kontakt@nordwerk.example`; alle `#`-Anker lösen auf; kein `<form>`. |
| **`B4` Komponenteninventar** | 6 | Teil A in `client-01-website/docs/security-advisory-sr01.md` trennt Produkt-Laufzeit (HTML5/CSS3, PHP/CMS/DB/Formular = `not used`), ungeklärtes Altsystem (`"PHP 8.2"`) und Build-/Test-/Factory-Komponenten. |
| **`B5` Sicherheitsanfrage `SR-01`** | 8 | Teil B in `client-01-website/docs/security-advisory-sr01.md` (~1 Seite) mit ENISA (`21.10.2026`, `CVE-2026-109618`/`109619`) & PHP 8.2 Quellen (Abruf `2026-11-09`), 4 Hoster-Fragen, Optionenvergleich, `"statisch != automatisch sicher"`, wegfallenden Funktionen und Pflegezuständigkeit. |
| **`B6` Übergabefähigkeit und Wartungshinweis** | 4 | `client-01-website/README.md` und `docs/release-s5-handover.md` enthalten Start-/Testbefehle, das Browser-/Tastatur-Prüfprotokoll (`375 px` & `1280 px`) und den Wartungshinweis. |

### Kategorie C: Experiment, Messung und Kosten (25 Punkte)

| Kriterium | Punkte | Was ist genau passiert & wo liegt der Beweis? |
|---|---:|---|
| **`C1` Hypothese und Bezug zu Termin 4** | 5 | Direkt aus dem Termin-4-Engpass abgeleitet (`implementation_node` benötigte in `R-01-BASELINE-001` `137,14 s` und `595` Output-Tokens für 16 JSON-Keys). |
| **`C2` Kontrollierter Vorher-/Nachher-Vergleich auf `R-01`** | 10 | Gleiche Aufgabe `R-01`, gleicher Produktstart `R-BASE` (`ecb5981`), gleiches Modell `qwen3:4b@359d7dd4bcda`, $n=2$ Läufe (`R-01-FNEW-001`, `R-01-FNEW-002`): Implementierungszeit sank von **`137,14 s` auf `3,76 s` / `3,86 s` (`-97,2 %`)**, Output-Tokens von **`595` auf `105` / `104` (`-82,4 %`)**, Credits von **`5,4166` auf `3,6962` / `3,1678` (`-36,6 %`)** bei identischem Output-SHA-256 (`0b05ef0b...`). |
| **`C3` Evidenzbasierte Entscheidung** | 5 | `F-NEW` wird dauerhaft übernommen; Grenzen ehrlich benannt (greift nur bei verifiziertem Baseline-HTML; bei großen Deltas wie 10 Keys in `CR-01` fängt der strikte Delta-Check + Retry fehlende Keys in wenigen Sekunden ab). |
| **`C4` Kosten- und Gesamtabrechnung (Termin 3–5)** | 5 | Vollständig in `costs/usage.csv` und `costs/cost-model.yaml`: Kundenprojekt S3–S5 gesamt **`718,3586` Credits** gegenüber `946,0` Budget (**`24,1 %` unter Budget**); Factory-Entwicklung S3–S5 gesamt **`400,0` Credits** (exakt im Budget). |

### Kategorie D: Governance, Nachweiskette und übertragbare Erkenntnisse (15 Punkte)

| Kriterium | Punkte | Was ist genau passiert & wo liegt der Beweis? |
|---|---:|---|
| **`D1` Nachweiskette, menschliche Verantwortung und Status** | 8 | Durchgängige Kette `Issue -> Run-ID -> Trace -> Manifest -> Diff-Patch -> Review -> Commit` in `evidence/session-05.md`. Menschlicher Faktencheck für `SR-01` (`muhammad`, `mirko`, `saad`) und klare Trennung zwischen technischer Freigabe (`approved`) und Kundenabnahme (`pending_customer_acceptance`). |
| **`D2` Übertragbare Erkenntnisse und Vorführung** | 7 | Drei konkret mit Run-IDs, Tokenzahlen und Commits belegte Lessons in Abschnitt 6 von `evidence/session-05.md`. |

---

## 4. Spickzettel für die Live-Vorführung (10 Minuten Ablauf + Antworten auf Prüferfragen)

### Schritt 1: Produkt live im Browser & Terminal zeigen (ca. 3 Minuten)
1. **Terminal 1 (Webserver starten):**
   ```powershell
   cd C:\Users\yawpo\PycharmProjects\client-01-website
   python -m http.server 8080 --directory site
   ```
2. **Browser öffnen:**
   - `http://localhost:8080/index.html` $\rightarrow$ unter *Für wen wir arbeiten* auf **`Technische Einkaufsabteilungen`** zeigen.
   - Oben rechts auf **`English (EN)`** klicken $\rightarrow$ `http://localhost:8080/en.html` zeigen (Titel, 3 Services, `Technical purchasing departments`, `Request information` mailto-Link, Kurshinweis, Rückwechsel `Deutsch (DE)`).
   - Kurz in den Browser-DevTools (`F12`) **`375 px`** und **`1280 px`** zeigen und mit der `Tab`-Taste den blauen Fokus-Rahmen (`:focus-visible`) vorführen.
3. **Terminal 2 (Alle 10 Produkttests ausführen):**
   ```powershell
   cd C:\Users\yawpo\PycharmProjects\client-01-website
   python -m unittest discover -s tests -p "test_*.py" -v
   ```

### Schritt 2: Sicherheitsanfrage `SR-01` präsentieren (ca. 3 Minuten)
Öffnet `client-01-website/docs/security-advisory-sr01.md` und nennt diese 4 Punkte:
1. **Quellen:** ENISA-Warnung vom `21.10.2026` (`CVE-2026-109618`, `CVE-2026-109619`) & PHP 8.2 ChangeLog (geprüft am `2026-11-09`).
2. **Warum `"PHP 8.2"` allein nichts beweist:** Weder das genaue Patchlevel (`8.2.x` / Security-Backports) noch die aktive PHP-Einbindung oder verbleibende `.php`-Dateien im Webroot sind daraus ersichtlich.
3. **Komponenteninventar:** Unser neues Produkt besteht nur aus statischem HTML5 (`index.html`, `en.html`) und lokalem CSS3 (`styles.css`) – **kein PHP, kein CMS, keine Datenbank, kein Formular**.
4. **Kernaussage `"statisch != automatisch sicher"`:** Wenn auf dem Server alte `.php`-Dateien des CMS liegen bleiben und PHP aktiv bleibt, ist der Server trotz statischer `index.html` weiter direkt über `.php`-URLs angreifbar! Deshalb unsere Empfehlung (Option 3): **Alte `.php`-Dateien aus dem Webroot löschen und PHP beim Hoster komplett deaktivieren.**

### Schritt 3: Factory-Experiment `F-NEW` (`R-01`), Kosten & Lessons zeigen (ca. 4 Minuten)
Öffnet `agentic_ai_haw_2627/evidence/session-05.md`:
1. **Abschnitt 3.3 (Tabelle `F-BASE` vs. `F-NEW` auf `R-01`):**
   - Erklärt: *„Weil `F-NEW` den bereits geprüften `R-BASE`-Stand aus `site/index.html` extrahiert und `qwen3:4b` nur noch nach den Delta-Keys fragt, sank die Laufzeit des Implementierungsschritts auf `R-01` von **`137,14 s` auf `3,76 s` bzw. `3,86 s` (`-97,2 %`)** und die Output-Tokens von **`595` auf `105` (`-82,4 %`)** – bei exakt identischem SHA-256-Ergebnis (`0b05ef0b...`).“*
2. **Abschnitt 2.2 (Echte Selbstkorrektur bei `CR-01`):**
   - Erklärt: *„Beim Kundenlauf `WF-WEBSITE01-S5-CR01` hat `qwen3:4b` in Iteration 1 sechs `EN_*`-Keys vergessen. Unser strikter Validator ohne Fallback hat das in `3,9 s` erkannt, die fehlenden Keys als Feedback übergeben, und in Iteration 2 hat der Agent in `6,75 s` beide Seiten (`index.html` + `en.html`) fehlerfrei generiert.“*
3. **Abschnitt 5 & Status-Disziplin:**
   - Kundenprojekt S3–S5 liegt mit **`718,36` von `946,0` Credits (`24,1 %` unter Budget)** im grünen Bereich.
   - Technischer Freigabestatus ist **`approved`**, Kundenabnahmestatus steht bewusst auf **`pending_customer_acceptance`**, bis die Lehrperson heute im Termin die Abnahme erteilt.


---

## 5. Kurzübersicht nach Terminen: Jedes Requirement aus Termin 3, 4 und 5 & wie wir es gelöst haben

### Termin 3 – Einstieg in das Kundenprojekt & erster vertikaler Durchstich (`NW-S3-001`)
1. **Strikte Repository-Trennung (`A1`):**
   - *Gelöst durch:* Eigenes Kunden-Repo `client-01-website` getrennt von der Factory `agentic_ai_haw_2627`, verbunden über `config/projects/website-01.yaml`.
2. **Workspace-Sandbox für Produkt-Tools (`A4`):**
   - *Gelöst durch:* `validate_product_workspace_path` in `src/agents/customer_delivery_workflow.py` erlaubt Schreibzugriffe (`write_product_file_tool`) ausschließlich unter `site/` und blockiert `../`-Traversal, `.env*`, `.git/` und `tests/`.
3. **Multi-Agenten-Kooperation & strukturierte Handover (`A2`, `A3`):**
   - *Gelöst durch:* LangGraph-Workflow `Architect -> Implementation -> Product QA -> Human Gate` mit Pydantic-Verträgen (`ProductHandoverPayload`, `QAHandoverPayload`) und begrenzter Korrekturschleife (`max_correction_loops = 2`).
4. **Erster Produkt-Slice (`B1`–`B3`: `AC-01`, `AC-02` mit 1 Leistung `N-03`, `AC-04`):**
   - *Gelöst durch:* Erzeugung von `site/index.html` mit `N-01` (`Nordwerk Industrie-Service`), `N-02`, `N-03` (`Wartungsplanung`), `N-08` (`mailto:kontakt@nordwerk.example`, kein `<form>`) und `N-09` (Kurshinweis) im realen Ollama-Lauf `WF-WEBSITE01-S3-002`, geprüft durch `tests/test_website_s3.py`.
5. **Budgetplan für S3/S4 + S5-Reserve (`C2`, `C3`):**
   - *Gelöst durch:* Separater Kunden-Budgetplan (`631,0` Credits für S3/S4 + `315,0` Credits Reserve für S5 = `946,0` Credits) getrennt vom Factory-Entwicklungsbudget (`400,0` Credits) in `costs/cost-model.yaml`.

### Termin 4 – Vollständiger Release-Kandidat (`AC-01`–`AC-08`), Quality Gate & Baseline `R-BASE` (`NW-S4-001`)
1. **Session-3-Feedback-Korrekturen:**
   - *Kein stiller HTML-Fallback:* `_validate_and_normalize_implementation_fields` wirft sofort einen `ValueError`, wenn der LLM-Call fehlschlägt oder Pflichtfelder fehlen.
   - *Verifizierter sauberer `factory_commit`:* `_get_factory_git_state` blockiert reale Läufe bei uncommitteten Factory-Änderungen und speichert `workflow_code_sha256`.
2. **Vollständiger deutscher Release-Kandidat (`B1`–`B5`: `AC-01` bis `AC-08`):**
   - *Gelöst durch:* Ergänzung der Leistungen 2 & 3 (`Ersatzteilkoordination`, `Betriebsdokumentation`), der Zielgruppen (`Kleine Produktionsbetriebe`, `Technische Serviceunternehmen`), der Arbeitsweise (`N-07`), der `#`-Ankernavigation (`#leistungen`, `#zielgruppen`, `#arbeitsweise`, `#kontakt`), des responsiven CSS (`375 px` & `1280 px`) und des sichtbaren Tastaturfokus (`:focus-visible` `#005fcc`) im Lauf `WF-WEBSITE01-S4-001` (committet als `R-BASE` `ecb5981`).
3. **Drei automatisierte Prüf-Familien & kontrollierter Fehlerlauf (`A3`, `A4`):**
   - *Gelöst durch:* `tests/test_website_s4.py` (Familie 1: Inhalt/Guardrails, Familie 2: Kontakt/Anker, Familie 3: Responsivität/A11y/lokale Assets). Im Negativlauf `WF-WEBSITE01-S4-FAULT-001` wurde `mailto:falsch@nordwerk.example` injiziert, von `test_website_s4.py` (`exit_code=1`) erkannt, auf `escalate_to_human` gesetzt und im Human Gate abgelehnt (`changes_requested`).
4. **Referenzaufgabe `R-01` als Baseline-Messung (`C1`, `L4.4`):**
   - *Gelöst durch:* Isolierter Lauf `R-01-BASELINE-001` (4. Leistungskarte `Projektkoordination`) mit `F-BASE` (`54a626b`) auf `R-BASE` (`ecb5981`), der den Engpass (`137,14 s` Implementierungszeit, `595` Output-Tokens) offenlegte.

### Termin 5 – Kundenänderung `CR-01`, Factory-Upgrade `F-NEW`, Sicherheitsanfrage `SR-01` & Abschluss (`NW-S5-CR01`)
1. **Session-4-Feedback-Korrekturen:**
   - *Gelöst durch:* Strikte RFC-4180-Anführungszeichen in `costs/usage.csv` + Verbuchung aller 4 CI-Läufe vom `2026-11-02`; explizite Trennung zwischen `uncommitted_worktree` und `committed_after_review` (`subsequent_product_commit`); Entfernung aller lokalen `C:\`-Pfade.
2. **Kundenänderung `CR-01` (`AC-09`, `A2`, `B1`–`B3`, `L5.1`):**
   - *Gelöst durch:* Issue & Impact-Analyse (`docs/issue-03-session-05-cr01.md`), 3. deutsche Zielgruppe `Technische Einkaufsabteilungen` in `site/index.html`, eigenständige englische Einstiegsseite `site/en.html` (`<html lang="en">`, `<title>`, alle 9 englischen Pflichtstrings, `Request information` $\rightarrow$ `mailto:kontakt@nordwerk.example`, Sprachwechsel `index.html` $\leftrightarrow$ `en.html`) + `#en`-Sektion, ausgeliefert über `WF-WEBSITE01-S5-CR01` und geprüft durch `tests/test_website_s5.py` (`10/10` Tests `OK`).
3. **Gezielte Factory-Verbesserung `F-NEW` & `R-01`-Vorher/Nachher-Vergleich (`A4`, `C1`–`C3`, `L5.2`):**
   - *Gelöst durch:* `F-NEW` (`5f3b49e`) mit Delta-Key-Merging (`extract_verified_baseline_from_product_html`) und deterministischem In-Memory Pre-Gate-Validator (`validate_rendered_html_pre_gate`). Auf `R-01` ($n=2$ Läufe: `R-01-FNEW-001`, `R-01-FNEW-002`) sank die Implementierungszeit von **`137,14 s` auf `3,76 s` / `3,86 s` (`-97,2 %`)** und die Output-Tokens von **`595` auf `105` / `104` (`-82,4 %`)** bei identischem SHA-256 (`0b05ef0b...`).
4. **Komponenteninventar & Sicherheitsanfrage `SR-01` (`AC-10`, `B4`, `B5`, `D1`, `L5.3`):**
   - *Gelöst durch:* `docs/security-advisory-sr01.md` mit separatem Komponenteninventar (Produkt = statisches HTML5/CSS3, PHP/CMS/DB/Formular = `not used`), Analyse der ENISA-Warnung vom `21.10.2026` (`CVE-2026-109618`, `CVE-2026-109619`) & PHP 8.2 ChangeLog (Abruf `2026-11-09`), 4 Hoster-Fragen, Optionenvergleich, Erklärung `"statisch != automatisch sicher"` und menschlichem Faktencheck (`muhammad`, `mirko`, `saad`).
5. **Übergabe, Kostenbilanz S3–S5 & 3 belegte Lessons (`B6`, `C4`, `D1`, `D2`, `L5.4`):**
   - *Gelöst durch:* `docs/release-s5-handover.md`, aktualisierte `README.md`, Gesamtkostenbilanz (`718,36` von `946,0` Kunden-Credits = `24,1 %` unter Budget; `400,0` Factory-Credits im Plan), Trennung von technischer Freigabe (`approved`) und Kundenabnahme (`pending_customer_acceptance`) sowie 3 mit Run-IDs/Tokens belegte Lessons in `evidence/session-05.md`.
