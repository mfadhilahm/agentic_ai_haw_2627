# Session 6 Evidence – Second Customer (`quotation-02` / HansePack), Same Software Factory

- **Company / Factory Repository:** `HAW Agentic Software Factory` ([`agentic_ai_haw_2627`](https://github.com/mfadhilahm/agentic_ai_haw_2627))
- **Customer Project 02 Product Repository:** `HansePack Handelsgesellschaft` (`../client-02-quotation`, GitHub: [`client-02-quotation`](https://github.com/minhnyn/client-02-quotation))
- **Frozen Previous Customer Repository:** `Nordwerk Industrie-Service` (`../client-01-website`, GitHub: [`client-01-website`](https://github.com/mfadhilahm/client-01-website))
- **Project ID / Session 6 Task ID:** `quotation-02` / `HP-S6-001`
- **Session:** Termin 6 (`2026-11-16`)
- **Team Members (Accountable Humans, Team Size = 6):**
  - `yaw` – Commission Lead & Budget / Cost Accounting
  - `saad` – Requirements Owner & Technical Release Gate Reviewer
  - `felix` – Project Manager, QA & Automated Product Checks
  - `minh` – Software Architect (`dev_architect_agent` – `software_architect`) & Failed-Run Gate Reviewer
  - `mirko` – Technical Delivery Lead (`dev_architect_agent` – `backend_api_engineer`)
  - `muhammad` – Agent & Integration Engineer, Project Isolation & Rework Lead

---

## Executive Summary & Version Matrix (`A1`, `B5`, `D1`, `D2`)

| Reference Role | Repository | Commit SHA | Verification & Status |
|---|---|---|---|
| **Frozen Nordwerk Product Baseline** | `client-01-website` | `53885e0a430dab3d75ed12b6ff4d7078aa19c595` | Clean working tree (`git status --porcelain` empty); `7/7` tests passed via `unittest` (`0.005s`) after HansePack delivery. |
| **Initial S6 Factory Switch Commit** | `agentic_ai_haw_2627` | `5270442050faf64484ae7d053a3213c091bc187f` | Added `config/projects/quotation-02.yaml`, Python quotation module workflow support, and `tests/test_session_06_factory.py` (`16/16` passed). Used in failed run `WF-QUOTATION02-S6-001`. |
| **Fixed S6 Factory Commit** | `agentic_ai_haw_2627` | `f8d778b3968c307974016a162faeaff1c0af189c` | Added trailing JSON schema reminders in `architect_node` and `implementation_node` (`factory_commit_clean: true`, `workflow_code_sha256: ff82b557e2ed2da93b7c696ab6fdf1157f7eb4ef9cb11bc5970bb5e6b4827083`). Used in approved run `WF-QUOTATION02-S6-002`. |
| **HansePack Product Input Commit** | `client-02-quotation` | `a167bf3cc96fc8ce00c43c55c17a616a113f9290` | Contains unchanged fixtures (`data/HansePack_Katalog.json`, `data/HansePack_Referenzfaelle.json`), `docs/issue-01-session-06.md`, CLI `main.py`, `tests/test_quotation_s6.py`, and `TODO_FACTORY_GENERATION` placeholder in `quotation/calculator.py`. |
| **HansePack Product Output Commit (`S6`)** | `client-02-quotation` | `724cfe72a1758e40346d77afd4b2cc4fbe7eb57d` | Contains agent-delivered `quotation/calculator.py` (`SHA-256: 72a490c672026c95d8d7449b6d8aaeb7287bc6d024ad4ff921bd1806d4b90294`); `4/4` `pytest` (`0.31s`) and `4/4` `unittest` (`0.298s`) passed; CLI `Q01`/`Q03`/`E01` verified. |
| **Technical Team Gate Status** | `agentic_ai_haw_2627` | **`approved`** (`WF-QUOTATION02-S6-002`) | `WF-QUOTATION02-S6-001` explicitly rejected (`changes_requested` by `minh` in [`runs/quotation-02/WF-QUOTATION02-S6-001/review.json`](../runs/quotation-02/WF-QUOTATION02-S6-001/review.json)); `WF-QUOTATION02-S6-002` reviewed and approved by `saad` in [`runs/quotation-02/WF-QUOTATION02-S6-002/review.json`](../runs/quotation-02/WF-QUOTATION02-S6-002/review.json). |
| **Customer Acceptance Status** | `client-02-quotation` | **`pending_customer_acceptance`** | Explicitly separated from internal technical gate approval; awaiting live instructor review in Session 6. |

---

## 1. Commission Clarification, Fixture Provenance & Project Switch (`A1`, `A4`, `B5`, `B6`, `L6.1`)

### 1.1 Customer Issue & Binding Fixture Provenance
- **Customer Issue #1 (`HP-S6-001`):** [`../client-02-quotation/docs/issue-01-session-06.md`](../../client-02-quotation/docs/issue-01-session-06.md) defines Session 6 scope (`HP-AC01`, `HP-AC02` cases `Q01` and `Q03`, `HP-AC04` minimum `E01`), separates S7 (`Q01`–`Q14`, `E01`–`E10`, web UI, JSON export download) and S8 (`CR-02` / `HP-V2`), records explicit assumptions (integer cents, `Decimal` `ROUND_HALF_UP`, strict rejection of `bool`/`float`/`str`/out-of-range quantities without coercion, English JSON keys matching `HansePack_Referenzfaelle.json`), and documents the `S6`/`S7` budget and `S8` reserve.
- **Unchanged Customer Fixtures (`data/` in `client-02-quotation`):**
  - `data/HansePack_Katalog.json`: `SHA-256: 70f0e1a7389b136828a794c79df130762d7638d9f63b373a7fd43e16607f953a` (identical byte-for-byte to `task sheets/session-06-08/HansePack_Katalog.json`)
  - `data/HansePack_Referenzfaelle.json`: `SHA-256: 7deb994e5debd82019062574ecfb1e445c4bd474e98b33fb532668ae00dc839a` (identical byte-for-byte to `task sheets/session-06-08/HansePack_Referenzfaelle.json`)

### 1.2 Factory Reuse vs. Central Adaptation vs. Customer-Specific Work

| Layer | Status | Concrete Files & Evidence |
|---|---|---|
| **Reused Unchanged** | Reused as-is | `src/llm/factory.py` (`get_chat_model`), `src/app/settings.py`, `src/observability/tracing.py` (`append_trace`, `estimate_cost_credits`, `usage_from_message`), `src/agents/task_models.py` (`CustomerDeliveryTask`, `ProductHandoverPayload`, `QAHandoverPayload`), `src/agents/dev_architect_agent.py` (`load_role_metadata`), `src/agents/qa_test_agent.py`, workspace sandbox `validate_product_workspace_path` / `read_product_file_tool` / `write_product_file_tool` / `run_product_test_tool`, bounded retry graph (`architect -> implementation -> product_qa -> human_gate`), and `record_customer_human_review`. |
| **Central Multi-Project Adaptations** | Adapted centrally (no agent copy) | 1. [`config/projects/quotation-02.yaml`](../config/projects/quotation-02.yaml): project ID `quotation-02`, repo `../client-02-quotation`, write prefix `["quotation/"]`, test target `tests/test_quotation_s6.py`, and `HP-V1` business rule map.<br>2. [`src/agents/customer_delivery_workflow.py`](../src/agents/customer_delivery_workflow.py): made `build_task_from_project_config`, prompts, and `manifest_payload` (`test_commands`, `issue_and_pr_references`) project-config driven (removing hardcoded Nordwerk strings/URLs), added central Python quotation module validation/rendering/AST pre-gate (`_validate_and_normalize_quotation_fields`, `_render_quotation_python_module`, `validate_rendered_quotation_module_pre_gate`), and added trailing JSON schema reminders.<br>3. [`tests/test_session_06_factory.py`](../tests/test_session_06_factory.py): deterministic project-switch and Nordwerk-isolation `pytest` tests (`4` tests). |
| **Customer-Specific Product Artefacts** | Created in `client-02-quotation` | `quotation/calculator.py` (agent-generated via `WF-QUOTATION02-S6-002`), `quotation/__init__.py`, standalone CLI `main.py`, `tests/test_quotation_s6.py`, `docs/issue-01-session-06.md`, `README.md`, `.gitattributes`, `.gitignore`, and copied customer fixtures in `data/`. |

### 1.3 Customer Isolation & Clean Nordwerk State (`A4`, `B5`)
- **Sandbox & Write Scope:** `quotation-02` restricts agent writes strictly to `["quotation/"]`; `validate_product_workspace_path` blocks path traversal (`../client-01-website/...`), `.git`, `.env*`, `data/`, and `tests/`.
- **Automated Factory Isolation Test:** `test_project_isolation_hansepack_run_never_modifies_nordwerk_files` in [`tests/test_session_06_factory.py`](../tests/test_session_06_factory.py) snapshots SHA-256 hashes of all files in a temporary `client-01-website` tree before and after running `quotation-02`, confirming zero changes and confirming sandbox rejections.
- **Live Nordwerk Verification:** After all HansePack Factory runs, `client-01-website` remains at `53885e0a430dab3d75ed12b6ff4d7078aa19c595` with an empty `git status --porcelain` and `7/7` tests passing (`python -m unittest discover -s tests -p "test_*.py" -v`).

---

## 2. Real Multi-Agent Factory Runs & Human Gate Decisions (`A2`, `A3`, `D1`, `L6.2`)

Both real runs executed on local **Ollama `qwen3:4b@359d7dd4bcda`** (`temperature = 0.0`, `reasoning = False`, `json_mode = True`, `max_correction_loops = 2`; overridden via `LLM_MODEL=qwen3:4b` because local `.env` defaulted to `gemma4:e2b`).

### 2.1 Failed Initial Run `WF-QUOTATION02-S6-001` (Preserved & Rejected)
- **Artifacts:** [`manifest.json`](../runs/quotation-02/WF-QUOTATION02-S6-001/manifest.json), [`workflow-report.json`](../runs/quotation-02/WF-QUOTATION02-S6-001/workflow-report.json), [`trace.jsonl`](../runs/quotation-02/WF-QUOTATION02-S6-001/trace.jsonl), [`review.json`](../runs/quotation-02/WF-QUOTATION02-S6-001/review.json)
- **Outcome:** On initial Factory commit `5270442`, `architect_node` (`run_id=0f9f2778-2f54-4e00-bfe3-f1c2dd2dc3d3`, `59.2077s`, `819` in / `147` out tokens, `1.6143` credits) echoed the `required_content` JSON instead of `architecture_decisions`/`summary`. Implementation was safely skipped (`6d92c036`, `0.0` credits), QA ran `tests/test_quotation_s6.py` (`run_id=faf6a063-a2a6-4bcb-9846-3ce1734fe2fc`, `109.5365s`, `1917` in / `181` out tokens, `2.1409` credits, `exit_code=1`), and the workflow escalated to human (`escalate_to_human`). `minh` recorded `decision: "changes_requested"`.

### 2.2 Approved Delivery Run `WF-QUOTATION02-S6-002` (Bounded Self-Correction)
- **Artifacts:** [`manifest.json`](../runs/quotation-02/WF-QUOTATION02-S6-002/manifest.json), [`workflow-report.json`](../runs/quotation-02/WF-QUOTATION02-S6-002/workflow-report.json), [`trace.jsonl`](../runs/quotation-02/WF-QUOTATION02-S6-002/trace.jsonl), [`changes.patch`](../runs/quotation-02/WF-QUOTATION02-S6-002/changes.patch), [`review.json`](../runs/quotation-02/WF-QUOTATION02-S6-002/review.json)

| Step | Run ID | Agent (`Role`) | Human | Status | Duration (s) | Tokens (In / Out) | Credits | Key Outcome & Handover |
|---|---|---|---|---|---:|---:|---:|---|
| 1 | `34ccff9e-6b33-477e-aef7-e87cd472ab93` | `dev_architect_agent` (`software_architect`) | `minh` | `completed` | `20.7976` | `852` / `108` | `1.2293` | Read `docs/issue-01-session-06.md`; emitted 4 `architecture_decisions` and structured `ProductHandoverPayload` (`ready_for_implementation=true`) to `backend_api_engineer`. |
| 2 (Iter 1) | `533c53ca-06ee-4632-94f6-cb7db3de364b` | `dev_architect_agent` (`backend_api_engineer`) | `mirko` | `error` | `54.1357` | `419` / `285` | `1.5611` | `qwen3:4b` omitted `max_quantity`; strict no-fallback validator rejected output without touching `quotation/calculator.py`. |
| 3 (Iter 1) | `0a10b432-99f3-4cd1-9311-bebe91e40fe8` | `qa-test-agent` (`qa_test_engineer`) | `felix` | `failed` | `112.2074` | `1923` / `175` | `2.1675` | Ran `tests/test_quotation_s6.py` (`exit_code=1`); routed exact missing-key feedback (`max_quantity`) back to Iteration 2 (`max_correction_loops=2`). |
| 4 (Iter 2) | `c363c2c1-130d-4f89-bdaa-a16dcd16593b` | `dev_architect_agent` (`backend_api_engineer`) | `mirko` | `completed` | `130.8423` | `2056` / `284` | `2.3609` | Self-corrected all rule keys, passed `validate_rendered_quotation_module_pre_gate`, wrote `quotation/calculator.py` (`sha256=72a490c6...`) + `changes.patch`, handed `QAHandoverPayload` to QA. |
| 5 (Iter 2) | `0d436c3d-a2a0-4f16-a953-78f5c3a84fbd` | `qa-test-agent` (`qa_test_engineer`) | `felix` | `passed` | `31.1214` | `398` / `92` | `1.3229` | `tests/test_quotation_s6.py` passed (`exit_code=0`, 0 findings); transitioned to `human_gate_status = "pending_approval"`. |
| **Total** | **5 steps (2 iterations)** | **Ollama `qwen3:4b@359d7dd4bcda`** | **`saad` (Gate)** | **`approved` (Tech Gate)** | **`349.1044`** | **`5648` / `944`** | **`8.6417`** | **Product committed in `client-02-quotation` as `724cfe72a1758e40346d77afd4b2cc4fbe7eb57d`.** |

### 2.3 Separation of Agent Contribution vs. Human Work (`A2`)
- **Agent-Generated Product Code:** `quotation/calculator.py` (177 insertions, 8 deletions in [`changes.patch`](../runs/quotation-02/WF-QUOTATION02-S6-002/changes.patch), committed at `724cfe72...`) implementing `QuotationValidationError`, `load_catalogue`, `ROUND_HALF_UP` per-line discounts (`0%`/`5%`/`10%`), `HP-V1` shipping (`1200` cents below `50000` goods net), and strict validation.
- **Explicitly Recorded Human Work:** Initial product repository scaffolding (`main.py`, `quotation/__init__.py`, `docs/issue-01-session-06.md`, `README.md`, `.gitattributes`, `.gitignore`), independent tests (`tests/test_quotation_s6.py`), Factory multi-project adaptation (`quotation-02.yaml`, `customer_delivery_workflow.py`, `test_session_06_factory.py`), and human code/output review (`saad`, `minh`).

---

## 3. Concrete Business & Isolation Checks (`B1`–`B5`, `L6.3`)

| Check | Command / Invocation | Expected (Brief / Fixtures) | Observed Result |
|---|---|---|---|
| **Q01 (`HP-BOX × 1`)** | `python main.py --sku HP-BOX --quantity 1` & `test_q01_hp_box_quantity_1` | Goods net `250`, shipping `1200`, total `1450` cents (`EUR`, `HP-V1`) | **Passed:** `goods_net_cents=250`, `shipping_cents=1200`, `total_cents=1450` |
| **Q03 (`HP-BOX × 50`)** | `python main.py --sku HP-BOX --quantity 50` & `test_q03_hp_box_quantity_50_discount` | List `12500`, 5% discount `625`, goods net `11875`, shipping `1200`, total `13075` cents | **Passed:** `list_amount_cents=12500`, `discount_cents=625`, `goods_net_cents=11875`, `shipping_cents=1200`, `total_cents=13075` |
| **E01 (`quantity = 0`)** | `python main.py --sku HP-BOX --quantity 0` & `test_e01_quantity_zero_rejected_in_business_logic` | Understandable error; no valid quotation | **Passed (Expected Negative):** raises `QuotationValidationError` (`reason="quantity_out_of_range"`); CLI exits `1` with JSON error and empty `stdout` |
| **Product Test Suite** | `python -m pytest tests/test_quotation_s6.py -v` (in `../client-02-quotation`) | `4 passed` (`fixture_provenance`, `Q01`, `Q03`, `E01`) | **Passed:** `4 passed in 0.31s` ([`product-pytest.txt`](session-06/product-pytest.txt)) and `unittest` `4/4 OK` (`0.298s`) |
| **Factory & Isolation Suite** | `python -m pytest tests/test_session_03_factory.py tests/test_session_04_factory.py tests/test_session_05_factory.py tests/test_session_06_factory.py -v` | All S3–S6 Factory + isolation tests pass | **Passed:** `16 passed in 29.06s` ([`pytest.txt`](session-06/pytest.txt), [`pytest.xml`](session-06/pytest.xml)) |
| **Nordwerk Continuity** | `git -C ../client-01-website status --short` & `python -m unittest discover -s ../client-01-website/tests -p "test_*.py" -v` | Clean tree at `53885e0a...`; tests pass | **Passed:** clean working tree (`HEAD=53885e0a430dab3d75ed12b6ff4d7078aa19c595`); `7/7` tests passed in `0.005s` |

---

## 4. Cost Accounting, Project-Start Effort & Reuse Learning (`C1`–`C4`, `L6.4`)

All costs are recorded in [`costs/usage.csv`](../costs/usage.csv) (RFC-4180 8-column format) and [`costs/cost-model.yaml`](../costs/cost-model.yaml) at the official course rates (`100` credits/h human; `1.0 + 0.01/s + 0.02/1k in + 0.04/1k out` agent; `1.0` credit/CI run).

### 4.1 Budget Plan & Session 6 Known Costs (Partial Known Totals Marked)

| Cost Category | Planned Budget (`S6–S8`) | Session 6 Actual | Notes & Completeness |
|---|---:|---:|---|
| **Customer Delivery (`HP-S6-001`, Human)** | `600.0` *(S6+S7 human)* | `100.0000` *(1.00 h)* | `client-02-quotation` setup, unchanged fixtures, Issue #1, CLI `main.py`, `tests/test_quotation_s6.py`. |
| **Human Review (`HP-S6-001`, Human)** | *(included above)* | `50.0000` *(0.50 h)* | Diff/output review for `WF-QUOTATION02-S6-001` & `002`, `Q01`/`Q03`/`E01` CLI/test checks, Nordwerk isolation verification. |
| **Rework (`HP-S6-001`, Human)** | *(included above)* | `25.0000` *(0.25 h)* | Root-cause diagnosis of `WF-QUOTATION02-S6-001` architect prompt omission and executing `WF-QUOTATION02-S6-002`. |
| **Workflow Agent Runs (`WF-001` + `WF-002`)** | `25.0` *(S6+S7 agent)* | `12.3969` *(7 calls)* | Includes failed `WF-QUOTATION02-S6-001` (`3.7552`) + approved `WF-QUOTATION02-S6-002` (`8.6417`). |
| **Standalone Diagnostic Probes (Agent)** | — | `unknown` | Two untraced ad-hoc `qwen3:4b` prompt checks (`task-144` aborted, `task-154` 2 calls) during debugging; exact token/duration cost `unknown`. |
| **GitHub Actions CI Runs (CI)** | `6.0` *(S6+S7 CI)* | `0.0000` *(0 runs)* | `0` CI runs executed yet before push to `origin/main` (`1.0` credit applies upon push). |
| **Subtotal: Customer Project `quotation-02` (`S6`)** | **`631.0`** *(S6+S7 budget; `315.0` S8 reserve separate)* | **`187.3969` (partial known)** | `29.7%` of `631.0` S6/S7 delivery budget; excludes untraced diagnostic probe credits (`unknown`). |
| **Separate Factory Project-Switch Setup (`S6`, Human)** | **`150.0`** *(S6–S8 adaptation)* | **`75.0000`** *(0.75 h)* | One-off second-customer switch: `quotation-02.yaml`, central Python quotation workflow/pre-gate support, and `test_session_06_factory.py`. |
| **Combined Session 6 Known Total (Customer + Switch)** | — | **`262.3969` (partial known)** | Excludes untraced standalone diagnostic probes (`unknown`). |

### 4.2 Reuse Learning & Weakness Analysis (`C4`)
- **What Was Reused:** The provider abstraction (`src/llm/factory.py`), tracing and cost calculation (`src/observability/tracing.py`), LangGraph orchestration loop (`architect -> implementation -> product_qa -> human_gate`), workspace sandbox (`validate_product_workspace_path`), `ProductHandoverPayload`/`QAHandoverPayload` contracts, and `record_customer_human_review` transferred unchanged to `quotation-02`.
- **What Remained Customer-Specific:** Creating `config/projects/quotation-02.yaml`, building a Python-module renderer and AST pre-gate validator in `src/agents/customer_delivery_workflow.py` (since S3–S5 only supported HTML), creating `client-02-quotation` (`main.py`, fixtures, `tests/test_quotation_s6.py`), and removing residual `client-01-website` URL/test-command hardcodings in `manifest_payload`.
- **No Unsupported Causal Claims:** We do **not** claim causal cost or speed savings relative to Nordwerk (`website-01`), because Nordwerk (static German/English HTML pages) and HansePack (Python B2B quotation pricing/validation CLI & app) are fundamentally different commissions.
- **One Testable Weakness to Investigate Next:** Requiring `qwen3:4b` in `implementation_node` to echo all 12 flat `required_content` business-rule keys verbatim in one JSON call caused an omission (`max_quantity`) on Iteration 1 of `WF-QUOTATION02-S6-002` and added `166.34s` across the failed Iteration 1 QA + Iteration 2 retry. We should test whether splitting/structuring rule verification or adding an automatic pre-QA short-circuit (skipping external `pytest` + QA LLM when `implementation_node` already failed before writing any product file) reduces failed-iteration latency and credits in Session 7.

---

## 5. Next Actions for Session 7 (Max 3) (`D2`)

1. **Extend Python Logic & Business Tests (`HP-AC03`, `HP-AC04`):** Implement all 3 SKUs (`HP-BOX`, `HP-TAPE`, `HP-FILM`), full `Q01`–`Q14` (`HP-V1`), and all invalid inputs `E01`–`E10` verified by automated `client-02-quotation` tests.
2. **Build Small Web UI & JSON Export (`HP-AC05`, `HP-AC06`, `HP-AC07`):** Add FastAPI + HTML/CSS/JS quotation UI with visible `"Net amounts – course project, not a binding quotation"` notice, JSON download matching displayed calculation, fresh-checkout human review, controlled 5%-discount fault test (`> 50` vs `>= 50`), and `R-02` baseline measurement.
3. **Investigate Pre-QA Short-Circuit / Prompt Reliability:** Test skipping the redundant QA LLM call when `implementation_node` produces `written_file=None` (`ready_for_qa=False`), so bounded retries feed validation errors straight back to `implementation_node` before running `Q01`–`Q14` and `R-02`.
