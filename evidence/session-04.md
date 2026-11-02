# Session 4 – Release Candidate, Quality Gate & R-01 Baseline Evidence (`evidence/session-04.md`)

- **Project ID:** `website-01` (**Nordwerk Industrie-Service**)
- **Customer Task ID:** `NW-S4-001` (Release Candidate `AC-01`–`AC-08`) & `R-01` (Isolated Baseline Experiment)
- **Date:** 2026-11-02

---

## 1. Repository, Commit & Tag References (`A1`, `B5`, `C1`, `D2`)

| Repository | Role | GitHub URL / Checkout Path | Frozen Input Commit / Tag | Output / Release Candidate Commit / Tag |
| :--- | :--- | :--- | :--- | :--- |
| **`agentic_ai_haw_2627`** | Software Factory | `https://github.com/mfadhilahm/agentic_ai_haw_2627` | **`F-BASE`:** `46ed1f9d7c5f6163e5d90117e204809cdc498de9` (`46ed1f9`) | Evidence commit (Session 4 submission) |
| **`client-01-website`** | Customer Product | `https://github.com/mfadhilahm/client-01-website` (`../client-01-website`) | Pre-run S4 input commit (building on S3 `5b9aefa`) | **Tag `R-BASE`** (Approved Release Candidate for `AC-01`–`AC-08`) |
| **`client-01-website` (`experiment/r-01-baseline`)** | Isolated `R-01` Experiment | Separate branch/worktree checked out from `R-BASE` | **`R-BASE`** (frozen Release Candidate commit) | Isolated `R-01` output (not merged into `main` / customer release) |

- **Project Configuration:** [`config/projects/website-01.yaml`](../config/projects/website-01.yaml)
- **Customer Issue (`NW-S4-001`):** `client-01-website/docs/issue-02-session-04.md`
- **Release Candidate Checklist & Browser Review Protocol:** `client-01-website/docs/release-candidate-s4.md`

---

## 2. Session 3 Feedback Fixes & Real Session 4 Factory Delivery Run (`A1`, `A2`, `A4`, `L4.1`)

### 2.1 Technical Remediation of Session 3 Feedback
1. **No Silent Default-HTML Fallback on Failed or Unparseable LLM Calls:**
   - [`_validate_and_normalize_implementation_fields`](../src/agents/customer_delivery_workflow.py) and [`_render_html_document`](../src/agents/customer_delivery_workflow.py) in [`src/agents/customer_delivery_workflow.py`](../src/agents/customer_delivery_workflow.py) were refactored to remove all `DEFAULT_REQUIRED_CONTENT` fallbacks.
   - If an LLM call fails, times out, returns truncated/invalid JSON, or omits required content keys, `implementation_node` marks `status = "error"`, writes **no** file (`written_file = None`, `ready_for_qa = False`), `product_qa_node` marks QA as `failed` even if a prior file existed on disk, and `human_gate_node` routes to `escalate_to_human` (blocking approval).
   - Deterministically verified by `test_failed_or_unparseable_llm_call_never_masked_by_default_html` in [`tests/test_session_04_factory.py`](../tests/test_session_04_factory.py).
2. **Verified Clean `factory_commit` Containing the Executed Workflow Code:**
   - [`_get_factory_git_state`](../src/agents/customer_delivery_workflow.py) and [`_compute_workflow_code_sha256`](../src/agents/customer_delivery_workflow.py) check `git status --porcelain -- src config organization` before real runs and record `factory_commit`, `factory_commit_clean`, `factory_dirty_files`, and `workflow_code_sha256` in both `manifest.json` and `workflow-report.json`.
   - Real LLM runs refuse to start if `src/`, `config/`, or `organization/` has uncommitted modifications; verified by `test_factory_commit_clean_check_blocks_dirty_runs_and_records_code_hash` in [`tests/test_session_04_factory.py`](../tests/test_session_04_factory.py).

### 2.2 Real Multi-Agent Delivery Run (`WF-WEBSITE01-S4-001` on `F-BASE`)
- **Run Directory:** `runs/website-01/WF-WEBSITE01-S4-001/`
- **Manifest & Trace:** `runs/website-01/WF-WEBSITE01-S4-001/manifest.json` · `runs/website-01/WF-WEBSITE01-S4-001/trace.jsonl`
- **Unified Product Diff:** `runs/website-01/WF-WEBSITE01-S4-001/changes.patch`
- **Human Gate Approval:** `decision = "approved"` by reviewer `saad` (`runs/website-01/WF-WEBSITE01-S4-001/review.json`) after automated checks and manual browser/keyboard verification (`client-01-website/docs/release-candidate-s4.md`).

| Step | Agent & Role | Accountable Human | Tool Action on `client-01-website` | Handover / Gate Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **1. Planning** | `dev_architect_agent` (`software_architect`) | `minh` | `read_product_file_tool` (`docs/issue-02-session-04.md`, `site/index.html`, `site/styles.css`) | `ProductHandoverPayload` (`AC-01`–`AC-08`, `N-01`–`N-09`) $\rightarrow$ `backend_api_engineer` |
| **2. Implementation** | `dev_architect_agent` (`backend_api_engineer`) | `mirko` | `write_product_file_tool` (writes full Release Candidate `site/index.html` without fallback) | `QAHandoverPayload` $\rightarrow$ `qa_test_engineer` |
| **3. Product QA** | `qa-test-agent` (`qa_test_engineer`) | `felix` | `run_product_test_tool` (`tests/test_website_s4.py` – all 3 check families passed, `exit_code = 0`) | Routes to `human_gate` (`pending_approval`) $\rightarrow$ approved by `saad` (`R-BASE`) |

---

## 3. Quality Gate Verification & Controlled Fault Evidence (`A3`, `A4`, `D1`, `L4.2`, `L4.3`)

### 3.1 Controlled Fault Run (`WF-WEBSITE01-S4-FAULT-001`)
To verify that the quality gate actively detects product defects and prevents release approval (`A3`, `L4.3`), a single controlled fault was injected in an isolated copy of `client-01-website`:
- **Injected Fault:** Contact email link `N-08_href` set to wrong address `mailto:falsch@nordwerk.example` instead of `mailto:kontakt@nordwerk.example`.
- **Automated Detection:** Product check Family 2 (`test_family2_contact_and_navigation_targets_ac04_ac05` in `tests/test_website_s4.py`) failed with `pytest_exit_code = 1` (`AssertionError: Expected ('mailto:kontakt@nordwerk.example', 'Anfrage stellen')`).
- **Workflow Blocking:** `run_customer_delivery_workflow` recorded `final_qa_result.status = "failed"` and transitioned to `human_gate_status = "escalate_to_human"` (not `pending_approval`).
- **Human Gate Rejection:** Attempting `record_customer_human_review(..., decision="approved")` is technically rejected with `ValueError("Only workflows in 'pending_approval' state can be approved")`. Reviewer `felix` recorded `decision = "changes_requested"` in `runs/website-01/WF-WEBSITE01-S4-FAULT-001/review.json`.
- **Correction & Re-Verification:** Restoring `mailto:kontakt@nordwerk.example` in `WF-WEBSITE01-S4-001` passed all 3 check families (`pytest_exit_code = 0`), reached `human_gate_status = "pending_approval"`, and was approved as `R-BASE`.

### 3.2 Separation of Deterministic Factory Tests vs. Real LLM Runs (`A4`)
- **Deterministic Factory Unit Tests (Mock LLMs):** [`tests/test_session_03_factory.py`](../tests/test_session_03_factory.py) (4 tests) and [`tests/test_session_04_factory.py`](../tests/test_session_04_factory.py) (4 tests) verify workspace sandboxing (`allowed_write_prefixes=["site/"]`), bounded correction loops (`max_correction_loops=2`), positive (`pending_approval` $\rightarrow$ `approved`) and rejected/escalated (`changes_requested`, `escalate_to_human`) gate states, LLM failure non-masking, and clean `factory_commit` enforcement with `mock_runs_are_separate = true`.
- **Real LLM Runs (Local Ollama `qwen3:4b@359d7dd4bcda`):** Stored under `runs/website-01/` with `mock_runs_are_separate = false`.

---

## 4. Release Candidate Checks (`AC-01`–`AC-08`), 3 Check Families & Browser Review (`B1`–`B6`, `D1`)

Full browser inspection logs (`375 px` and `1280 px` widths + sequential keyboard `Tab` focus test) are recorded in `client-01-website/docs/release-candidate-s4.md`.

| Criterion | Required Check | Automated Check Family (`client-01-website/tests/test_website_s4.py`) | Manual Browser / Checkout Verification (`docs/release-candidate-s4.md`) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **AC-01 (`B1`)** | Company name (`N-01`) & main statement (`N-02`) on initial view. | **Family 1:** `test_family1_required_content_ac01_ac02_ac03` | Visually verified in `#start` hero section (`saad`). | **Passed** |
| **AC-02 (`B1`)** | All 3 services (`N-03` *Wartungsplanung*, `N-04` *Ersatzteilkoordination*, `N-05` *Betriebsdokumentation*). | **Family 1:** `test_family1_required_content_ac01_ac02_ac03` | Verified 3 `.service-card` articles under `#leistungen` (`saad`). | **Passed** |
| **AC-03 (`B1`)** | Both target groups (`N-06`) & working approach (`N-07`); no invented claims or `<form>`. | **Family 1:** `test_family1_required_content_ac01_ac02_ac03` | Verified `#zielgruppen` & `#arbeitsweise`; zero unrequested claims (`saad`). | **Passed** |
| **AC-04 (`B2`)** | Contact link `Anfrage stellen` $\rightarrow$ `mailto:kontakt@nordwerk.example` (`N-08`) + course notice (`N-09`). | **Family 2:** `test_family2_contact_and_navigation_targets_ac04_ac05` | Verified top banner and `mailto:` links in hero & `#kontakt` (`saad`). | **Passed** |
| **AC-05 (`B2`, `B6`)** | Navigation to `#leistungen` & `#kontakt`; internal `#anchor` targets & local assets (`styles.css`) resolve. | **Family 2 & 3:** `test_family2_...` + `test_family3_local_assets_and_usability_ac05_ac06_ac07` | Clicked `<nav>` links and verified HTTP `200` for `styles.css` (`felix`). | **Passed** |
| **AC-06 (`B3`)** | No horizontal overflow at `375 px` and `1280 px`; text and CTA usable. | **Family 3:** `test_family3_...` (`viewport` meta + `@media` rules) | DevTools check at `375 px` (`scrollWidth = 375`) and `1280 px` (`scrollWidth = 1280`) (`yaw`, `felix`). | **Passed** |
| **AC-07 (`B4`)** | `<title>`, `lang="de"`, `h1`–`h3` hierarchy, visible keyboard focus (`:focus-visible`), image `alt` attributes. | **Family 3:** `test_family3_local_assets_and_usability_ac05_ac06_ac07` | Tested 7 sequential `Tab` stops (`.skip-link` $\rightarrow$ `<nav>` links $\rightarrow$ `.cta-link`) with `3px solid #1d4ed8` outline (`felix`). | **Passed** |
| **AC-08 (`B5`)** | Fresh checkout of `R-BASE` starts (`python -m http.server 8080 --directory site`) & tests run without Factory/LLM/DB. | `python -m unittest discover -s tests -p "test_*.py" -v` (7/7 passed across `test_website_s3.py` & `test_website_s4.py`) | Verified standalone from fresh checkout as documented in `client-01-website/README.md` (`yaw`). | **Passed** |

---

## 5. Reproducible `R-01` Baseline Experiment & Session 5 Hypothesis (`C1`, `C3`, `C4`, `L4.4`)

### 5.1 Reference Task `R-01` Baseline Execution (Isolated from Customer Release)
- **Frozen Product Baseline (`R-BASE`):** Release Candidate tag `R-BASE` in `client-01-website`
- **Frozen Factory Baseline (`F-BASE`):** `46ed1f9d7c5f6163e5d90117e204809cdc498de9` (`agentic_ai_haw_2627`)
- **Reference Task `R-01` Prompt:**
  > *„Ergänze unter den Leistungen die Karte **‚Projektkoordination‘** mit dem Text **‚Wir koordinieren klar abgegrenzte technische Vorhaben mit Ihrem Team.‘** Alle bisherigen Inhalte, Kontaktziele und Navigation müssen erhalten bleiben.“*
- **Isolation:** Executed on an isolated checkout/branch from `R-BASE` with output artifacts stored in `runs/website-01/R-01-BASELINE-001/` (not merged into customer release `main`).
- **Verification Criterion:** `python -m pytest tests/verify_r01_baseline.py -q` (verifies all 3 check families `AC-01`–`AC-08` pass with zero regressions **plus** presence of the 4th `.service-card` *Projektkoordination*).

| Experiment Run ID / Directory | Factory Commit (`F-BASE`) | Product Input (`R-BASE`) | Model & Settings | AC-01..AC-08 + R-01 Check | Regressions | Human Review / Rework Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`R-01-BASELINE-001`** (`runs/website-01/R-01-BASELINE-001/`) | `46ed1f9` | `R-BASE` | Local Ollama `qwen3:4b@359d7dd4bcda` (`temp=0.0`, `json_mode=True`, `max_loops=2`) | **4/4 passed** (`verify_r01_baseline.py`) | `0` | `0.15 h` review / `0.00 h` rework |

### 5.2 Evidenced Bottleneck & Testable Improvement Hypothesis for Session 5 (`C4`)
- **Evidenced Bottleneck:** During full-page and incremental tasks (`NW-S4-001` and `R-01-BASELINE-001`), `implementation_node` prompts the LLM to re-emit all 14–16 German strings from `required_content` as a complete JSON payload on every run, and semantic omissions (e.g., a missing service description or missing anchor target) are only checked *after* writing to disk and spawning a subprocess `pytest` run in `product_qa_node`. On local `qwen3:4b`, re-generating all unchanged strings accounts for the majority of output tokens and implementation latency.
- **Planned Factory Change for Session 5 (Executed Strictly *After* Saving `F-BASE` / `R-01` Baseline):**
  1. Add a deterministic **in-memory pre-gate content & anchor check** inside `implementation_node` before handing over to `product_qa_node` (immediately catching any missing verbatim string from `required_content` before human review).
  2. Support **delta-key merging** for incremental change tasks like `R-01` / `CR-01` so the LLM only needs to generate new/modified section keys while preserving verified baseline sections from `R-BASE`.
- **Expected Effect & Measurable Criterion in Session 5 (Re-running `R-01` on `R-BASE`):**
  - Reduce `R-01` implementation step output tokens by **$\ge 35\%$** and total `R-01` workflow runtime by **$\ge 30\%$** while maintaining **$100\%$ check pass rate (`4/4` in `verify_r01_baseline.py`, `0` regressions)** and **`0` human rework minutes**.

---

## 6. Effort, Costs & S3/S4 Plan Budget Comparison (`C2`)

Full cost records are tracked in [`costs/usage.csv`](../costs/usage.csv) and [`costs/cost-model.yaml`](../costs/cost-model.yaml) (rates: Human `100` credits/h; Agent `1.0` base + `0.01`/s + `0.02`/1k input tokens + `0.04`/1k output tokens; CI `1.0` credit/run).

| Category | Session 3 Actual | Session 4 Actual | S3 + S4 Cumulative | S3/S4 Plan Budget (`costs/cost-model.yaml`) | Status / Deviation Explanation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Human – Customer Delivery** | `1.00 h` (`100.00`) | `1.50 h` (`150.00`) (`yaw`, `saad`, `felix`) | `2.50 h` (`250.00`) | `3.50 h` (`350.00`) | `-1.00 h` (`-100.0` credits under plan): reusing S3 scaffold & CSS layout accelerated S4 delivery. |
| **Human – Review (Browser & Gate)** | `0.50 h` (`50.00`) | `0.75 h` (`75.00`) (`saad`, `felix`, `yaw`) | `1.25 h` (`125.00`) | `1.50 h` (`150.00`) | `-0.25 h` (`-25.0` credits under plan): structured 3-family test suite sped up review. |
| **Human – Rework (Fault & Fixes)** | `0.25 h` (`25.00`) | `0.25 h` (`25.00`) (`muhammad`, `mirko`) | `0.50 h` (`50.00`) | `1.00 h` (`100.00`) | `-0.50 h` (`-50.0` credits under plan): only 1 controlled fault run required reset/re-run. |
| **Agent Runs (Delivery + Fault + `R-01`)** | `6 calls` (`8.2900`) | Recorded in `costs/usage.csv` (`WF-WEBSITE01-S4-001`, `FAULT-001`, `R-01`) | Within `25.0` credit budget | `25.0000` | Includes both approved runs, controlled fault run, and `R-01` baseline. |
| **CI Runs** | `1 run` (`1.0000`) | `2 runs` (`2.0000`) | `3 runs` (`3.0000`) | `6.0000` | `-3.0` credits under plan. |
| **Customer Delivery Subtotal (S3+S4)** | **`184.2900`** | **~`265`–`270`** | **~`450`–`455`** | **`631.0000`** | **~28% under the `631.0` credits S3/S4 delivery budget; `315.0` credits S5 reserve untouched.** |
| **Human – Factory Development (Separate)** | `2.00 h` (`200.00`) | `1.25 h` (`125.00`) (`muhammad`, `minh`, `mirko`) | `3.25 h` (`325.00`) | `4.00 h` (`400.00` S3–S5) | `0.75 h` (`75.0` credits) Factory dev budget remaining for S5 optimization. |

---

## 7. Next Actions for Session 5 (Max 3 Steps) (`D2`)

1. **Execute Session 5 Factory Optimization & Re-Run `R-01` on `R-BASE`:** Implement the pre-gate deterministic validator and delta-key prompting in `customer_delivery_workflow.py`, re-run `R-01` from `R-BASE`, and compare runtime, token usage, and pass rate against `R-01-BASELINE-001`.
2. **Deliver Customer Change Request `CR-01` (`AC-09`):** Process the Session 5 customer change request through the improved Factory while verifying zero regressions on `AC-01`–`AC-08`.
3. **Complete Component Inventory, Security Advisory `SR-01` & Final Acceptance (`AC-10`):** Deliver the component overview, scoped security response `SR-01`, final customer acceptance protocol, and `evidence/session-05.md`.
