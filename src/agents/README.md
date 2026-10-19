# Team-owned agents

Implement the company's actual agents in this directory.

The supplied reference workflow under `examples/` is intentionally excluded from assessment evidence.

A project agent should eventually make clear:

- role / responsibility,
- accepted task input,
- state schema,
- tools and permissions,
- structured output,
- failure behaviour,
- trace evidence,
- accountable human,
- cost evidence.

## Termin 2: Operations & Observability (`ops-agent`)

- Entry point: `python -m src.agents.ops_agent run --mode devops --task-id OPS-001`
- Costs: `python -m src.agents.ops_agent run --mode observability --task-id OPS-002 --observed-task-id SESSION-01-QA`
- Human approval: `python -m src.agents.ops_agent review --report reports/ops/<run_id>.json --reviewer Mirko --decision changes_requested`
- Details and limitations: [`docs/OPS_AGENT.md`](../../docs/OPS_AGENT.md).
