# Session 6 Evidence – Second Customer (`quotation-02` / HansePack), Same Software Factory

- **Company / Factory Repository:** `HAW Agentic Software Factory` ([`agentic_ai_haw_2627`](https://github.com/mfadhilahm/agentic_ai_haw_2627))
- **Customer Project 02 Product Repository:** `HansePack Handelsgesellschaft` (`../client-02-quotation`, GitHub: [`client-02-quotation`](https://github.com/minhnyn/client-02-quotation))
- **Frozen Previous Customer Repository:** `Nordwerk Industrie-Service` (`../client-01-website`, GitHub: [`client-01-website`](https://github.com/mfadhilahm/client-01-website))
- **Project ID / Session 6 Task ID:** `quotation-02` / `HP-S6-001`
- **GitHub Issues Tracking Commission `HP-S6-001`:**
  - Customer Product Repository Issue: [`minhnyn/client-02-quotation#1`](https://github.com/minhnyn/client-02-quotation/issues/1)
  - Software Factory Repository Issue: [`mfadhilahm/agentic_ai_haw_2627#4`](https://github.com/mfadhilahm/agentic_ai_haw_2627/issues/4)
  - Versioned Issue Specification in Repo: [`../client-02-quotation/docs/issue-01-session-06.md`](https://github.com/minhnyn/client-02-quotation/blob/a167bf3cc96fc8ce00c43c55c17a616a113f9290/docs/issue-01-session-06.md)
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
| **Frozen Nordwerk Product Baseline (`S5 Final Release`)** | `client-01-website` | [`84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f`](https://github.com/mfadhilahm/client-01-website/commit/84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f) (`R-S5-FINAL` / `v1.0.0-s5-rc`) | Clean working tree (`git status --porcelain` empty); includes German `site/index.html` (`SHA-256: 6ebd91ed...`) and English website `site/en.html` (`SHA-256: 8b43eaa3...`) plus `docs/security-advisory-sr01.md`; `10/10` S3–S5 tests pass (`0.004s`); separately runnable via `python -m http.server 8080 --directory site`. |
| **Initial S6 Factory Switch Commit** | `agentic_ai_haw_2627` | [`5270442050faf64484ae7d053a3213c091bc187f`](https://github.com/mfadhilahm/agentic_ai_haw_2627/commit/5270442050faf64484ae7d053a3213c091bc187f) | Added `config/projects/quotation-02.yaml`, Python quotation module workflow support, and `tests/test_session_06_factory.py`. Used in failed run `WF-QUOTATION02-S6-001`. |
| **Fixed S6 Factory Commit** | `agentic_ai_haw_2627` | [`f8d778b3968c307974016a162faeaff1c0af189c`](https://github.com/mfadhilahm/agentic_ai_haw_2627/commit/f8d778b3968c307974016a162faeaff1c0af189c) | Added trailing JSON schema reminders in `architect_node` and `implementation_node` (`factory_commit_clean: true`, `workflow_code_sha256: ff82b557e2ed2da93b7c696ab6fdf1157f7eb4ef9cb11bc5970bb5e6b4827083`). Used in approved run `WF-QUOTATION02-S6-002`. |
| **HansePack Product Input Commit** | `client-02-quotation` | [`a167bf3cc96fc8ce00c43c55c17a616a113f9290`](https://github.com/minhnyn/client-02-quotation/commit/a167bf3cc96fc8ce00c43c55c17a616a113f9290) | Contains unchanged fixtures (`data/HansePack_Katalog.json`, `data/HansePack_Referenzfaelle.json`), `docs/issue-01-session-06.md`, CLI `main.py`, `tests/test_quotation_s6.py`, and `TODO_FACTORY_GENERATION` placeholder in `quotation/calculator.py`. |
| **HansePack Product Output Commit (`S6`)** | `client-02-quotation` | [`724cfe72a1758e40346d77afd4b2cc4fbe7eb57d`](https://github.com/minhnyn/client-02-quotation/commit/724cfe72a1758e40346d77afd4b2cc4fbe7eb57d) | Contains agent-delivered `quotation/calculator.py` (`SHA-256: 72a490c672026c95d8d7449b6d8aaeb7287bc6d024ad4ff921bd1806d4b90294`); `4/4` `pytest` and `4/4` `unittest` passed; CLI `Q01`/`Q03`/`E01` verified. |
| **Technical Team Gate Status** | `agentic_ai_haw_2627` | **`approved`** (`WF-QUOTATION02-S6-002`) | `WF-QUOTATION02-S6-001` explicitly rejected (`changes_requested` by `minh` in [`runs/quotation-02/WF-QUOTATION02-S6-001/review.json`](../runs/quotation-02/WF-QUOTATION02-S6-001/review.json)); `WF-QUOTATION02-S6-002` reviewed and approved by `saad` in [`runs/quotation-02/WF-QUOTATION02-S6-002/review.json`](../runs/quotation-02/WF-QUOTATION02-S6-002/review.json). |
| **Customer Acceptance Status** | `client-02-quotation` | **`pending_customer_acceptance`** | Explicitly separated from internal technical gate approval; awaiting live instructor review. |

---

## 1. Commission Clarification, Fixture Provenance & Project Switch (`A1`, `A4`, `B5`, `B6`, `L6.1`)

### 1.1 Real GitHub Issues & Binding Fixture Provenance
- **GitHub Issue #1 (`HP-S6-001`):** Tracked as a live GitHub Issue in [`minhnyn/client-02-quotation#1`](https://github.com/minhnyn/client-02-quotation/issues/1) and [`mfadhilahm/agentic_ai_haw_2627#4`](https://github.com/mfadhilahm/agentic_ai_haw_2627/issues/4) (mirrored in repository file [`../client-02-quotation/docs/issue-01-session-06.md`](https://github.com/minhnyn/client-02-quotation/blob/a167bf3cc96fc8ce00c43c55c17a616a113f9290/docs/issue-01-session-06.md)). Defines Session 6 scope (`HP-AC01`, `HP-AC02` cases `Q01` and `Q03`, `HP-AC04` minimum `E01`), separates S7 (`Q01`–`Q14`, `E01`–`E10`, web UI, JSON export download) and S8 (`CR-02` / `HP-V2`), records explicit assumptions (integer cents, `Decimal` `ROUND_HALF_UP`, strict rejection of `bool`/`float`/`str`/out-of-range quantities without coercion, English JSON keys matching `HansePack_Referenzfaelle.json`), and documents the `S6`/`S7` budget and `S8` reserve.
- **Unchanged Customer Fixtures (`data/` in `client-02-quotation`):**
  - `data/HansePack_Katalog.json`: `SHA-256: 70f0e1a7389b136828a794c79df130762d7638d9f63b373a7fd43e16607f953a` (identical byte-for-byte to `task sheets/session-06-08/HansePack_Katalog.json`)
  - `data/HansePack_Referenzfaelle.json`: `SHA-256: 7deb994e5debd82019062574ecfb1e445c4bd474e98b33fb532668ae00dc839a` (identical byte-for-byte to `task sheets/session-06-08/HansePack_Referenzfaelle.json`)

### 1.2 Factory Reuse vs. Generic Multi-Project Capabilities vs. Customer-Specific Configuration
To ensure true reusability across different customer domains (Feedback Point 3), the Factory strictly separates **generic workflow/validation capabilities** in [`src/agents/customer_delivery_workflow.py`](../src/agents/customer_delivery_workflow.py) from **declarative project configuration and external templates** under `config/projects/`:

| Layer | Reusability Classification | Concrete Files & Evidence |
|---|---|---|
| **Reused Unchanged from S1–S5** | 100% Generic Factory Infrastructure | `src/llm/factory.py` (`get_chat_model`), `src/app/settings.py`, `src/observability/tracing.py` (`append_trace`, `estimate_cost_credits`, `usage_from_message`), `src/agents/task_models.py` (`CustomerDeliveryTask`, `ProductHandoverPayload`, `QAHandoverPayload`), `src/agents/dev_architect_agent.py` (`load_role_metadata`), `src/agents/qa_test_agent.py`, workspace sandbox (`validate_product_workspace_path`, `read_product_file_tool`, `write_product_file_tool`, `run_product_test_tool`), bounded retry graph (`architect -> implementation -> product_qa -> human_gate`), and `record_customer_human_review`. |
| **Generic Multi-Project Python & Workflow Capabilities** | Generic Factory Core ([`src/agents/customer_delivery_workflow.py`](../src/agents/customer_delivery_workflow.py)) | 1. **Config-Driven Contract Validator (`validate_and_normalize_python_contract_fields`):** Validates required keys, integer bounds (`integer_rule_keys`), enum constraints (`enum_rule_keys`), and min/max pairs (`max_gte_min_pairs`) declared in any project's YAML config without silent fallback.<br>2. **Generic Python AST Pre-Gate (`validate_python_module_pre_gate`):** Parses any generated Python module (`ast.parse`), checks syntax, blocks generation placeholders (`TODO_FACTORY_GENERATION`) and forbidden Factory/LLM runtime imports (`FORBIDDEN_PRODUCT_LLM_IMPORTS`), and verifies project-configured classes (`required_classes`), functions (`required_functions`), and constants (`rule_constant_map`).<br>3. **Generic Template / Direct Code Renderer (`render_python_module_from_contract`):** Renders any external project template (`module_template_path`) or passes through direct LLM `python_code`.<br>4. **Pre-QA Short-Circuit (`product_qa_node`):** Immediately intercepts failed implementation steps (`status != "completed"` or `not ready_for_qa` or `written_file is None`) **before** spawning an external `pytest` subprocess or making an unnecessary QA LLM call (`0` calls, `0.0` credits, `tool_status="not_started"`), routing actionable validation errors straight back into the bounded retry loop. |
| **Declarative HansePack Project Config & Template** | Customer-Project Configuration (`config/projects/`) | 1. [`config/projects/quotation-02.yaml`](../config/projects/quotation-02.yaml): project ID `quotation-02`, repo `../client-02-quotation`, GitHub issues (`issues/1`, `issues/4`), write prefix `["quotation/"]`, test target `tests/test_quotation_s6.py`, `HP-V1` `required_content`, and declarative `python_module_contract`.<br>2. [`config/projects/templates/quotation_02_calculator.py.tpl`](../config/projects/templates/quotation_02_calculator.py.tpl): externalized HansePack Python module template consumed by `render_python_module_from_contract`. |
| **Customer Product Repository Artefacts** | Product Repo (`../client-02-quotation`) | `quotation/calculator.py` (agent-generated via `WF-QUOTATION02-S6-002`), `quotation/__init__.py`, standalone CLI `main.py`, `tests/test_quotation_s6.py`, `docs/issue-01-session-06.md`, `README.md`, `.gitattributes`, `.gitignore`, and unchanged customer fixtures in `data/`. |

### 1.3 Customer Isolation & Clean Session 5 Nordwerk State (`84d5baf`, Including English Website) (`A4`, `B5`)
- **Sandbox & Write Scope:** `quotation-02` restricts agent writes strictly to `["quotation/"]`; `validate_product_workspace_path` blocks path traversal (`../client-01-website/site/index.html`, `../client-01-website/site/en.html`), `.git`, `.env*`, `data/`, and `tests/`.
- **Automated Factory Isolation Test on Session 5 Nordwerk Release (`84d5baf`):** `test_project_isolation_hansepack_run_never_modifies_nordwerk_files` in [`tests/test_session_06_factory.py`](../tests/test_session_06_factory.py) creates a complete Session 5 (`84d5baf` / `v1.0.0-s5-rc`) Nordwerk checkout — including both the German page (`site/index.html`) and the **English entry page (`site/en.html`)**, `site/styles.css`, `docs/issue-03-session-05-cr01.md`, `docs/security-advisory-sr01.md`, `docs/release-s5-handover.md`, and `tests/test_website_s5.py` — snapshots SHA-256 hashes of all files before and after executing the `quotation-02` workflow, confirms zero modifications (`nordwerk_after == nordwerk_before`), and executes `tests/test_website_s5.py` (`exit_code = 0`) on the untouched bilingual Nordwerk checkout.
- **Live Verification of Frozen Nordwerk Session 5 Release (`84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f`):**
  - Repository `../client-01-website` is checked out cleanly at the actual final Session 5 release commit **`84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f`** (`R-S5-FINAL` / `v1.0.0-s5-rc`, replacing the outdated Session 4 reference `53885e0`), with `git status --porcelain` empty.
  - Both `site/index.html` (`SHA-256: 6ebd91ed...`) and the English website `site/en.html` (`SHA-256: 8b43eaa3...`) remain unchanged and separately runnable via `python -m http.server 8080 --directory site` (`http://localhost:8080/index.html` and `http://localhost:8080/en.html`).
  - All **`10/10`** automated product and regression tests across `tests/test_website_s3.py`, `tests/test_website_s4.py`, and `tests/test_website_s5.py` pass (`python -m unittest discover -s tests -p "test_*.py" -v` $\rightarrow$ `Ran 10 tests in 0.004s — OK`).

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
| 4 (Iter 2) | `c363c2c1-130d-4f89-bdaa-a16dcd16593b` | `dev_architect_agent` (`backend_api_engineer`) | `mirko` | `completed` | `130.8423` | `2056` / `284` | `2.3609` | Self-corrected all rule keys, passed `validate_python_module_pre_gate`, wrote `quotation/calculator.py` (`sha256=72a490c6...`) + `changes.patch`, handed `QAHandoverPayload` to QA. |
| 5 (Iter 2) | `0d436c3d-a2a0-4f16-a953-78f5c3a84fbd` | `qa-test-agent` (`qa_test_engineer`) | `felix` | `passed` | `31.1214` | `398` / `92` | `1.3229` | `tests/test_quotation_s6.py` passed (`exit_code=0`, 0 findings); transitioned to `human_gate_status = "pending_approval"`. |
| **Total** | **5 steps (2 iterations)** | **Ollama `qwen3:4b@359d7dd4bcda`** | **`saad` (Gate)** | **`approved` (Tech Gate)** | **`349.1044`** | **`5648` / `944`** | **`8.6417`** | **Product committed in `client-02-quotation` as `724cfe72a1758e40346d77afd4b2cc4fbe7eb57d`.** |

### 2.3 Separation of Agent Contribution vs. Human Work (`A2`)
- **Agent-Generated Product Code:** `quotation/calculator.py` (177 insertions, 8 deletions in [`changes.patch`](../runs/quotation-02/WF-QUOTATION02-S6-002/changes.patch), committed at `724cfe72...`) implementing `QuotationValidationError`, `load_catalogue`, `ROUND_HALF_UP` per-line discounts (`0%`/`5%`/`10%`), `HP-V1` shipping (`1200` cents below `50000` goods net), and strict validation.
- **Explicitly Recorded Human Work:** Initial product repository scaffolding (`main.py`, `quotation/__init__.py`, GitHub Issue #1 & `docs/issue-01-session-06.md`, `README.md`, `.gitattributes`, `.gitignore`), independent tests (`tests/test_quotation_s6.py`), Factory multi-project adaptation (`quotation-02.yaml`, `quotation_02_calculator.py.tpl`, `customer_delivery_workflow.py`, `test_session_06_factory.py`), and human code/output review (`saad`, `minh`, `felix`).

---

## 3. Concrete Business & Isolation Checks (`B1`–`B5`, `L6.3`)

| Check | Command / Invocation | Expected (Brief / Fixtures) | Observed Result |
|---|---|---|---|
| **Q01 (`HP-BOX × 1`)** | `python main.py --sku HP-BOX --quantity 1` & `test_q01_hp_box_quantity_1` | Goods net `250`, shipping `1200`, total `1450` cents (`EUR`, `HP-V1`) | **Passed:** `goods_net_cents=250`, `shipping_cents=1200`, `total_cents=1450` |
| **Q03 (`HP-BOX × 50`)** | `python main.py --sku HP-BOX --quantity 50` & `test_q03_hp_box_quantity_50_discount` | List `12500`, 5% discount `625`, goods net `11875`, shipping `1200`, total `13075` cents | **Passed:** `list_amount_cents=12500`, `discount_cents=625`, `goods_net_cents=11875`, `shipping_cents=1200`, `total_cents=13075` |
| **E01 (`quantity = 0`)** | `python main.py --sku HP-BOX --quantity 0` & `test_e01_quantity_zero_rejected_in_business_logic` | Understandable error; no valid quotation | **Passed (Expected Negative):** raises `QuotationValidationError` (`reason="quantity_out_of_range"`); CLI exits `1` with JSON error and empty `stdout` |
| **Product Test Suite** | `python -m pytest tests/test_quotation_s6.py -v` (in `../client-02-quotation`) | `4 passed` (`fixture_provenance`, `Q01`, `Q03`, `E01`) | **Passed:** `4 passed in 0.31s` ([`product-pytest.txt`](session-06/product-pytest.txt)) and `unittest` `4/4 OK` (`0.298s`) |
| **Factory & Isolation Suite** | `python -m pytest tests/test_session_03_factory.py tests/test_session_04_factory.py tests/test_session_05_factory.py tests/test_session_06_factory.py -v` | All S3–S6 Factory + isolation + short-circuit tests pass | **Passed:** `18 passed` ([`pytest.txt`](session-06/pytest.txt), [`pytest.xml`](session-06/pytest.xml)) |
| **Nordwerk Continuity (`S5 Release 84d5baf`)** | `git -C ../client-01-website status --short`, `python -m http.server 8080 --directory ../client-01-website/site`, & `python -m unittest discover -s ../client-01-website/tests -p "test_*.py" -v` | Clean tree at `84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f` (`v1.0.0-s5-rc`, including `site/index.html` & English `site/en.html`); separately runnable; `10/10` tests pass | **Passed:** clean working tree (`HEAD=84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f`); `site/index.html` (`6ebd91ed...`) and `site/en.html` (`8b43eaa3...`) intact; `10/10` S3–S5 tests passed in `0.004s` |

---

## 4. Cost Accounting, Person-Hours Breakdown & Reuse Learning (`C1`–`C4`, `L6.4`)

All costs are recorded in [`costs/usage.csv`](../costs/usage.csv) (RFC-4180 8-column format) and [`costs/cost-model.yaml`](../costs/cost-model.yaml) at the official course rates (`100` credits/Personenstunde human; `1.0 + 0.01/s + 0.02/1k in + 0.04/1k out` agent; `1.0` credit/CI run).

### 4.1 Exclusive Per-Member Person-Hours (`Personenstunden`) Matrix (`C2`, `C3`)
To avoid any ambiguity between wall-clock time and person-hours (`Personenstunden`), every human activity in Session 6 (`2026-11-16`) is recorded per individual team member and assigned to exactly one exclusive category in [`costs/usage.csv`](../costs/usage.csv):

| Team Member | Customer Delivery (`HP-S6-001`) | Human Review (`HP-S6-001`) | Rework (`HP-S6-001`) | Separate Factory Switch (`SESSION-06-FACTORY-SWITCH`) | Member Total (`Personenstunden`) | Member Credits (`100 / h`) | Concrete Tasks Performed |
|---|---:|---:|---:|---:|---:|---:|---|
| **`yaw`** | `0.25 h` *(15 min)* | `0.00 h` | `0.00 h` | `0.00 h` | **`0.25 h`** *(15 min)* | **`25.0000`** | `client-02-quotation` setup, unchanged fixture copy (`data/`), SHA-256 check, S6–S8 budget plan. |
| **`saad`** | `0.25 h` *(15 min)* | `0.20 h` *(12 min)* | `0.00 h` | `0.00 h` | **`0.45 h`** *(27 min)* | **`45.0000`** | Commission scoping & GitHub Issue #1 (`0.25 h`); diff inspection & gate approval of `WF-QUOTATION02-S6-002` (`0.20 h`). |
| **`felix`** | `0.25 h` *(15 min)* | `0.15 h` *(9 min)* | `0.00 h` | `0.00 h` | **`0.40 h`** *(24 min)* | **`40.0000`** | Automated test suite `tests/test_quotation_s6.py` (`0.25 h`); independent CLI/pytest & Nordwerk `84d5baf` (`site/en.html`) check (`0.15 h`). |
| **`minh`** | `0.00 h` | `0.15 h` *(9 min)* | `0.00 h` | `0.25 h` *(15 min)* | **`0.40 h`** *(24 min)* | **`40.0000`** | `config/projects/quotation-02.yaml` & `python_module_contract` (`0.25 h`); gate review & rejection of `WF-QUOTATION02-S6-001` (`0.15 h`). |
| **`mirko`** | `0.25 h` *(15 min)* | `0.00 h` | `0.10 h` *(6 min)* | `0.00 h` | **`0.35 h`** *(21 min)* | **`35.0000`** | Standalone CLI `main.py` & `README.md` (`0.25 h`); worktree reset after `WF-001` & re-running `WF-002` (`0.10 h`). |
| **`muhammad`** | `0.00 h` | `0.00 h` | `0.15 h` *(9 min)* | `0.50 h` *(30 min)* | **`0.65 h`** *(39 min)* | **`65.0000`** | Generic Python contract validator, external template loader, pre-QA short-circuit & `test_session_06_factory.py` (`0.50 h`); `WF-001` diagnosis & schema reminder fix `f8d778b` (`0.15 h`). |
| **Category Total** | **`1.00 h`** *(60 min)* | **`0.50 h`** *(30 min)* | **`0.25 h`** *(15 min)* | **`0.75 h`** *(45 min)* | **`2.50 h`** *(150 min)* | **`250.0000`** | **`1.75 h` (`175.0` credits) Customer Project + `0.75 h` (`75.0` credits) Factory Switch.** |

### 4.2 Budget Plan & Session 6 Known Costs (Including All 3 GitHub CI Runs on `2026-11-16`)

| Cost Category | Planned Budget (`S6–S8`) | Session 6 Actual | Notes & Completeness |
|---|---:|---:|---|
| **Customer Delivery (`HP-S6-001`, Human)** | `600.0` *(S6+S7 human)* | `100.0000` *(1.00 h)* | `yaw` (`0.25 h`) + `saad` (`0.25 h`) + `mirko` (`0.25 h`) + `felix` (`0.25 h`). |
| **Human Review (`HP-S6-001`, Human)** | *(included above)* | `50.0000` *(0.50 h)* | `saad` (`0.20 h`) + `minh` (`0.15 h`) + `felix` (`0.15 h`). |
| **Rework (`HP-S6-001`, Human)** | *(included above)* | `25.0000` *(0.25 h)* | `muhammad` (`0.15 h`) + `mirko` (`0.10 h`). |
| **Workflow Agent Runs (`WF-001` + `WF-002`)** | `25.0` *(S6+S7 agent)* | `12.3969` *(7 calls)* | Includes failed `WF-QUOTATION02-S6-001` (`3.7552`) + approved `WF-QUOTATION02-S6-002` (`8.6417`). |
| **Standalone Diagnostic Probes (Agent)** | — | `unknown` | Two untraced ad-hoc `qwen3:4b` prompt checks (`task-144` aborted, `task-154` 2 calls) during debugging; exact token/duration cost `unknown`. |
| **GitHub Actions CI Runs (`2026-11-16`, CI)** | `6.0` *(S6+S7 CI)* | `3.0000` *(3 runs)* | All **3 GitHub Actions CI runs** on `2026-11-16` (commits [`5270442`](https://github.com/mfadhilahm/agentic_ai_haw_2627/commit/5270442050faf64484ae7d053a3213c091bc187f), [`f8d778b`](https://github.com/mfadhilahm/agentic_ai_haw_2627/commit/f8d778b3968c307974016a162faeaff1c0af189c), [`e86ad33`](https://github.com/mfadhilahm/agentic_ai_haw_2627/commit/e86ad33)). |
| **Subtotal: Customer Project `quotation-02` (`S6`)** | **`631.0`** *(S6+S7 budget; `315.0` S8 reserve separate)* | **`190.3969` (partial known)** | `30.2%` of `631.0` S6/S7 delivery budget; excludes untraced diagnostic probe credits (`unknown`). |
| **Separate Factory Project-Switch Setup (`S6`, Human)** | **`150.0`** *(S6–S8 adaptation)* | **`75.0000`** *(0.75 h)* | `muhammad` (`0.50 h`) + `minh` (`0.25 h`): generic Python contract validator, external template loader, pre-QA short-circuit, `quotation-02.yaml`, and `test_session_06_factory.py`. |
| **Combined Session 6 Known Total (Customer + Switch)** | — | **`265.3969` (partial known)** | Excludes untraced standalone diagnostic probes (`unknown`). |

### 4.3 Reuse Learning, Generic Refactoring & Pre-QA Short-Circuit (`C4`)
- **What Was Reused Unchanged:** The provider abstraction (`src/llm/factory.py`), tracing and cost calculation (`src/observability/tracing.py`), LangGraph orchestration loop (`architect -> implementation -> product_qa -> human_gate`), workspace sandbox (`validate_product_workspace_path`), `ProductHandoverPayload`/`QAHandoverPayload` contracts, and `record_customer_human_review` transferred unchanged to `quotation-02`.
- **Separating Generic Python Capabilities from HansePack-Specific Templates (Feedback Point 3):** We refactored `src/agents/customer_delivery_workflow.py` so that the HansePack Python source template is externalized to [`config/projects/templates/quotation_02_calculator.py.tpl`](../config/projects/templates/quotation_02_calculator.py.tpl) and its structural/rule constraints are declared in [`config/projects/quotation-02.yaml`](../config/projects/quotation-02.yaml) (`python_module_contract`). The Factory workflow now provides genuinely generic capabilities (`validate_and_normalize_python_contract_fields`, `render_python_module_from_contract`, `validate_python_module_pre_gate`) reusable for any Python customer project.
- **Pre-QA Short-Circuit Implemented & Verified (Feedback Point 3):** In `WF-QUOTATION02-S6-001` (`2.1409` QA credits, `109.54 s`) and `WF-QUOTATION02-S6-002` Iteration 1 (`2.1675` QA credits, `112.21 s`), `product_qa_node` had executed an external `pytest` subprocess and a `qa-test-agent` LLM call even though `implementation_node` had already failed pre-gate validation and written no file (`written_file=None`, `ready_for_qa=False`). We added an automatic **Pre-QA Short-Circuit** at the entry of `product_qa_node`: whenever `implementation_node` fails (`status != "completed"` or `not ready_for_qa` or `not written_file`), `product_qa_node` skips both `run_product_test_tool` and the QA LLM call (`0` calls, `0.0` credits, `tool_status="not_started"`) and immediately routes the validation error back to `implementation_node` (verified by `test_generic_python_contract_and_pre_qa_short_circuit_on_failed_implementation` in [`tests/test_session_06_factory.py`](../tests/test_session_06_factory.py)).
- **No Unsupported Causal Claims:** We do **not** claim causal cost or speed savings relative to Nordwerk (`website-01`), because Nordwerk (static German/English HTML pages) and HansePack (Python B2B quotation pricing/validation CLI & app) are fundamentally different commissions.

---

## 5. Next Actions for Session 7 (Max 3) (`D2`)

1. **Complete Python Business Logic & Full Reference Test Suite (`HP-AC03`, `HP-AC04`):** Verify all 3 SKUs (`HP-BOX`, `HP-TAPE`, `HP-FILM`), all valid cases `Q01`–`Q14` (`HP-V1`), and all invalid inputs `E01`–`E10` via automated tests in `../client-02-quotation`.
2. **Deliver Small Web UI, JSON Export & Controlled Fault Gate (`HP-AC05`, `HP-AC06`, `HP-AC07`):** Add the quotation web UI with visible `"Net amounts – course project, not a binding quotation"` notice and JSON download matching displayed results, perform human UI/export review, and demonstrate that an injected 5%-discount boundary fault (`> 50` vs. `>= 50` failing `Q03` with `13700` instead of `13075` cents) blocks release approval.
3. **Record `R-02` Baseline on Isolated `Q-BASE` Checkout (`L7.4`):** Freeze `Q-BASE` and `F-BASE`, run reference experiment `R-02` (`calculation_note: "Net amounts; shipping shown separately."`) on an isolated copy of `Q-BASE`, and formulate a targeted optimization hypothesis for Session 8.
