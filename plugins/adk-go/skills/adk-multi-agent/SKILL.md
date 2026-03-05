---
name: adk-multi-agent
description: ADK-Go multi-agent patterns including sequential pipelines, parallel fan-out, loop agents for iterative refinement, and agent handoffs. Use when building complex agent workflows, orchestrating multiple agents, or implementing retry/refinement loops. Triggers on queries about "sequential agent", "parallel agent", "loop agent", "multi-agent", "agent workflow", "agent handoff", "pipeline".
---

# ADK-Go Multi-Agent Patterns

Compose multiple agents into sophisticated workflows.

## Package Map

| Package | Purpose |
|---|---|
| `google.golang.org/adk/agent` | Base agent interface |
| `google.golang.org/adk/agent/llmagent` | LLM-backed agents |
| `google.golang.org/adk/agent/sequentialagent` | Sequential pipeline |
| `google.golang.org/adk/agent/parallelagent` | Parallel fan-out |
| `google.golang.org/adk/agent/loopagent` | Iterative refinement |

## Sequential Pipeline

Execute agents in sequence, passing output from one to the next:

```go
import "google.golang.org/adk/agent/sequentialagent"

pipeline, _ := sequentialagent.New(sequentialagent.Config{
    Name:       "content_pipeline",
    SubAgents:  []agent.Agent{researchAgent, draftAgent, editAgent, publishAgent},
})
```

**Use cases:**
- Content generation (research → draft → edit → publish)
- Data processing (extract → transform → load)
- Code review (analyze → suggest → apply)

## Parallel Fan-Out

Execute multiple agents concurrently:

```go
import "google.golang.org/adk/agent/parallelagent"

fanout, _ := parallelagent.New(parallelagent.Config{
    Name:      "analysis_fanout",
    SubAgents: []agent.Agent{securityAgent, performanceAgent, styleAgent},
})
```

**Context isolation:** Each sub-agent gets its own Branch in the context. Branch format: `"parent.child"`.

**Use cases:**
- Multi-perspective analysis (security, performance, style)
- Independent data processing
- A/B testing different approaches

## Loop Agent (Iterative Refinement)

Run an agent repeatedly until a condition is met or max iterations reached:

```go
import "google.golang.org/adk/agent/loopagent"

loop, _ := loopagent.New(loopagent.Config{
    Name:     "refinement_loop",
    SubAgent: refinementAgent,
    MaxIter:  5,
})
```

**Use cases:**
- Code refinement until tests pass
- Content improvement with quality checks
- Retry with exponential backoff

## Agent Handoff

Agents can transfer control to other agents via the auto-generated `agent_transfer` tool:

```go
// When sub-agents are registered, ADK auto-generates transfer tools
// The LLM calls agent_transfer to delegate to a specific sub-agent

specialistAgent, _ := llmagent.New(llmagent.Config{
    Name:        "sql_specialist",
    Model:       model,
    Description: "Handles SQL query generation and optimization",
    Instruction: "You are a SQL expert. Generate optimized queries.",
})

coordinatorAgent, _ := llmagent.New(llmagent.Config{
    Name:        "coordinator",
    Model:       model,
    Description: "Routes requests to appropriate specialists",
    Instruction: "You coordinate between specialists. Transfer to sql_specialist for SQL tasks.",
    SubAgents:   []agent.Agent{specialistAgent},
})
```

## Composing Patterns

Combine patterns for complex workflows:

```go
// Sequential pipeline with parallel analysis stage
researchAgent, _ := llmagent.New(llmagent.Config{...})
analysisFanout, _ := parallelagent.New(parallelagent.Config{
    SubAgents: []agent.Agent{securityAgent, performanceAgent},
})
summaryAgent, _ := llmagent.New(llmagent.Config{...})

fullPipeline, _ := sequentialagent.New(sequentialagent.Config{
    SubAgents: []agent.Agent{researchAgent, analysisFanout, summaryAgent},
})
```

## Best Practices

### Clear Responsibilities
Each agent should have a single, well-defined responsibility:

```go
// Good: Focused responsibility
extractAgent := llmagent.Config{
    Name:        "extract",
    Instruction: "Extract key entities from text. Output JSON only.",
}

// Avoid: Overly broad responsibility
doEverythingAgent := llmagent.Config{
    Name:        "everything",
    Instruction: "Analyze, extract, transform, and summarize everything.",
}
```

### Explicit Handoff Instructions
Tell the coordinator when to transfer:

```go
coordinator := llmagent.Config{
    Instruction: `You are a coordinator.
- Transfer to sql_specialist for database queries
- Transfer to api_specialist for API calls
- Handle general questions yourself`,
}
```

### State Sharing Between Agents
Use session state to pass data:

```go
// First agent writes to state
firstAgent := llmagent.Config{
    OutputKey: "analysis_result",  // Auto-stores final response
}

// Second agent reads from state
secondAgent := llmagent.Config{
    Instruction: "Process the previous analysis: {analysis_result}",
}
```

## See Also

- [adk-basics](../adk-basics) - Core agent setup
- [adk-callbacks](../adk-callbacks) - Callbacks between agent stages
