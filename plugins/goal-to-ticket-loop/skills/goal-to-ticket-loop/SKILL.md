---
name: goal-to-ticket-loop
description: This skill should be used when the user asks to "turn this goal into tickets and ship it", "run the goal-to-ticket loop", "decompose this goal and implement it unattended", or "hand this goal off and open PRs for each piece". Decomposes a goal into a tk ticket graph, then runs a self-pacing loop that implements, gates, commits, pushes, and opens a pull request for each ready ticket until the graph is exhausted.
argument-hint: "<goal description>"
allowed-tools: [Bash, Read, Write, Skill, AskUserQuestion]
---

## Process

<!-- TODO(U5): decomposition — size/ambiguity classification, inline tk create/tk dep, ce-plan/ce-brainstorm escalation, acceptance-criteria authoring. -->

<!-- TODO(U6): execution loop — preflight, reconciliation, ticket pick, implement, gate, branch/commit/push/PR, scope-creep handling, cap/stop checks, terminal summary. -->
