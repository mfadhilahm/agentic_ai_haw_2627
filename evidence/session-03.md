# Session 3 – First Customer Delivery Evidence (`evidence/session-03.md`)

- **Project ID:** `website-01` (**Nordwerk Industrie-Service**)
- **Customer Task ID:** `NW-S3-001`
- **Date:** 2026-10-26

---

## 1. Repository & Commit References (`A1`, `C1`, `D2`)

| Repository | Role | GitHub URL / Checkout Path | Input Commit (Frozen Before Run) | Output / Evidence Commit |
| :--- | :--- | :--- | :--- | :--- |
| **`agentic_ai_haw_2627`** | Software Factory | `https://github.com/mfadhilahm/agentic_ai_haw_2627` | `c6b8348ccbb1a6f83e8082a18807270331e142d2` | Recorded in Session 3 submission commit |
| **`client-01-website`** | Customer Product | `https://github.com/mfadhilahm/client-01-website` (`../client-01-website`) | `15d7ce55ba48effe15904833b0b9df819552a6d5` (`15d7ce5`) | `5b9aefa412a67cf3350c5aac98c856a099d72bec` (`5b9aefa`) |

- **Project Configuration File:** [`config/projects/website-01.yaml`](../config/projects/website-01.yaml)
- **Customer Issue:** `client-01-website` Issue `#1` / `docs/issue-01-session-03.md` (`NW-S3-001`)

---

## 2. Factory Runs, Run IDs & Multi-Agent Cooperation (`A2`, `A3`, `A4`, `C1`)

All run traces, manifests, unified diffs (`changes.patch`), and human gate review records (`review.json`) are stored without overwriting under `runs/website-01/<workflow_id>/`:

### Workflow 1: `WF-WEBSITE01-S3-001` (Rejected Intermediate Run – `changes_requested`)
- **Directory:** [`runs/website-01/WF-WEBSITE01-S3-001/`](../runs/website-01/WF-WEBSITE01-S3-001/)
- **Run IDs:** `e6611738-5146-4ed7-9200-7ece09e694db`, `ccf9f03d-50df-4d86-b123-89edbb059279`, `7315b671-9289-4ef3-b9ee-a71d8c954f67`
- **Human Gate Decision:** `changes_requested` (Reviewer: `muhammad`, see [`runs/website-01/WF-WEBSITE01-S3-001/review.json`](../runs/website-01/WF-WEBSITE01-S3-001/review.json))
- **Reason for Rejection & Rework:** Local `.env` had an unapproved `openai_compatible` provider configured from an earlier test. Per `docs/SESSION_03_TECHNICAL_NOTES.md`, the product checkout was reset to the frozen input commit (`15d7ce5`) and re-executed using the local Ollama model `qwen3:4b@359d7dd4bcda`.

### Workflow 2: `WF-WEBSITE01-S3-002` (Approved Production Run – Local Ollama `qwen3:4b@359d7dd4bcda`)
- **Directory:** [`runs/website-01/WF-WEBSITE01-S3-002/`](../runs/website-01/WF-WEBSITE01-S3-002/)
- **Manifest:** [`runs/website-01/WF-WEBSITE01-S3-002/manifest.json`](../runs/website-01/WF-WEBSITE01-S3-002/manifest.json)
- **Raw Trace:** [`runs/website-01/WF-WEBSITE01-S3-002/trace.jsonl`](../runs/website-01/WF-WEBSITE01-S3-002/trace.jsonl)
- **Product Patch:** [`runs/website-01/WF-WEBSITE01-S3-002/changes.patch`](../runs/website-01/WF-WEBSITE01-S3-002/changes.patch) (`site/index.html` SHA-256: `9424b48c5f309148cc95abbf49180d62fa5df290de0f5652d20fb2fb0a1f460b`)
- **Human Gate Decision:** `approved` (Reviewer: `saad`, see [`runs/website-01/WF-WEBSITE01-S3-002/review.json`](../runs/website-01/WF-WEBSITE01-S3-002/review.json))

| Step | Run ID | Agent & Role | Accountable Human | Tool Action on Product Checkout | Structured Handover | Tokens (In / Out) | Duration | Credits |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Planning** | `0f80f57a-ea68-4719-ae6d-597541d8a3d8` | `dev_architect_agent` (`software_architect`) | `minh` | `read_product_file_tool` (`docs/issue-01-session-03.md`, `site/index.html`, `site/styles.css`) | Produces `ProductHandoverPayload` $\rightarrow$ `backend_api_engineer` | 792 / 151 | 80.74s | 1.8293 |
| **2. Implementation** | `f94402cb-6d67-44e0-b4e9-410c8188f5b4` | `dev_architect_agent` (`backend_api_engineer`) | `mirko` | `write_product_file_tool` (writes `site/index.html` in `../client-01-website`) | Produces `QAHandoverPayload` $\rightarrow$ `qa_test_engineer` | 479 / 384 | 100.80s | 2.0329 |
| **3. Product QA** | `89972355-4ca8-48fe-8a7d-ae1de042f0a3` | `qa-test-agent` (`qa_test_engineer`) | `felix` | `run_product_test_tool` (runs `tests/test_website_s3.py` in `../client-01-website`, 4/4 passed) | Routes to `human_gate` (`pending_approval`) | 347 / 76 | 30.92s | 1.3192 |

---

## 3. Checks Against Today's Acceptance Criteria (`B1`–`B6`, `D1`)

| Criterion | Required Check | Verification Method & Evidence | Status |
| :--- | :--- | :--- | :--- |
| **AC-01 (`B1`)** | Company name (`N-01`) and main statement (`N-02`) easy to find on initial view. | Automated (`test_ac01_identity_and_main_statement` in `client-01-website/tests/test_website_s3.py`) + human visual review (`saad`). | **Passed** |
| **AC-02 Slice (`B2`)** | One service (`N-03`: *Wartungsplanung*) with verbatim required description present. | Automated (`test_ac02_first_service_present`) + human visual review (`saad`). | **Passed** |
| **AC-04 (`B3`)** | Contact link labeled `Anfrage stellen` targeting `mailto:kontakt@nordwerk.example` (`N-08`) + visible course notice (`N-09`). | Automated (`test_ac04_contact_mailto_and_course_notice`) + human link & visual check (`saad`). | **Passed** |
| **Product Check (`B4`)** | Meaningful automated check in product repo runs separately (`python -m unittest discover -s tests -p "test_*.py" -v`). | 4/4 passed in `client-01-website` (`tests/test_website_s3.py`). | **Passed** |
| **Independent Start (`B5`)** | Website starts without Factory/LLM/DB (`python -m http.server 8080 --directory site`). | Verified and documented in `client-01-website/README.md`. | **Passed** |
| **Own Factory Check (`D1`)** | Factory test verifying project assignment, workspace sandboxing, structured handover state, and bounded retry loops. | [`tests/test_session_03_factory.py`](../tests/test_session_03_factory.py) (4/4 passed; full suite recorded in [`evidence/session-03/pytest.txt`](session-03/pytest.txt) and [`evidence/session-03/pytest.xml`](session-03/pytest.xml)). | **Passed** |

---

## 4. Human vs. Agent Contributions (`A2`, `D1`)

- **Human Contributions:**
  - Created the separate `client-01-website` repository, initial scaffold commit (`15d7ce5`), stylesheet (`site/styles.css`), customer issue (`docs/issue-01-session-03.md`), and product check (`tests/test_website_s3.py`) (`yaw`, `saad`, `felix`).
  - Engineered the Factory's multi-repo customer delivery workflow ([`src/agents/customer_delivery_workflow.py`](../src/agents/customer_delivery_workflow.py)), workspace sandbox (`validate_product_workspace_path`), bounded retry loop (`max_correction_loops=2`), and Factory unit tests ([`tests/test_session_03_factory.py`](../tests/test_session_03_factory.py)) (`muhammad`, `minh`, `mirko`).
  - Fixed `/db/health` 503 exception redaction in [`src/app/main.py`](../src/app/main.py) (`muhammad`).
  - Executed the Human Gate review: rejected `WF-WEBSITE01-S3-001` (`muhammad`), visually inspected `site/index.html` and the `mailto:kontakt@nordwerk.example` link after `WF-WEBSITE01-S3-002`, and recorded explicit approval (`saad`).
- **Agent Contributions (`WF-WEBSITE01-S3-002`):**
  - `dev_architect_agent` (`software_architect`) read the customer issue and scaffold in `client-01-website` via `read_product_file_tool` and generated the `ProductHandoverPayload`.
  - `dev_architect_agent` (`backend_api_engineer`) consumed the `ProductHandoverPayload`, generated the German content fields via `qwen3:4b@359d7dd4bcda`, and wrote `site/index.html` (`5b9aefa`) via `write_product_file_tool`.
  - `qa-test-agent` (`qa_test_engineer`) consumed the `QAHandoverPayload`, ran `tests/test_website_s3.py` via `run_product_test_tool`, and summarized the passing test results.

---

## 5. Effort, Costs & Budget Plan (`C2`, `C3`)

Full cost details are recorded in [`costs/cost-model.yaml`](../costs/cost-model.yaml) and [`costs/usage.csv`](../costs/usage.csv):

| Category | Session 3 Actual | Credits | Budget Reference |
| :--- | :--- | :--- | :--- |
| **Human – Customer Delivery** | `1.00 h` (`yaw`, `saad`, `felix`) | `100.0000` | S3/S4 Delivery Budget (`631.0` credits total; S5 Reserve: `315.0` credits) |
| **Human – Review** | `0.50 h` (`saad`, `felix`) | `50.0000` | S3/S4 Delivery Budget |
| **Human – Rework** | `0.25 h` (`muhammad`) | `25.0000` | S3/S4 Delivery Budget |
| **Agent Runs (Approved `WF-WEBSITE01-S3-002`)** | `3 calls` (`212.47s`, `1618 in / 611 out` tokens) | `5.1814` | S3/S4 Delivery Budget |
| **Agent Runs (Discarded `WF-WEBSITE01-S3-001`)** | `3 calls` (`5.08s`, `1748 in / 571 out` tokens) | `3.1086` | S3/S4 Delivery Budget |
| **CI Runs** | `1 run` | `1.0000` | S3/S4 Delivery Budget |
| **Customer Delivery Subtotal (S3)** | | **`184.2900`** | **29.2% of S3/S4 Delivery Plan Budget (`631.0`) used** |
| **Human – Factory Development (Separate)** | `2.00 h` (`muhammad`, `minh`, `mirko`) | `200.0000` | Separate S3–S5 Factory Dev Budget (`400.0` credits) |
| **Session 3 Grand Total** | | **`384.2900`** | |

---

## 6. Bottleneck & Testable Improvement Hypothesis for S4/S5 (`C4`, `L3.4`)

- **Observed Bottleneck:** In [`runs/website-01/WF-WEBSITE01-S3-002/trace.jsonl`](../runs/website-01/WF-WEBSITE01-S3-002/trace.jsonl), the implementation step (`run_id=f94402cb-6d67-44e0-b4e9-410c8188f5b4`, role `backend_api_engineer` on local `qwen3:4b@359d7dd4bcda`) took **`100.8007s`** (47.4% of total workflow duration `212.47s`) and hit the output token ceiling (`output_tokens=384` == `llm_max_output_tokens`), because serializing the full `ProductHandoverPayload` into the prompt caused `qwen3:4b` to generate verbose output before completing JSON closure.
- **Testable Improvement Hypothesis (for Session 4):** Passing a compact prompt view of `ProductHandoverPayload` (only `required_content` and `target_product_file`) and evaluating the installed non-thinking local model `gemma4:e2b@b37049369adf` (with `json_mode=True`) will reduce implementation step runtime by **$\ge 40\%$** (target `< 60s` per step) and keep output tokens **`< 220` tokens** (avoiding truncation at `384` tokens) while maintaining `100%` pass rate on the expanded Session 4 acceptance criteria (`AC-01`–`AC-08`).

---

## 7. Next Actions for Session 4 (Max 3 Steps) (`D2`)

1. **Expand Website Content & Layout (`AC-02`–`AC-07`):** Extend `config/projects/website-01.yaml` and the implementation template to deliver all three services (`N-03`, `N-04`, `N-05`), target groups (`N-06`), working approach (`N-07`), anchor navigation (`AC-05`), responsive `375px`/`1280px` rules (`AC-06`), and keyboard focus/a11y metadata (`AC-07`).
2. **Expand Automated Product Checks (`AC-01`–`AC-08`):** Add tests in `client-01-website/tests/` covering navigation anchors, local asset resolution, responsive overflow rules, and `AC-03` forbidden-claim checks.
3. **Run Before/After Bottleneck Experiment (`C4`):** Measure runtime and output token counts on `WF-WEBSITE01-S4` comparing compact handover prompts and `qwen3:4b@359d7dd4bcda` vs. `gemma4:e2b@b37049369adf`.
