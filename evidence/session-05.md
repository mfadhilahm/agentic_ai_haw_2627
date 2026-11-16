# Session 5 Evidence – Controlled Change (`CR-01`), Targeted Factory Improvement (`F-NEW`), Security Advisory (`SR-01`), and Final Release (`website-01`)

- **Company / Factory Repository:** `HAW Agentic Software Factory` (`https://github.com/mfadhilahm/agentic_ai_haw_2627`)
- **Customer Product Repository:** `Nordwerk Industrie-Service` (`../client-01-website`, GitHub: `https://github.com/mfadhilahm/client-01-website`)
- **Project ID / Session 5 Task IDs:** `website-01` / `NW-S5-CR01` (`CR-01`), `NW-S5-SR01` (`SR-01`), `R-01` (`F-BASE` vs. `F-NEW` Experiment)
- **Session:** Termin 5 (`2026-11-09`)
- **Team Members (Accountable Humans, Team Size = 6):**
  - `yaw` – Commission Lead & Cost / Portfolio Accounting
  - `saad` – Requirements Owner & Technical Release Approval
  - `felix` – Project Manager, QA & Regression Checks
  - `minh` – Software Architect (`dev_architect_agent` – `software_architect`)
  - `mirko` – Technical Delivery Lead (`dev_architect_agent` – `backend_api_engineer`)
  - `muhammad` – Agent & Integration Engineer & Security Advisory Lead (`SR-01`)

---

## Executive Summary & Version Matrix (`A1`, `D1`, `D2`)

| Reference Role | Repository | Commit SHA / Tag | Direct GitHub Link & Verification State |
|---|---|---|---|
| **`F-BASE` (Session 4 Factory Baseline)** | `agentic_ai_haw_2627` | `54a626b18e0ce4a58142468a820e4626bd536de0` (`F-BASE`) | [`54a626b`](https://github.com/mfadhilahm/agentic_ai_haw_2627/commit/54a626b18e0ce4a58142468a820e4626bd536de0) (`workflow_code_sha256: e306c649...`) |
| **`F-NEW` (Session 5 Improved Factory)** | `agentic_ai_haw_2627` | `5f3b49e215f1b9e60c487c7015d26e7c68372107` (`F-NEW`) | [`5f3b49e`](https://github.com/mfadhilahm/agentic_ai_haw_2627/commit/5f3b49e215f1b9e60c487c7015d26e7c68372107) (`factory_commit_clean: true`, `workflow_code_sha256: b5df5d710251e0bfdb35af8a8b14fcd4e791f99d2c62aecc803f3c310ca2a883`) |
| **`R-BASE` (Session 4 Product Baseline)** | `client-01-website` | `ecb598140d0b2d0778d891f9bc1acc8c36295a93` (`R-BASE`) | [`ecb5981`](https://github.com/mfadhilahm/client-01-website/commit/ecb598140d0b2d0778d891f9bc1acc8c36295a93) (`site/index.html` SHA-256: `4a6a61db...`) |
| **Product Input Commit for `WF-WEBSITE01-S5-CR01`** | `client-01-website` | `c3866e164d89a19bc83557058318319765b339b3` | [`c3866e1`](https://github.com/mfadhilahm/client-01-website/commit/c3866e164d89a19bc83557058318319765b339b3) (contains `R-BASE` `site/index.html` + `docs/issue-03-session-05-cr01.md` + `tests/test_website_s5.py`) |
| **Final Session 5 Product Release (`R-S5-FINAL` / `v1.0.0-s5-rc`)** | `client-01-website` | `84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f` (`R-S5-FINAL`, `v1.0.0-s5-rc`) | [`84d5baf`](https://github.com/mfadhilahm/client-01-website/commit/84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f) (`site/index.html` SHA-256: `6ebd91ed...`, `site/en.html` SHA-256: `8b43eaa3...`, `10/10` unit & regression tests passed) |
| **Technical Release Gate Status** | Both Repos | **`approved`** | Reviewed and signed off by `saad` (Release Owner), `felix` (QA), and `muhammad` (Security Advisory) in [`runs/website-01/WF-WEBSITE01-S5-CR01/review.json`](../runs/website-01/WF-WEBSITE01-S5-CR01/review.json) |
| **Customer Acceptance Status** | `client-01-website` | **`pending_customer_acceptance`** | Explicitly separated from technical release approval; final customer acceptance is granted live by the instructor in Session 5. |

---

## 1. Remediation of Session 4 Feedback (`Feedback_Session_04_Team_1-1.md`)

All points raised in the Session 4 feedback were resolved and covered by automated regression tests in [`tests/test_session_04_factory.py`](../tests/test_session_04_factory.py):
1. **Strict RFC-4180 CSV Quoting & Complete CI Run Accounting in [`costs/usage.csv`](../costs/usage.csv):**
   - Every `notes` field in `costs/usage.csv` is wrapped in RFC-4180 double quotes (`"..."`), verified by `test_session_04_feedback_usage_csv_and_worktree_commit_distinction` asserting `len(row) == 8` and `None not in dict_row` across all rows.
   - Updated the `2026-11-02` GitHub Actions CI row from `2` runs (`2.0` credits) to all **`4` actual GitHub Actions runs (`4.0` credits)** executed on `2026-11-02` (`46ed1f9`, `6393ebf`, `54a626b`, `a03d3be`) in both [`costs/usage.csv`](../costs/usage.csv) and [`costs/cost-model.yaml`](../costs/cost-model.yaml).
2. **Distinction Between Uncommitted Worktree Changes (`uncommitted_worktree`) and Subsequent Product Commits (`committed_after_review`):**
   - [`src/agents/customer_delivery_workflow.py`](../src/agents/customer_delivery_workflow.py) now records `product_worktree_state: "uncommitted_worktree"` and `product_output_commit: "uncommitted_worktree"` at the end of a workflow run (since the agent writes to `site/` without running `git commit`), and updates `product_worktree_state: "committed_after_review"` and `subsequent_product_commit: "<sha>"` when `record_customer_human_review(..., tested_source_commit="<sha>")` is called after committing the reviewed product state.
   - Normalized all run manifests, workflow reports, and review records across Sessions 3–5 so no local Windows paths (`C:\...`) appear anywhere under `runs/website-01/`.

---

## 2. Customer Change `CR-01` (`NW-S5-CR01`): Impact Analysis, Multi-Agent Delivery & Regression (`A1`–`A3`, `B1`–`B3`, `L5.1`)

### 2.1 Customer Change Issue & Impact Analysis (`A2`)
- **Customer Change Issue `#3` (`NW-S5-CR01`):** [`client-01-website/docs/issue-03-session-05-cr01.md`](https://github.com/mfadhilahm/client-01-website/blob/84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f/docs/issue-03-session-05-cr01.md)
- **Scope (`AC-09` + Regression `AC-01`–`AC-08`):**
  1. Expand German target groups (`#zielgruppen`) on `site/index.html` with **`Technische Einkaufsabteilungen`** (`N-06_group_3`) while preserving all 14 existing German `N-01`–`N-09` strings and anchors.
  2. Add a standalone English entry page **`site/en.html`** (`<html lang="en">`, `<title>`) plus an in-page `#en` overview section on `site/index.html` with bidirectional language switching (`index.html` $\leftrightarrow$ `en.html`) and all 9 required verbatim English strings (`Nordwerk Industrie-Service`, `Practical support for your technical operations.`, `Maintenance planning`, `Spare parts coordination`, `Operational documentation`, `Technical purchasing departments`, `Request information`, `mailto:kontakt@nordwerk.example`, `Fictional company – HAW Hamburg course project. No real offers or contact.`).

### 2.2 Real Multi-Agent Workflow Execution (`WF-WEBSITE01-S5-CR01`) & Bounded Self-Correction (`A2`, `A3`, `A4`)
- **Run Artifacts:**
  - Manifest: [`runs/website-01/WF-WEBSITE01-S5-CR01/manifest.json`](../runs/website-01/WF-WEBSITE01-S5-CR01/manifest.json)
  - Workflow Report: [`runs/website-01/WF-WEBSITE01-S5-CR01/workflow-report.json`](../runs/website-01/WF-WEBSITE01-S5-CR01/workflow-report.json)
  - Trace Log: [`runs/website-01/WF-WEBSITE01-S5-CR01/trace.jsonl`](../runs/website-01/WF-WEBSITE01-S5-CR01/trace.jsonl)
  - Diff Patch (`site/index.html` + `site/en.html`): [`runs/website-01/WF-WEBSITE01-S5-CR01/changes.patch`](../runs/website-01/WF-WEBSITE01-S5-CR01/changes.patch)
  - Human Gate Review Record: [`runs/website-01/WF-WEBSITE01-S5-CR01/review.json`](../runs/website-01/WF-WEBSITE01-S5-CR01/review.json)

| Step | Run ID | Agent (`Role`) | Accountable Human | Status | Duration (s) | Tokens (In / Out) | Credits | Key Outcome |
|---|---|---|---|---|---:|---:|---:|---|
| 1 | `6fa3d659-26cc-4ebe-aeae-1120b973230f` | `dev_architect_agent` (`software_architect`) | `minh` | `completed` | `3.9734` | `767` / `85` | `1.0585` | Inspected `docs/issue-03-session-05-cr01.md` & `site/index.html`; extracted verified 14-key `R-BASE` baseline and handed over 10 `CR-01` `delta_keys`. |
| 2 (Iter 1) | `670390c0-5806-4414-9e4e-c0e865a96a06` | `dev_architect_agent` (`backend_api_engineer`) | `mirko` | `error` | `3.9000` | `364` / `105` | `1.0505` | `qwen3:4b` omitted 6 `EN_*` delta keys; strict `F-NEW` delta validator rejected output immediately (`no fallback allowed`) without touching `site/index.html`. |
| 3 (Iter 1) | `390e1270-f912-4919-bc3f-32c7d19bf16c` | `qa-test-agent` (`qa_test_engineer`) | `felix` | `failed` | `7.0797` | `2116` / `207` | `1.1214` | Ran `tests/test_website_s5.py` (`exit_code=1`); routed exact missing-key feedback back to `implementation_node` (Iteration 2 of `max_correction_loops=2`). |
| 4 (Iter 2) | `cbcfecf4-ded3-4700-bd1b-48404d5529d4` | `dev_architect_agent` (`backend_api_engineer`) | `mirko` | `completed` | `6.7517` | `2165` / `261` | `1.1213` | Self-corrected using feedback: emitted all 10 `CR-01` delta keys, merged with `R-BASE`, passed `validate_rendered_html_pre_gate`, and wrote `site/index.html` (`6ebd91ed...`) + `site/en.html` (`8b43eaa3...`). |
| 5 (Iter 2) | `ec9d30b1-8642-4b5d-bf4b-d9ad1a78f8f6` | `qa-test-agent` (`qa_test_engineer`) | `felix` | `passed` | `4.7624` | `433` / `75` | `1.0593` | `tests/test_website_s5.py` passed (`exit_code=0`, 0 findings); transitioned to `human_gate_status = "pending_approval"`. |
| **Total** | **5 steps (2 iterations)** | **Ollama `qwen3:4b@359d7dd4bcda`** | **`saad` (Reviewer)** | **`approved` (Tech Gate)** | **`26.4672`** | **`5845` / `733`** | **`5.4110`** | **Committed in `client-01-website` as [`84d5baf`](https://github.com/mfadhilahm/client-01-website/commit/84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f) (`R-S5-FINAL`).** |

### 2.3 Complete `AC-01`–`AC-10` Verification Matrix (`B1`–`B6`)

| Criterion | Requirement Summary | Product Artifact(s) | Verification Method & Result |
|---|---|---|---|
| **AC-01** | Company name (`N-01`) & main statement (`N-02`) visible in German | `site/index.html` | Automated (`test_website_s3.py`, `test_website_s4.py`, `test_website_s5.py`) + Browser check $\rightarrow$ **Passed** |
| **AC-02** | All 3 core services (`N-03`–`N-05`) with verbatim titles & descriptions | `site/index.html` | Automated (`test_website_s4.py`, `test_website_s5.py`) $\rightarrow$ **Passed** |
| **AC-03** | Target groups (`N-06_group_1`, `N-06_group_2`) & working approach (`N-07`); no unverified claims (`ISO 9001`, `TÜV`, `24/7`) | `site/index.html` | Pre-gate validator + `test_website_s5.py` $\rightarrow$ **Passed** |
| **AC-04** | `mailto:kontakt@nordwerk.example` (`Anfrage stellen`), no `<form>`, course notice (`N-09`) | `site/index.html` | Pre-gate validator + `test_website_s5.py` $\rightarrow$ **Passed** |
| **AC-05** | Semantic landmarks (`header`, `nav`, `main`, `section`, `footer`), resolving `#`-anchors, local assets only | `site/index.html`, `site/styles.css` | Pre-gate anchor validator + `test_website_s5.py` $\rightarrow$ **Passed** |
| **AC-06** | Responsive layout at `375 px` (Mobile) and `1280 px` (Desktop), `0 px` horizontal overflow | `site/index.html`, `site/en.html`, `site/styles.css` | CSS checks + Browser DevTools review at `375×812` & `1280×800` $\rightarrow$ **Passed** |
| **AC-07** | Keyboard accessibility (`Tab`/`Shift+Tab`/`Enter`, `:focus-visible` outline `#005fcc`, skip link) | `site/index.html`, `site/en.html`, `site/styles.css` | Automated CSS check + manual keyboard walkthrough $\rightarrow$ **Passed** |
| **AC-08** | Reproducible README start/test documentation & automated product tests | `README.md`, `docs/release-s5-handover.md`, `tests/test_website_s5.py` | `python -m unittest discover -s tests -p "test_*.py" -v` (`10/10 OK` in `0.003s`) $\rightarrow$ **Passed** |
| **AC-09 (`CR-01`)** | 3rd German target group `Technische Einkaufsabteilungen` + English entry page `site/en.html` (`<html lang="en">`, `<title>`, all 9 verbatim English strings, `Request information` mailto, DE $\leftrightarrow$ EN switch) + `#en` section | `site/index.html`, `site/en.html`, `docs/issue-03-session-05-cr01.md` | `test_01_cr01_german_target_group_and_language_switch` & `test_02_cr01_english_entry_page_and_contact` in `test_website_s5.py` $\rightarrow$ **Passed** |
| **AC-10 (`SR-01`)** | Component inventory (`B4`) + ~1-page customer security response (`B5`) citing ENISA (`21.10.2026`, `CVE-2026-109618`/`109619`) & PHP 8.2 sources with `"statisch != sicher"` and human fact-check (`D1`) | `docs/security-advisory-sr01.md` | Human fact-check & sign-off by `muhammad`, `mirko`, and `saad` (`2026-11-09`) $\rightarrow$ **Passed** |

---

## 3. Targeted Factory Improvement (`F-NEW`) & Controlled `R-01` Experiment (`A4`, `C1`–`C3`, `L5.2`)

### 3.1 Hypothesis, Root Cause in `F-BASE`, and Mechanism of `F-NEW` (`C1`)
- **Observed Bottleneck in Session 4 (`F-BASE` `54a626b`, Run `R-01-BASELINE-001`):**
  1. *Full-Payload Regeneration Bottleneck:* Even for a small incremental change (`R-01`: adding the 4th service card `Projektkoordination` to the already verified `R-BASE` `site/index.html`), `F-BASE` forced `qwen3:4b` in `implementation_node` to regenerate all 16 JSON keys (`N-01`..`N-09` + `R-01_title`, `R-01_text`, `summary`). This consumed `595` output tokens and **`137.1376 s`** (`58.6%` of the entire `234.16 s` workflow runtime).
  2. *Late Structural Fault Detection:* In `F-BASE` (`WF-WEBSITE01-S4-FAULT-001`), missing strings or broken `#anchor` links were only detected *after* writing the file and invoking the external `pytest` subprocess + QA LLM in `product_qa_node`.
- **Implemented Factory Improvement in `F-NEW` ([`5f3b49e`](https://github.com/mfadhilahm/agentic_ai_haw_2627/commit/5f3b49e215f1b9e60c487c7015d26e7c68372107), [`src/agents/customer_delivery_workflow.py`](../src/agents/customer_delivery_workflow.py)):**
  1. **Verified Baseline Extraction & Delta-Key Merging (`extract_verified_baseline_from_product_html`):** `architect_node` inspects `site/index.html` in the product checkout. If all 14 `R-BASE` (`SESSION_04_REQUIRED_CONTENT`) strings are verified present in `site/index.html` and the task defines additional keys, `architect_node` populates `handover.baseline_content` and `handover.delta_keys`. `implementation_node` prompts `qwen3:4b` **only** for `handover.delta_keys` + `"summary"`, verifies that every delta key is returned non-empty by the LLM (**zero silent fallback**), and merges `{**handover.baseline_content, **flat_llm_fields}` prior to rendering.
  2. **Deterministic In-Memory Pre-Gate HTML & Anchor Validator (`validate_rendered_html_pre_gate`):** Before writing product files or handing over to `product_qa_node`, `implementation_node` deterministically checks in `< 1 ms` that all required verbatim strings are present, all `href="#..."` anchors resolve to existing `id="..."` attributes, and no `<form>` or forbidden claims (`ISO 9001`, `TÜV`, `24/7`) exist.

### 3.2 Controlled Experimental Setup (`C2`)
To ensure a fair, apples-to-apples comparison, all external variables were held strictly constant:
- **Reference Task:** `R-01` (*Add 4th service card `"Projektkoordination"` with `"Wir koordinieren klar abgegrenzte technische Vorhaben mit Ihrem Team."`*)
- **Product Starting State (`R-BASE`):** Fresh isolated git checkout of `client-01-website` at commit `ecb598140d0b2d0778d891f9bc1acc8c36295a93`
- **Model & Parameters:** Local Ollama `qwen3:4b@359d7dd4bcda`, `temperature = 0.0`, `reasoning = False` (`/no_think`), `json_mode = True`, `max_correction_loops = 2`
- **Sample Size:** `n = 1` baseline run with `F-BASE` (`R-01-BASELINE-001`) compared against **`n = 2` independent runs with `F-NEW`** (`R-01-FNEW-001` and confirmation run `R-01-FNEW-002`).

### 3.3 Before (`F-BASE`) vs. After (`F-NEW`) Empirical Comparison (`C2`, `C3`)

| Metric | `F-BASE` (`R-01-BASELINE-001`) | `F-NEW` Run 1 (`R-01-FNEW-001`) | `F-NEW` Run 2 (`R-01-FNEW-002`) | `F-NEW` Mean ($n=2$) vs. `F-BASE` ($\Delta$) |
|---|---:|---:|---:|---:|
| **Factory Commit** | `54a626b` (`F-BASE`) | `5f3b49e` (`F-NEW`) | `5f3b49e` (`F-NEW`) | Versioned upgrade |
| **Product Input Commit (`R-BASE`)** | `ecb5981` | `ecb5981` | `ecb5981` | Identical baseline |
| **Model & Digest** | `qwen3:4b@359d7dd4bcda` | `qwen3:4b@359d7dd4bcda` | `qwen3:4b@359d7dd4bcda` | Identical model |
| **Architect Step Duration (s)** | `67.9889 s` | `57.3129 s` *(cold load)* | `4.4740 s` *(warm)* | `30.8935 s` (**`-54.6%`**) |
| **Implementation Step Duration (s)** | **`137.1376 s`** | **`3.7578 s`** | **`3.8584 s`** | **`3.8081 s` (`-97.2%`!)** |
| **QA Step Duration (s)** | `29.0376 s` | `4.7028 s` | `4.6641 s` | `4.6835 s` (**`-83.9%`**) |
| **Total Workflow Duration (s)** | **`234.1641 s`** | **`65.7735 s`** | **`12.9965 s`** | **`39.3850 s` (`-83.2%`)** |
| **Implementation Tokens (In / Out)** | `566` / **`595`** | `207` / **`105`** | `207` / **`104`** | `207` / **`104.5` (`-82.4%` out)** |
| **Total Workflow Tokens (In / Out)** | `2114` / **`819`** | `1258` / **`332`** | `1258` / **`316`** | `1258` / **`324` (`-60.4%` out)** |
| **Implementation Step Credits** | `2.3930` | `1.0459` | `1.0469` | **`1.0464` (`-56.3%`)** |
| **Total Agent Workflow Credits** | **`5.4166`** | **`3.6962`** | **`3.1678`** | **`3.4320` (`-36.6%`)** |
| **Iterations Used / Pre-Gate Passed** | `1` / N/A | `1` / `true` (`0` findings) | `1` / `true` (`0` findings) | `1` iteration |
| **Output `site/index.html` SHA-256** | `0b05ef0b38da40af...` | `0b05ef0b38da40af...` | `0b05ef0b38da40af...` | **100% byte-identical** |
| **Product Check (`verify_r01_baseline.py`)** | `4/4 passed` (`exit_code=0`) | `4/4 passed` (`exit_code=0`) | `4/4 passed` (`exit_code=0`) | **100% pass rate (0 regressions)** |
| **Human Review / Rework Effort** | `10 min` review / `0 min` rework | `3 min` review / `0 min` rework | `2 min` review / `0 min` rework | **`-75%` review time** (only delta keys changed) |

### 3.4 Evidence-Based Decision & Limitations (`C3`)
- **Decision:** **Adopt `F-NEW` (`5f3b49e`) permanently as the production Factory workflow.**
- **Justification:** Across both confirmation runs (`R-01-FNEW-001` and `R-01-FNEW-002`), `F-NEW` reduced `implementation_node` output tokens by **`82.4%`** (`595` $\rightarrow$ `104.5` tokens), cut implementation latency by **`97.2%`** (`137.14 s` $\rightarrow$ `3.81 s`), lowered total workflow agent credits by **`36.6%`** (`5.4166` $\rightarrow$ `3.4320` credits), and produced the **exact same byte-for-byte verified HTML artifact (`0b05ef0b...`)** without any loss of quality or regression coverage.
- **Limitations & Honest Trade-Offs:**
  1. Delta-key merging applies only when the product repository already contains a verified baseline (`extract_verified_baseline_from_product_html`); greenfield builds from an empty template still require full-key generation.
  2. When a delta request has many new keys (e.g., 10 delta keys in `NW-S5-CR01`), a small 4B model (`qwen3:4b`) can still omit keys on the first attempt (as seen in `WF-WEBSITE01-S5-CR01` Iteration 1). However, because `F-NEW` combines delta prompting with a strict no-fallback delta check (`missing_deltas`) and the bounded retry loop, the retry took only `6.75 s` instead of `>130 s`!

---

## 4. Security Enquiry `SR-01` & Component Inventory (`AC-10`, `B4`, `B5`, `D1`, `L5.3`)

The complete component inventory and ~1-page customer response are delivered in [`client-01-website/docs/security-advisory-sr01.md`](https://github.com/mfadhilahm/client-01-website/blob/84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f/docs/security-advisory-sr01.md):
- **Primary Sources Cited (Accessed `2026-11-09`):**
  1. **ENISA Joint Statement (21.10.2026):** *Joint Statement on Critical PHP Vulnerabilities (`CVE-2026-109618` and `CVE-2026-109619`)*, `https://www.enisa.europa.eu/news/joint-statement-on-critical-php-vulnerabilities` *(course scenario CVE identifiers noted explicitly)*.
  2. **Linked PHP Source:** *PHP 8.2 ChangeLog / Security Release Notes*, `https://www.php.net/ChangeLog-8.php#PHP_8_2` and `https://www.php.net/archive/2026.php`.
- **Key Findings & Customer Guidance Summary:**
  - **Known vs. Open:** Our delivered product (`site/index.html`, `site/en.html`, `site/styles.css`) uses **`0` PHP components, `0` CMS components, `0` databases, and `0` server-side forms**. However, the customer's legacy hosting panel entry `"PHP 8.2"` proves neither vulnerability nor safety because it omits the exact patch level (`8.2.x`), Linux distribution security backports, and whether `php-fpm`/`mod_php` and legacy `.php` CMS files remain reachable in the public `DocumentRoot`.
  - **4 Mandatory Hoster Questions:** (1) Exact `php -v` patch level & `CVE-2026-109618`/`109619` patch status, (2) complete deactivation of PHP for the domain, (3) removal of all residual `.php` CMS/form files from `DocumentRoot`, and (4) inspection of access logs since October 2026.
  - **Option Comparison & Recommendation:** Compared Option 1 (In-Place Patching of PHP + Legacy CMS), Option 2 (Immediate Temporary Isolation), and **Option 3 (Static Replacement + Deactivating PHP & Deleting Legacy `.php` Files – Recommended)**.
  - **Why `"statisch != automatisch sicher"`:** Uploading static HTML alone does **not** secure the server if legacy `.php` scripts remain in the webroot with PHP active; furthermore, TLS/HTTPS configuration, web server patching, security headers, and SFTP/hosting credential protection remain mandatory.
  - **Human Fact-Check Sign-Off (`D1`):** Verified and signed off by `muhammad` (Security Advisory Lead), `mirko` (Technical Delivery), and `saad` (Release Owner) on `2026-11-09`.

---

## 5. Session 5 & Cumulative S3–S5 Cost Accounting (`C4`, `D1`)

All costs are recorded in [`costs/usage.csv`](../costs/usage.csv) (strictly RFC-4180 quoted, 8 columns per row) and [`costs/cost-model.yaml`](../costs/cost-model.yaml) using the official course rates (`100` credits/h human, `1.0` base + `0.01/s` + `0.02/1k in` + `0.04/1k out` agent, `1.0` credit/CI run).

| Cost Category | Planned Budget (Credits) | Session 3 Actual | Session 4 Actual | Session 5 Actual | S3–S5 Cumulative Total | Variance vs. Budget |
|---|---:|---:|---:|---:|---:|---:|
| **Customer Delivery, `SR-01`, Review & Rework (Human)** | `900.0000` *(600 S3/S4 + 300 S5 Reserve)* | `175.0000` *(1.75 h)* | `250.0000` *(2.50 h)* | `250.0000` *(2.50 h)* | **`675.0000`** *(6.75 h)* | **`-225.0000` (Under budget)** |
| **Multi-Agent Workflows & `R-01` Runs (Agent)** | `34.0000` *(25 S3/S4 + 9 S5)* | `8.2900` *(6 calls)* | `15.7936` *(9 calls)* | `12.2750` *(11 calls)* | **`36.3586`** *(26 calls)* | `+2.3586` *(due to `n=2` `R-01` & retry)* |
| **GitHub Actions CI Runs (CI)** | `12.0000` *(6 S3/S4 + 6 S5)* | `1.0000` *(1 run)* | `4.0000` *(4 runs)* | `2.0000` *(2 runs)* | **`7.0000`** *(7 runs)* | **`-5.0000` (Under budget)** |
| **Subtotal: Customer Project `website-01` (S3–S5)** | **`946.0000`** | **`184.2900`** | **`269.7936`** | **`264.2750`** | **`718.3586`** | **`-227.6414` (`24.1%` under budget)** |
| **Separate Factory Engineering (`F-BASE` $\rightarrow$ `F-NEW`)** | **`400.0000`** *(4.00 h S3–S5)* | `200.0000` *(2.00 h)* | `125.0000` *(1.25 h)* | `75.0000` *(0.75 h)* | **`400.0000`** *(4.00 h)* | **`0.0000` (On target)** |
| **Combined S3–S5 Total (Customer + Factory)** | **`1346.0000`** | **`384.2900`** | **`394.7936`** | **`339.2750`** | **`1118.3586`** | **`-227.6414` (`16.9%` under budget)** |

---

## 6. Three Evidenced Transferable Lessons (`D2`, `L5.4`)

1. **Lesson 1 – Delta-Key Handovers Drastically Outperform Full-Document Regeneration on Small Local Models (`qwen3:4b`):**
   - *Concrete Evidence:* In Session 4 (`R-01-BASELINE-001`), forcing `qwen3:4b` to re-emit all 16 content keys for a 1-card addition took **`137.14 s`** and `595` output tokens (`2.3930` credits). By extracting the verified 14-key baseline from `site/index.html` and prompting only for the 2 delta keys (`R-01_title`, `R-01_text`) in `F-NEW` (`R-01-FNEW-001` & `R-01-FNEW-002`), implementation latency dropped by **`97.2%` to `3.76 s` / `3.86 s`** (`105` / `104` output tokens, `1.046` credits) while producing the exact same SHA-256 artifact (`0b05ef0b...`).
   - *Transferable Rule:* When orchestrating local 4B–8B LLMs on iterative software maintenance tasks, never ask the model to echo unchanged baseline state; extract verified state deterministically in the architect/orchestrator node and restrict the LLM prompt to the delta schema.
2. **Lesson 2 – Strict No-Fallback Schema Validation Paired with Actionable Retry Feedback Enables Fast Self-Correction:**
   - *Concrete Evidence:* After removing silent default HTML fallbacks in Session 4, our live Session 5 delivery run `WF-WEBSITE01-S5-CR01` demonstrated why strict validation + bounded retry is essential: in Iteration 1 (`run_id=670390c0`), `qwen3:4b` omitted 6 of the 10 `CR-01` delta keys. Instead of silently writing broken HTML, `implementation_node` failed in `3.90 s` with an exact list of missing keys (`EN_service_2..EN_notice`). Passed via `qa_feedback` into Iteration 2 (`run_id=cbcfecf4`), the model self-corrected in `6.75 s`, passed `validate_rendered_html_pre_gate`, and passed all 10 unit/regression tests (`run_id=ec9d30b1`).
   - *Transferable Rule:* Never mask partial LLM outputs with default fallbacks; fail fast with a machine-readable list of missing keys/constraints and feed that exact error string into a bounded ($k \le 2$) retry loop.
3. **Lesson 3 – Governance Requires Explicit Separation of Build/Test Tooling, Runtime Attack Surface, Technical Gate Approval, and Customer Acceptance:**
   - *Concrete Evidence:* In `SR-01` ([`docs/security-advisory-sr01.md`](https://github.com/mfadhilahm/client-01-website/blob/84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f/docs/security-advisory-sr01.md)), separating the Factory's Python/LLM build stack from the product's static HTML/CSS runtime proved that our delivered artifact has `0` PHP dependencies, while also revealing that `"statisch != automatisch sicher"` if the hoster leaves legacy `.php` files active in `DocumentRoot`. Similarly, in [`runs/website-01/WF-WEBSITE01-S5-CR01/manifest.json`](../runs/website-01/WF-WEBSITE01-S5-CR01/manifest.json) and [`review.json`](../runs/website-01/WF-WEBSITE01-S5-CR01/review.json), distinguishing `uncommitted_worktree` from `committed_after_review` (`84d5baf`) and `decision: "approved"` (internal technical gate) from `pending_customer_acceptance` (live instructor sign-off) eliminated audit ambiguity.
   - *Transferable Rule:* In agentic delivery pipelines, treat (a) uncommitted agent worktree output, (b) human-reviewed technical commits, and (c) external customer acceptance as distinct state transitions in every manifest and review record.

---

## 7. Verification Commands & Test Evidence (`evidence/session-05/`)

- **Factory Unit & Integration Tests (`12 passed` across S3, S4, S5):**
  - Command: `python -m pytest tests/test_session_03_factory.py tests/test_session_04_factory.py tests/test_session_05_factory.py -v`
  - Text Log: [`evidence/session-05/pytest.txt`](session-05/pytest.txt)
  - JUnit XML: [`evidence/session-05/pytest.xml`](session-05/pytest.xml)
- **Customer Product & Regression Tests (`10 passed` across S3, S4, S5 in `../client-01-website`):**
  - Command: `python -m unittest discover -s ../client-01-website/tests -p "test_*.py" -v`
