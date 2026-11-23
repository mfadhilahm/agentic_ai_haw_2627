# Session 7 Evidence – Complete `HP-V1` Quotation Calculator, Business & Validation Suite (`Q01`–`Q14`, `E01`–`E10`), Controlled Discount Fault Gate, and `R-02` Baseline (`quotation-02`)

- **Company / Factory Repository:** `HAW Agentic Software Factory` ([`agentic_ai_haw_2627`](https://github.com/mfadhilahm/agentic_ai_haw_2627))
- **Customer Project 02 Product Repository:** `HansePack Handelsgesellschaft` (`../client-02-quotation`, GitHub: [`client-02-quotation`](https://github.com/minhnyn/client-02-quotation))
- **Frozen Previous Customer Repository:** `Nordwerk Industrie-Service` (`../client-01-website`, GitHub: [`client-01-website`](https://github.com/mfadhilahm/client-01-website), frozen at Session 5 final release [`84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f`](https://github.com/mfadhilahm/client-01-website/commit/84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f) / `v1.0.0-s5-rc` including English `site/en.html`)
- **Project ID / Session 7 Task IDs:** `quotation-02` / `HP-S7-001` (Release Candidate `Q-BASE`), `HP-S7-FAULT-001` (Controlled Discount Boundary Fault `> 50`), `R-02` (Isolated Baseline Experiment)
- **Live GitHub Issues Tracking Session 7 (`HP-S7-001`):**
  - Customer Product Repository Issue #2: [`minhnyn/client-02-quotation#2`](https://github.com/minhnyn/client-02-quotation/issues/2)
  - Software Factory Repository Issue #5: [`mfadhilahm/agentic_ai_haw_2627#5`](https://github.com/mfadhilahm/agentic_ai_haw_2627/issues/5)
  - Versioned Issue Specification: [`../client-02-quotation/docs/issue-02-session-07.md`](../../client-02-quotation/docs/issue-02-session-07.md)
  - Human UI, JSON Export & Fresh-Checkout Review Protocol: [`../client-02-quotation/docs/ui-export-review-s7.md`](../../client-02-quotation/docs/ui-export-review-s7.md)
- **Session:** Termin 7 (`2026-11-23`)
- **Team Members (Accountable Humans, Team Size = 6):**
  - `yaw` – Commission Lead, Cost Accounting & `R-02` Experiment / T8 Hypothesis Lead
  - `saad` – Requirements Owner, GitHub Issue #2 & Technical Release Gate Reviewer (`Q-BASE`)
  - `felix` – QA Lead, Full `Q01`–`Q14` / `E01`–`E10` Suite & Controlled Fault Gate Reviewer
  - `minh` – Software Architect (`dev_architect_agent` – `software_architect`) & `quotation-02.yaml` Contract Owner
  - `mirko` – Technical Delivery Lead (`dev_architect_agent` – `backend_api_engineer`), Web UI & JSON Export (`app.py`)
  - `muhammad` – Agent & Integration Engineer, Pre-QA Short-Circuit, Fault & `R-02` Baseline Runner

---

## Executive Summary & Version Matrix (`A1`, `B6`, `C1`, `D1`, `D2`)

| Reference Role | Repository | Commit SHA / Tag | Verification & Gate Status |
|---|---|---|---|
| **Frozen Nordwerk Product Baseline (`S5 Final Release`)** | `client-01-website` | [`84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f`](https://github.com/mfadhilahm/client-01-website/commit/84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f) (`R-S5-FINAL` / `v1.0.0-s5-rc`) | Clean working tree (`git status --porcelain` empty); includes German `site/index.html` (`6ebd91ed...`) and English website `site/en.html` (`8b43eaa3...`); `10/10` S3–S5 tests pass (`0.004s`). |
| **`F-BASE` (Session 7 Factory Baseline)** | `agentic_ai_haw_2627` | `0d84224c1b8bfc46380f25a4a401fa9a48318fb2` (`F-BASE`, `factory_commit_clean: true`, `workflow_code_sha256: 99200793...`) | Remediated S6 feedback (generic Python contract validator, externalized template `quotation_02_calculator.py.tpl`, pre-QA short-circuit) + S7 task support (`HP-S7-001`, `HP-S7-FAULT-001`, `R-02`). |
| **Session 7 Product Input Commit (`before WF-QUOTATION02-S7-001`)** | `client-02-quotation` | `0f880ead8de98dde615f5a166abbe6dbd793e765` | Input state containing FastAPI Web UI + JSON export endpoint (`app.py`), full `Q01`–`Q14` / `E01`–`E10` test suite (`tests/test_quotation_s7.py`), and `R-02` verification suite (`tests/verify_r02_baseline.py`). |
| **`Q-BASE` (Session 7 HansePack `HP-V1` Release Candidate)** | `client-02-quotation` | `d86b3c3853568297a16a7fb4c9f82cc3535e3d07` (`Q-BASE`, `HP-AC01`–`HP-AC07`) | Delivered `quotation/calculator.py` (`SHA-256: 6000415817249f8b286e7fa22fa377db7b3317fe13711b8466376da998d58ce0`); passes all `14/14` valid (`Q01`–`Q14`) and `10/10` invalid (`E01`–`E10`) customer reference cases + JSON export consistency + human Web UI review (`Q12`, `E01`, `E03`). Approved at technical gate by `saad`. |
| **Controlled Fault Run (`WF-QUOTATION02-S7-FAULT-001`)** | Isolated Checkout of `Q-BASE` | `uncommitted_worktree (rejected_not_committed)` | 5% discount boundary changed to `quantity > 50` (`discount_tier_50_min_qty=51`, `SHA-256: 82024d0f...`). Fails `Q03` (`13700 != 13075` cents, `pytest_exit_code = 1`); blocked by Factory gate (`escalate_to_human`, `decision: "changes_requested"` by `felix`). Never merged into `main`. |
| **Isolated `R-02` Baseline (`R-02-BASELINE-001`)** | Isolated Copy of `Q-BASE` | `uncommitted_worktree (isolated_experiment)` | Executed on a clean isolated copy of `Q-BASE` (`d86b3c3`) with `F-BASE` (`0d84224`); adds `"calculation_note": "Net amounts; shipping shown separately."` (`SHA-256: c549d980...`) with 0 regressions (`13/13` tests, `116` subtests in `verify_r02_baseline.py`). Not merged into `main`. |
| **Customer Acceptance Status** | `client-02-quotation` | **`pending_customer_acceptance`** | Strictly distinguished from internal technical release candidate approval (`approved` on `Q-BASE`); awaits live instructor acceptance. |

---

## 1. Remediation of Session 6 Feedback (`Feedback_Session_06_Team_1.md`)

All three improvement points from the Session 6 feedback were implemented and verified by automated regression tests in [`tests/test_session_06_factory.py`](../tests/test_session_06_factory.py) (`18/18 passed` across S3–S6):
1. **Actual Session 5 Nordwerk Release (`84d5baf` Including English Website `site/en.html`) Frozen & Tested:**
   - Replaced the outdated Session 4 commit reference (`53885e0`) with the actual Session 5 final release commit [`84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f`](https://github.com/mfadhilahm/client-01-website/commit/84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f) (`R-S5-FINAL` / `v1.0.0-s5-rc`), including both `site/index.html` (`6ebd91ed...`) and the English entry page `site/en.html` (`8b43eaa3...`).
   - Extended `test_project_isolation_hansepack_run_never_modifies_nordwerk_files` in [`tests/test_session_06_factory.py`](../tests/test_session_06_factory.py) to verify SHA-256 invariance and passing `tests/test_website_s5.py` checks across both German and English pages after running `quotation-02`.
2. **Complete CI Run Accounting (`2026-11-16`), Individual Person-Hours (`Personenstunden`) & Real GitHub Issues:**
   - Recorded all **3 GitHub Actions CI runs** on `2026-11-16` (`3.0` credits for commits `5270442`, `f8d778b`, `e86ad33`) in [`costs/usage.csv`](../costs/usage.csv) and [`costs/cost-model.yaml`](../costs/cost-model.yaml).
   - Itemized all human effort into individual per-member rows (`yaw`, `saad`, `felix`, `minh`, `mirko`, `muhammad`) with exclusive category labels (`Factory Switch & Adaptation`, `Customer Delivery`, `Human Review`, `Rework`) in [`costs/usage.csv`](../costs/usage.csv).
   - Created real GitHub Issues for both Session 6 ([`client-02-quotation#1`](https://github.com/minhnyn/client-02-quotation/issues/1), [`agentic_ai_haw_2627#4`](https://github.com/mfadhilahm/agentic_ai_haw_2627/issues/4)) and Session 7 ([`client-02-quotation#2`](https://github.com/minhnyn/client-02-quotation/issues/2), [`agentic_ai_haw_2627#5`](https://github.com/mfadhilahm/agentic_ai_haw_2627/issues/5)).
3. **Generic Python Contract Validation, Externalized Project Template & Pre-QA Short-Circuit:**
   - Externalized the HansePack Python template to [`config/projects/templates/quotation_02_calculator.py.tpl`](../config/projects/templates/quotation_02_calculator.py.tpl) and declared its contract in [`config/projects/quotation-02.yaml`](../config/projects/quotation-02.yaml) (`python_module_contract`), keeping [`src/agents/customer_delivery_workflow.py`](../src/agents/customer_delivery_workflow.py) generic (`validate_and_normalize_python_contract_fields`, `render_python_module_from_contract`, `validate_python_module_pre_gate`).
   - Added a **Pre-QA Short-Circuit** at the start of `product_qa_node`: failed implementation steps (`status != "completed"` or `not ready_for_qa` or `written_file is None`) are intercepted immediately with `0` QA LLM calls and `0.0` QA credits (`tool_status="not_started"`), routing validation errors straight back into the bounded retry loop.

---

## 2. Repeat Factory Delivery (`WF-QUOTATION02-S7-001`), Full Business Tests (`Q01`–`Q14`, `E01`–`E10`) & Human UI/Export Review (`A1`, `A2`, `B1`–`B6`, `D1`, `L7.1`)

### 2.1 Subsequent Real Multi-Agent Run (`WF-QUOTATION02-S7-001` $\rightarrow$ Release Candidate `Q-BASE`)
- **Task (`HP-S7-001`):** Complete `HP-V1` quotation calculation and JSON export (`export_quotation_dict` / `calculate_quotation`) in `quotation/calculator.py`, verified against all 14 valid (`Q01`–`Q14`) and 10 invalid (`E01`–`E10`) customer reference cases in `tests/test_quotation_s7.py`.
- **Commit Lineage:**
  - `factory_commit` (`F-BASE`): `0d84224c1b8bfc46380f25a4a401fa9a48318fb2` (`factory_commit_clean: true`, `workflow_code_sha256: 992007935cb401e3e398c10c1ee6f3bb51211cc553aef671ae801705101e5276`)
  - `product_input_commit`: `0f880ead8de98dde615f5a166abbe6dbd793e765`
  - `subsequent_product_commit` / `tested_source_commit` (`Q-BASE`): `d86b3c3853568297a16a7fb4c9f82cc3535e3d07` (`quotation/calculator.py` SHA-256: `6000415817249f8b286e7fa22fa377db7b3317fe13711b8466376da998d58ce0`)
- **Step-by-Step Multi-Agent Handover & Trace Metrics (`WF-QUOTATION02-S7-001`):**

| Step | Run ID | Agent (`Role`) | Accountable Human | Tool Invoked | Handover / Output | Duration (s) | In / Out Tokens | Credits |
|---:|---|---|---|---|---|---:|---:|---:|
| **1** | `4df4306c-26a9-4dc2-9b10-9f968416bd73` | `dev_architect_agent` (`software_architect`) | `minh` | `read_product_file_tool` | `ArchitectToImplementationHandover` (`to_role: backend_api_engineer`, 14 `HP-V1` contract fields) | `70.8877` | `819` / `164` | `1.7318` |
| **2** | `fcbcf744-4a21-4711-bc75-598eaad3fcaa` | `dev_architect_agent` (`backend_api_engineer`) | `mirko` | `write_product_file_tool` | `ImplementationToQAHandover` (`to_role: qa_test_engineer`, `quotation/calculator.py` `60004158...`, `pre_gate_validation_passed: true`) | `16.7828` | `474` / `339` | `1.1909` |
| **3** | `9acabd76-bf65-4252-94b1-be86521de1fb` | `qa-test-agent` (`qa_test_engineer`) | `felix` | `run_product_test_tool` | `QATestResult` (`tests/test_quotation_s7.py`, `pytest_exit_code: 0`, `status: "passed"`) | `8.5293` | `405` / `92` | `1.0971` |
| **Total** | **3 LLM calls (`iterations_used: 1`)** | **Ollama `qwen3:4b@359d7dd4bcda`** | **`saad` (Gate Reviewer)** | **3 distinct tools** | **`human_gate_status: "pending_approval"` $\rightarrow$ `decision: "approved"` (`Q-BASE` `d86b3c3`)** | **`96.1998`** | **`1698` / `595`** | **`4.0198`** |

- **Run Artifacts:**
  - Manifest: [`runs/quotation-02/WF-QUOTATION02-S7-001/manifest.json`](../runs/quotation-02/WF-QUOTATION02-S7-001/manifest.json)
  - Workflow Report: [`runs/quotation-02/WF-QUOTATION02-S7-001/workflow-report.json`](../runs/quotation-02/WF-QUOTATION02-S7-001/workflow-report.json)
  - Trace Log: [`runs/quotation-02/WF-QUOTATION02-S7-001/trace.jsonl`](../runs/quotation-02/WF-QUOTATION02-S7-001/trace.jsonl)
  - Product Diff Patch: [`runs/quotation-02/WF-QUOTATION02-S7-001/changes.patch`](../runs/quotation-02/WF-QUOTATION02-S7-001/changes.patch)
  - Human Gate Review Record: [`runs/quotation-02/WF-QUOTATION02-S7-001/review.json`](../runs/quotation-02/WF-QUOTATION02-S7-001/review.json) (`decision: "approved"` by `saad`)

### 2.2 Complete Business & Validation Test Matrix (`B1`–`B3`, `HP-AC03`, `HP-AC04`)

All tests in `../client-02-quotation/tests/test_quotation_s7.py` load the unchanged customer fixture [`data/HansePack_Referenzfaelle.json`](../../client-02-quotation/data/HansePack_Referenzfaelle.json) (`SHA-256: 7deb994e...`) directly:

| Test Family | Cases Covered | Key Business & Boundary Rules Verified | Result |
|---|---|---|---|
| **Fixture Provenance (`B6`)** | `HansePack_Katalog.json`, `HansePack_Referenzfaelle.json` | Exact SHA-256 verification against official customer files (`70f0e1a7...`, `7deb994e...`). | **Passed** |
| **Discounts & Commercial Rounding (`B1`, `HP-AC03`)** | **`Q01`–`Q14`** (all 14 valid cases, line-level checks) | All 3 SKUs (`HP-BOX`, `HP-TAPE`, `HP-FILM`); tier boundaries `49` (`0%`, `Q02`), `50` (`5%`, `Q03`), `99` (`5%`, `Q04`), `100` (`10%`, `Q05`, `Q09`); `Decimal` `ROUND_HALF_UP` half-cent cases: `Q04` (`1237.5 -> 1238` ct), `Q13` (`3187.5 -> 3188` ct), `Q14` (`662.5 -> 663` ct, distinguishing `ROUND_HALF_UP` from `ROUND_HALF_EVEN`). | **Passed (`14/14`)** |
| **Shipping & Totals under `HP-V1` (`B2`, `HP-AC03`)** | **`Q01`–`Q14`** (all 14 valid cases, summary totals) | `goods_net_cents`, `shipping_cents`, `total_cents` under `HP-V1` (`1200` ct below `50000` ct goods net, `0` ct from `50000` ct): `Q06` (`HP-BOX × 200`: list `50000` ct, after 10% discount `45000 < 50000` $\rightarrow$ `1200` ct shipping, total `46200` ct); `Q07` (`HP-FILM × 40`: `goods_net = 50000` at threshold $\rightarrow$ `0` ct shipping, total `50000` ct); `Q08` (`48750` $\rightarrow$ `1200` ct shipping); multi-line `Q12` (`15875` + `1200` = `17075` ct). | **Passed (`14/14`)** |
| **Input Validation in Python (`B3`, `HP-AC04`)** | **`E01`–`E10`** (all 10 invalid cases + `bool` check) | `E01` (`qty=0`), `E02` (`qty=-5`), `E03` (duplicate SKU `HP-BOX`), `E04` (unknown SKU `HP-PALLET`), `E05` (empty list `[]`), `E06` (`qty=10001 > 10000`), `E07` (`qty=1.5` float), `E08` (`qty="50"` string), `E09` (`qty=None` missing), `E10` (`4` lines `> 3`), plus `bool` (`True`/`False`). All raise `QuotationValidationError` with zero silent type coercion or SKU aggregation. | **Passed (`10/10`)** |
| **Web UI & JSON Export Consistency (`B4`, `B5`, `HP-AC05`, `HP-AC06`)** | `POST /api/quotation`, `POST /api/quotation/export`, `export_quotation_dict` | Required integer-cent fields, `currency: "EUR"`, `rule_version: "HP-V1"`, and `course_notice` present; exported JSON matches displayed calculation 100%; invalid inputs reach Python via `POST /api/quotation` and return HTTP `400`. | **Passed** |

### 2.3 Human Web UI, JSON Export & Fresh-Checkout Review (`B4`–`B6`, `D1`)
Documented in full in [`../client-02-quotation/docs/ui-export-review-s7.md`](../../client-02-quotation/docs/ui-export-review-s7.md):
- **Multi-Line UI & Export Check (`Q12`, reviewed by `saad` & `felix`):** Entered `HP-BOX × 50` and `HP-TAPE × 10` in the browser UI (`http://127.0.0.1:8000/`), verified visible notice `"Net amounts – course project, not a binding quotation"`, verified displayed values (`goods_net_cents = 15875`, `shipping_cents = 1200`, `total_cents = 17075`), downloaded `hansepack-quotation.json`, and confirmed 100% field-by-field parity.
- **Invalid Input UI Check (`E01`, `E03`, reviewed by `felix` & `mirko`):** Entered quantity `0` (`E01`) and duplicate SKU `HP-BOX` (`E03`) in the web form; confirmed the request reaches Python `calculate_quotation()`, raises `QuotationValidationError`, displays a clear error banner in the UI, and produces no valid quotation.
- **Fresh Checkout Verification (`B6`):** Started `python app.py`, `python main.py`, and `python -m pytest tests/test_quotation_s7.py -q` from a clean checkout without the Factory or any LLM.

---

## 3. Controlled Business Fault Injection (`> 50` vs. `>= 50`) & Quality Gate Blocking (`A3`, `A4`, `L7.2`, `L7.3`)

### 3.1 Injected Fault & Expected Failure on `Q03`
- **Fault Specification (`HP-S7-FAULT-001`):** In an isolated checkout/branch of `Q-BASE`, exactly one condition in `_discount_percent_for_quantity` was modified so that the 5% discount starts **above 50 (`quantity > 50`, i.e., from `51`) instead of from 50 (`quantity >= 50`)**.
- **Unchanged Customer Expectations:** `data/HansePack_Referenzfaelle.json` and `tests/test_quotation_s7.py` remained completely unchanged.
- **Concrete Failure on `Q03` (`HP-BOX × 50`):**
  - Under the injected fault (`quantity > 50`), `HP-BOX × 50` receives `0%` discount (`0` cents) instead of `5%` (`625` cents):
    - Faulty output: `list_amount_cents = 12500`, `discount_cents = 0`, `goods_net_cents = 12500`, `shipping_cents = 1200`, **`total_cents = 13700`**
    - Customer reference (`Q03`): `list_amount_cents = 12500`, `discount_cents = 625`, `goods_net_cents = 11875`, `shipping_cents = 1200`, **`total_cents = 13075`**

### 3.2 Workflow Gate Consequence, Rejection & Correction (`WF-QUOTATION02-S7-FAULT-001`)
- **Artifacts:** [`manifest.json`](../runs/quotation-02/WF-QUOTATION02-S7-FAULT-001/manifest.json), [`workflow-report.json`](../runs/quotation-02/WF-QUOTATION02-S7-FAULT-001/workflow-report.json), [`trace.jsonl`](../runs/quotation-02/WF-QUOTATION02-S7-FAULT-001/trace.jsonl), [`changes.patch`](../runs/quotation-02/WF-QUOTATION02-S7-FAULT-001/changes.patch), [`calculator-faulty.py`](../runs/quotation-02/WF-QUOTATION02-S7-FAULT-001/calculator-faulty.py) (`SHA-256: 82024d0f0f3f959620c4f8f2fff76ceca20b892ced0daea4453159bb52491a2b`), [`review.json`](../runs/quotation-02/WF-QUOTATION02-S7-FAULT-001/review.json)
- **Step-by-Step Trace Metrics (`WF-QUOTATION02-S7-FAULT-001`, executed from `Q-BASE` `d86b3c3` on `F-BASE` `0d84224`):**

| Step | Run ID | Agent (`Role`) | Tool Invoked | Outcome | Duration (s) | In / Out Tokens | Credits |
|---:|---|---|---|---|---:|---:|---:|
| **1** | `90407ff7-0512-40bd-afc4-1a99f2cf08d7` | `dev_architect_agent` (`software_architect`) | `read_product_file_tool` | Handover with `discount_tier_50_min_qty: "51"` (`> 50`) | `8.2171` | `838` / `106` | `1.1032` |
| **2** | `581a718b-d6b7-4167-bf4b-031581a59a3d` | `dev_architect_agent` (`backend_api_engineer`) | `write_product_file_tool` | Wrote faulty `quotation/calculator.py` (`82024d0f...`) | `16.8673` | `476` / `341` | `1.1918` |
| **3** | `d8ae4188-b5a9-462d-a01f-9b76bb3476ff` | `qa-test-agent` (`qa_test_engineer`) | `run_product_test_tool` | **`status: "failed"`, `pytest_exit_code: 1` (`Q03` failed: `13700 != 13075`)** | `14.2488` | `2001` / `171` | `1.1893` |
| **Total** | **3 LLM calls (`max_correction_loops: 1`)** | **Ollama `qwen3:4b@359d7dd4bcda`** | **3 distinct tools** | **`human_gate_status: "escalate_to_human"` $\rightarrow$ `decision: "changes_requested"` (`felix`)** | **`39.3332`** | **`3315` / `618`** | **`3.4843`** |

- **Automated Gate Blocking:** `product_qa_node` executed `run_product_test_tool` on `tests/test_quotation_s7.py`, which failed on `Q03` (`AssertionError: 13700 != 13075`, `pytest_exit_code = 1`). The workflow set `final_qa_result.status = "failed"`, `product_test_passed = false`, and transitioned to **`human_gate_status = "escalate_to_human"`** (technically blocking `record_customer_human_review(..., decision="approved")` with `ValueError("Only workflows in 'pending_approval' state can be approved")`).
- **Human Gate Rejection & Correction (`D1`):** Reviewer `felix` recorded `decision = "changes_requested"` in [`runs/quotation-02/WF-QUOTATION02-S7-FAULT-001/review.json`](../runs/quotation-02/WF-QUOTATION02-S7-FAULT-001/review.json). Restoring `quantity >= 50` in `Q-BASE` (`WF-QUOTATION02-S7-001`, commit `d86b3c3853568297a16a7fb4c9f82cc3535e3d07`) passed `Q03` (`13075` cents) and all `Q01`–`Q14` / `E01`–`E10` checks (`pytest_exit_code = 0`) and was approved by `saad`. The isolated fault state was never merged into `client-02-quotation` `main`.
- **Automated Factory Gate Unit Tests (`A4`):** `tests/test_session_07_factory.py` deterministically verifies both the passed gate state (`pending_approval` $\rightarrow$ `approved`) and the blocked discount-boundary fault state (`13700 != 13075` $\rightarrow$ `escalate_to_human` $\rightarrow$ `changes_requested`) while preserving project isolation and bounded loop limits.

---

## 4. Reproducible `R-02` Baseline Experiment & Targeted Session 8 Hypothesis (`C1`, `C3`, `C4`, `L7.4`)

### 4.1 Reproducible `R-02` Baseline Setup & Execution (`R-02-BASELINE-001`)
- **Reference Task `R-02` Specification:**
  > *„Ergänze im exportierten Angebots-JSON das Feld `calculation_note` mit dem festen Text `Net amounts; shipping shown separately.`. Anzeige, Geldwerte und Fehlerbehandlung bleiben unverändert. Ergänze einen Test für das Feld; alle bisherigen Fachtests müssen weiter bestehen.“*
- **Strict Isolation from Customer Candidate:** Executed on a clean, isolated copy of **`Q-BASE` (`d86b3c3853568297a16a7fb4c9f82cc3535e3d07`)** using **`F-BASE` (`0d84224c1b8bfc46380f25a4a401fa9a48318fb2`)** (`Ollama qwen3:4b@359d7dd4bcda`, `temperature = 0.0`, `reasoning = False`, `json_mode = True`, `max_correction_loops = 2`). Output artifacts are preserved in [`runs/quotation-02/R-02-BASELINE-001/`](../runs/quotation-02/R-02-BASELINE-001/) ([`manifest.json`](../runs/quotation-02/R-02-BASELINE-001/manifest.json), [`workflow-report.json`](../runs/quotation-02/R-02-BASELINE-001/workflow-report.json), [`trace.jsonl`](../runs/quotation-02/R-02-BASELINE-001/trace.jsonl), [`changes.patch`](../runs/quotation-02/R-02-BASELINE-001/changes.patch), [`calculator-r02.py`](../runs/quotation-02/R-02-BASELINE-001/calculator-r02.py), [`review.json`](../runs/quotation-02/R-02-BASELINE-001/review.json)) and **not** merged into `client-02-quotation` `main`.
- **Complete `R-02` Baseline Protocol & Measurement Table (`C1`, `C3`):**

| Baseline Dimension | Recorded `R-02-BASELINE-001` Measurement (`F-BASE` on `Q-BASE`) |
|---|---|
| **Workflow ID & Run IDs** | `R-02-BASELINE-001` (`359c865f-a753-4677-80f4-b8e183e2a862`, `d6065dcc-6bd5-4105-ba21-73613b9f4ce3`, `93c69056-4e77-4672-9884-afa7f8250add`) |
| **Product Input State (`Q-BASE`)** | Commit `d86b3c3853568297a16a7fb4c9f82cc3535e3d07` (`tag: Q-BASE`; input `quotation/calculator.py` SHA-256: `6000415817249f8b286e7fa22fa377db7b3317fe13711b8466376da998d58ce0`) |
| **Factory Baseline (`F-BASE`)** | Commit `0d84224c1b8bfc46380f25a4a401fa9a48318fb2` (`tag: F-BASE`, `factory_commit_clean: true`, `workflow_code_sha256: 992007935cb401e3e398c10c1ee6f3bb51211cc553aef671ae801705101e5276`) |
| **Provider / Model / Digest / Settings** | `ollama` / `qwen3:4b` / `qwen3:4b@359d7dd4bcda` / `temperature: 0.0`, `reasoning: false`, `json_mode: true`, `min_output_tokens: 1024`, `max_correction_loops: 2` |
| **Output Artifact & Diff** | Isolated `quotation/calculator.py` (`SHA-256: c549d980717c2a6b2e1f5c121c31acdd2b60fcc5deb5c702486397f2ac4bf2cd`, archived in [`calculator-r02.py`](../runs/quotation-02/R-02-BASELINE-001/calculator-r02.py) and [`changes.patch`](../runs/quotation-02/R-02-BASELINE-001/changes.patch): sets `CALCULATION_NOTE = "Net amounts; shipping shown separately."`) |
| **Automated Checks Executed** | `python -m pytest tests/verify_r02_baseline.py -q` (`13/13` tests, `116` subtests passed, `pytest_exit_code: 0`): verifies `"calculation_note": "Net amounts; shipping shown separately."` in exported JSON, unchanged display/monetary values across `Q01`–`Q14`, and unchanged error handling across `E01`–`E10`. |
| **Step 1 (`software_architect`)** | `duration: 6.2880s`, `input_tokens: 842`, `output_tokens: 58`, `credits: 1.0820` (`delta_keys: []` — full 15-field contract handover) |
| **Step 2 (`backend_api_engineer`)** | `duration: 17.4741s`, `input_tokens: 491`, `output_tokens: 356`, `credits: 1.1988` (`delta_mode: false` — LLM re-emitted all 15 contract fields + summary) |
| **Step 3 (`qa_test_engineer`)** | `duration: 7.6496s`, `input_tokens: 401`, `output_tokens: 65`, `credits: 1.0871` (`status: "passed"`, `pytest_exit_code: 0`) |
| **Total Run Duration / Tokens / Credits** | **`31.4117s` total (`17.4741s` in implementation)** / **`1734` input tokens, `479` output tokens (`356` in implementation)** / **`3.3679` agent credits** (`iterations_used: 1`) |
| **Human Review & Correction Effort** | `0.15` person-hours (`9 min` = `15.0` credits by `yaw` for review & diff inspection; `0` manual code edits required) |

### 4.2 Targeted Factory Optimization Hypothesis for Session 8 (`C4`)
- **Evidenced Bottleneck in `F-BASE` on `R-02`:**
  In `F-BASE`, `architect_node` only extracts a verified baseline for HTML targets (`extract_verified_baseline_from_product_html`, line 1707: `if t.target_product_file.endswith(".py"): verified_baseline = {}`). Consequently, even when `quotation/calculator.py` in `Q-BASE` already contains all 12 verified `HP-V1` business rule constants (`RULE_VERSION` through `COURSE_NOTICE`) and `R-02` only adds a single new field (`calculation_note: "Net amounts; shipping shown separately."`), `F-BASE` forces `qwen3:4b` in `implementation_node` to re-emit all 13 rule keys (`12` baseline rules + `calculation_note` + `summary`) in one flat JSON payload. This increases prompt/output token volume, implementation latency, and the probability of omitting an unchanged baseline key on Iteration 1.
- **Planned Small Factory Intervention for Session 8 (`F-NEW-S8`, Executed Strictly *After* Freezing `F-BASE` & `R-02-BASELINE-001`):**
  1. Add **AST-based Python baseline rule extraction & delta-key merging (`extract_verified_baseline_from_python_module`)** in `src/agents/customer_delivery_workflow.py`: inspect the existing `quotation/calculator.py` AST constants against `DEFAULT_PYTHON_MODULE_CONTRACT["rule_constant_map"]`, populate `handover.baseline_content` and `handover.delta_keys`, and prompt `implementation_node` **only** for the changed/added delta keys (e.g. `calculation_note` for `R-02`, or `rule_version`, `free_shipping_threshold_cents`, `shipping_fee_cents` for `CR-02` / `HP-V2`) plus `"summary"`.
  2. Add a **deterministic pre-gate JSON export contract check** inside `validate_python_module_pre_gate` verifying that required export keys (including `calculation_note` for `R-02`) are present in the AST before running external `pytest`.
- **Expected Measurable Effect in Session 8 (Re-running `R-02` on `Q-BASE` with `F-NEW-S8`):**
  - Reduce `R-02` `implementation_node` output tokens by **$\ge 50\%$** and reduce `implementation_node` latency and agent credits while maintaining **$100\%$ pass rate on all `Q01`–`Q14`, `E01`–`E10`, and `calculation_note` checks (`0` regressions)**.

---

## 5. Session 7 Daily Costs, Person-Hours Breakdown & Budget Variance (`C2`)

All costs are recorded in [`costs/usage.csv`](../costs/usage.csv) (RFC-4180 8-column CSV) and [`costs/cost-model.yaml`](../costs/cost-model.yaml) at official course rates (`100` credits/Personenstunde human; `1.0 + 0.01/s + 0.02/1k in + 0.04/1k out` agent; `1.0` credit/CI run).

### 5.1 Exclusive Per-Member Person-Hours (`Personenstunden`) Matrix for Session 7 (`2026-11-23`)

| Team Member | Customer Delivery (`HP-S7-001`) | Human Review (`HP-S7-001` / Fault / `R-02`) | Rework (`HP-S7-001`) | Separate Factory Dev (`SESSION-07-FACTORY-DEV`) | Member Total (`Personenstunden`) | Member Credits (`100 / h`) | Concrete Tasks Performed |
|---|---:|---:|---:|---:|---:|---:|---|
| **`yaw`** | `0.25 h` *(15 min)* | `0.15 h` *(9 min)* | `0.00 h` | `0.00 h` | **`0.40 h`** *(24 min)* | **`40.0000`** | S7 cost/budget accounting & `evidence/session-07.md` (`0.25 h`); `R-02` baseline metrics & T8 hypothesis review (`0.15 h`). |
| **`saad`** | `0.25 h` *(15 min)* | `0.25 h` *(15 min)* | `0.00 h` | `0.00 h` | **`0.50 h`** *(30 min)* | **`50.0000`** | GitHub Issue #2 (`issues/2`, `issues/5`) & `docs/issue-02-session-07.md` (`0.25 h`); human UI/export review (`Q12`, `E01`) & `Q-BASE` gate approval (`0.25 h`). |
| **`felix`** | `0.50 h` *(30 min)* | `0.20 h` *(12 min)* | `0.00 h` | `0.00 h` | **`0.70 h`** *(42 min)* | **`70.0000`** | Full `tests/test_quotation_s7.py` suite (`Q01`–`Q14`, `E01`–`E10`, export parity) (`0.50 h`); controlled fault verification (`Q03` `13700 != 13075`) & gate rejection (`0.20 h`). |
| **`minh`** | `0.00 h` | `0.15 h` *(9 min)* | `0.00 h` | `0.25 h` *(15 min)* | **`0.40 h`** *(24 min)* | **`40.0000`** | `quotation-02.yaml` & template updates for `HP-S7-001`, `HP-S7-FAULT-001`, `R-02` (`0.25 h`); fresh-checkout & architecture handover review (`0.15 h`). |
| **`mirko`** | `0.50 h` *(30 min)* | `0.00 h` | `0.10 h` *(6 min)* | `0.00 h` | **`0.60 h`** *(36 min)* | **`60.0000`** | FastAPI Web UI + JSON export download (`app.py`, `README.md`) (`0.50 h`); isolated fault/baseline worktree reset & cleanup (`0.10 h`). |
| **`muhammad`** | `0.00 h` | `0.00 h` | `0.15 h` *(9 min)* | `0.50 h` *(30 min)* | **`0.65 h`** *(39 min)* | **`65.0000`** | S6 feedback remediation (generic Python contract, pre-QA short-circuit) + `tests/test_session_07_factory.py` (`0.50 h`); executing fault & `R-02` runs (`0.15 h`). |
| **Category Total** | **`1.50 h`** *(90 min)* | **`0.75 h`** *(45 min)* | **`0.25 h`** *(15 min)* | **`0.75 h`** *(45 min)* | **`3.25 h`** *(195 min)* | **`325.0000`** | **`2.50 h` (`250.0` credits) Customer Delivery/Review/Rework + `0.75 h` (`75.0` credits) Factory Dev.** |

### 5.2 Cumulative S6 + S7 Budget vs. Actual Comparison (`C2`)

| Cost Category | Planned S6+S7 Budget (`costs/cost-model.yaml`) | Session 6 Actual (`2026-11-16`) | Session 7 Actual (`2026-11-23`) | S6 + S7 Cumulative Actual | Variance vs. S6+S7 Plan & Explanation |
|---|---:|---:|---:|---:|---|
| **Customer Delivery (Human)** | `450.0000` *(4.50 h)* | `100.0000` *(1.00 h)* | `150.0000` *(1.50 h)* | **`250.0000`** *(2.50 h)* | **`-200.0000` (`-2.00 h` under plan):** `calculator.py` from S6 already satisfied all `Q01`–`Q14` and `E01`–`E10` rules, saving implementation hours in S7. |
| **Human Review & Rework (Human)** | `150.0000` *(1.50 h)* | `75.0000` *(0.75 h)* | `100.0000` *(1.00 h: 0.75 review + 0.25 rework)* | **`175.0000`** *(1.75 h)* | **`+25.0000` (`+0.25 h` above sub-plan):** Extra review time invested in thorough 3-part verification (Web UI `Q12`/JSON download, controlled fault `Q03`, and `R-02` baseline). |
| **Total Customer Human Effort (S6+S7)** | **`600.0000`** *(6.00 h)* | **`175.0000`** *(1.75 h)* | **`250.0000`** *(2.50 h)* | **`425.0000`** *(4.25 h)* | **`-175.0000` (`29.2%` under `600.0` human budget).** |
| **Multi-Agent Workflow Runs (Agent)** | `25.0000` | `12.3969` *(2 workflows, 7 calls)* | **`10.8720`** *(3 workflows, 9 calls: `4.0198` `S7-001` + `3.4843` `FAULT-001` + `3.3679` `R-02`)* | **`23.2689`** *(5 workflows, 16 calls)* | **`-1.7311` (`6.9%` under `25.0` agent budget):** Includes all failed S6 (`3.7552`), S7 fault (`3.4843`), and `R-02` baseline (`3.3679`) runs (`untraced S6 diagnostic probes` remain marked `unknown`). |
| **GitHub Actions CI Runs (CI)** | `6.0000` *(6 runs)* | `3.0000` *(3 runs on 16.11.)* | `2.0000` *(2 runs on 23.11.)* | **`5.0000`** *(5 runs)* | **`-1.0000` (`5` of `6` planned CI runs used across S6 & S7).** |
| **Customer Delivery Subtotal (S6+S7)** | **`631.0000`** | **`190.3969`** *(known partial)* | **`262.8720`** | **`453.2689`** *(known partial)* | **`-177.7311` (`28.17%` under `631.0` S6+S7 customer delivery budget).** |
| **Separate Factory Switch & Adaptation (Human)** | **`150.0000`** *(1.50 h S6–S8)* | `75.0000` *(0.75 h)* | `75.0000` *(0.75 h)* | **`150.0000`** *(1.50 h)* | **`0.0000` (On target):** Completed second-customer switch (S6) + generic Python contract refactoring, pre-QA short-circuit, and S7 gate tests (S7). |
| **`S8` Change Reserve (`CR-02` / `HP-V2`)** | **`315.0000`** *(reserved for S8)* | `0.0000` | `0.0000` | **`0.0000`** | **100% of `315.0` credit S8 reserve remains untouched for Session 8 (`CR-02` / `HP-V2`).** |

---

## 6. Next Actions for Session 8 (Max 3) (`D2`)

1. **Implement Targeted Factory Improvement (`F-NEW-S8`) & Re-Run `R-02` on `Q-BASE`:** After freezing `R-02-BASELINE-001`, implement AST-based Python baseline extraction & delta-key merging (`extract_verified_baseline_from_python_module`) in `src/agents/customer_delivery_workflow.py`, re-run `R-02` from `Q-BASE`, and compare latency, output tokens, quality, and credits against `R-02-BASELINE-001`.
2. **Deliver Customer Change `CR-02` (`HP-V2` Shipping Rule, `HP-AC08`):** Process `CR-02` (`1500` cents shipping below `40000` cents goods net after discount, `0` cents from `40000` cents) through the Factory, update product checks for `HP-V2` (`Q01`–`Q14`, especially `Q06`, `Q08`, `Q10`, `Q11`), and verify UI and JSON export consistency.
3. **Finalize Versioned Release Handover & Full S6–S8 Cost Balance (`HP-AC09`):** Document the final release candidate, technical approval vs. customer acceptance status, and complete S6–S8 cost and reuse evaluation in `evidence/session-08.md`.
