# Lesson 12 reference shelf

These are instructor references, not required reading during the CTF. The lesson
keeps framework-specific syntax behind adapters; the concepts and safety contract
are the durable content.

## Agent orchestration and durable state

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) —
  durable execution, stateful workflows, streaming, and human-in-the-loop.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) —
  checkpoints, fault tolerance, replay/time travel, and thread state.
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) —
  pausing a graph for approve/edit/reject decisions and resuming it later.

## Tool boundaries

- [Model Context Protocol architecture](https://modelcontextprotocol.io/docs/learn/architecture) —
  hosts, clients, servers, tools, resources, and prompts.
- [OpenAI Agents SDK guide](https://developers.openai.com/api/docs/guides/agents) —
  a useful comparison for agent loops, tools, handoffs, guardrails, sessions,
  approvals, and traces. Lesson 12 uses LangGraph because the explicit state
  machine is part of the teaching material, not because it is the only option.

## Observability and evaluation

- [LangSmith evaluation](https://docs.langchain.com/langsmith/evaluation) —
  offline and online evaluation from datasets and traces.
- [LangSmith evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts) —
  deterministic checks, human review, model judges, and trajectory evaluation.
- [OpenAI agent observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability#tracing) —
  tracing model calls, tools, guardrails, handoffs, and custom spans.

## Local implementation policy

- The six evaluation cases in `evals/` are the source of truth for this lesson's
  agent quality—not a hosted dashboard.
- The deterministic investigator is the classroom fallback and test oracle.
- A real-model run is optional and configured through environment variables.
- Retrieved runbook text is labeled guidance; it never counts as live evidence.
- No model or MCP client receives arbitrary shell, arbitrary SQL, or remediation
  authority.

