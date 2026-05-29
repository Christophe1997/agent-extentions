export const meta = {
  name: 'audit-plugins',
  description: 'Audit every plugin in plugins/ against repo conventions, adversarially verify flagged findings, and emit a prioritized health report',
  whenToUse: 'Before a release or after adding/editing plugins — checks README structure, skill/agent frontmatter, version sync, marketplace registration, and progressive-disclosure compliance across all plugins. Pass an array of plugin names as args to audit only a subset.',
  phases: [
    { title: 'Discover', detail: 'list plugin dirs (or take them from args)' },
    { title: 'Audit', detail: 'one agent per plugin scores it against the rubric' },
    { title: 'Verify', detail: 'adversarially refute flagged findings' },
    { title: 'Report', detail: 'synthesize a prioritized health report' },
  ],
}

// ─────────────────────────────────────────────────────────────────────────
// Rubric — grounded in this repo's own docs, so the audit measures THIS repo's
// conventions, not generic best practices:
//   • docs/agents/readme-template.md     → README structure & install format
//   • docs/agents/skill-patterns.md      → SKILL.md frontmatter & Process shape
//   • docs/agents/progressive-disclosure.md → lean bodies, references/, self-contained
//   • CLAUDE.md "Validation" checklist   → manifest fields & version sync
// ─────────────────────────────────────────────────────────────────────────
const RUBRIC = [
  'Score each dimension 0-5 (5 = fully compliant, 0 = absent/broken) and raise a finding for every gap.',
  '',
  'DIMENSION "readme" (docs/agents/readme-template.md):',
  '  - Sections present and in order: Features -> Examples (optional) -> Installation -> Usage -> License.',
  '  - Install line is exactly: /plugin install <plugin-name>@agent-extentions (no restart instructions).',
  '  - License section says MIT. Hooks shown as a table; Skills shown as a bullet list.',
  '',
  'DIMENSION "skills" (docs/agents/skill-patterns.md):',
  '  - Each skills/*/SKILL.md has YAML frontmatter: a name in short plugin-prefix form (e.g. a2a:send; bare for single-skill plugins and the directory-matching flagship) and a description with concrete trigger phrases.',
  '  - COMMAND/workflow skills (perform a task) have a "## Process" of numbered, **bold action-labelled** steps, and set argument-hint when they accept arguments.',
  '  - REFERENCE/knowledge skills (inform reasoning) are EXEMPT from "## Process" — do NOT flag its absence.',
  '  - "## Example Usage" is OPTIONAL and sequence-only: NEVER flag its absence. Flag it (low severity) ONLY when present but redundant — a single-shot echo of argument-hint that shows nothing the hint cannot.',
  '  - Script-like skills that need no LLM reasoning set disable-model-invocation: true.',
  '',
  'DIMENSION "manifest" (CLAUDE.md Validation):',
  '  - .claude-plugin/plugin.json has required fields: name, version, description.',
  '  - plugin.json version EQUALS the version registered for this plugin in the root .claude-plugin/marketplace.json.',
  '  - The plugin is registered in marketplace.json with source ./plugins/<name>, and linked from the root README.md.',
  '',
  'DIMENSION "progressiveDisclosure" (docs/agents/progressive-disclosure.md):',
  '  - SKILL.md bodies stay under ~2000 words; deep content lives in references/ or examples/.',
  '  - Plugin is self-contained: cross-plugin references avoided, or use full plugin-name:skill-name form when unavoidable.',
  '',
  'DIMENSION "agents" (CLAUDE.md Component Patterns) — only if agents/ exists, else score 5 with no findings:',
  '  - Each agents/*.md has a "When to Use" section with example queries, plus description/tools/model/color frontmatter.',
].join('\n')

// ─────────────────────────────── Schemas ────────────────────────────────
const DIMENSIONS = ['readme', 'skills', 'manifest', 'progressiveDisclosure', 'agents']

const DISCOVERY_SCHEMA = {
  type: 'object',
  required: ['plugins'],
  properties: {
    plugins: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name', 'path'],
        properties: {
          name: { type: 'string' },
          path: { type: 'string', description: 'repo-relative path, e.g. plugins/tdd' },
        },
      },
    },
  },
}

const AUDIT_SCHEMA = {
  type: 'object',
  required: ['plugin', 'scores', 'findings', 'summary'],
  properties: {
    plugin: { type: 'string' },
    scores: {
      type: 'object',
      required: DIMENSIONS,
      properties: Object.fromEntries(
        DIMENSIONS.map((d) => [d, { type: 'integer', minimum: 0, maximum: 5 }]),
      ),
    },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['dimension', 'severity', 'title', 'detail', 'suggestion'],
        properties: {
          dimension: { type: 'string', enum: DIMENSIONS },
          severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] },
          title: { type: 'string' },
          detail: { type: 'string', description: 'what is wrong and where' },
          file: { type: 'string', description: 'repo-relative path of the offending file' },
          suggestion: { type: 'string', description: 'concrete fix' },
        },
      },
    },
    summary: { type: 'string' },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['confirmed', 'reason'],
  properties: {
    confirmed: { type: 'boolean', description: 'true only if the issue was independently reproduced' },
    reason: { type: 'string' },
  },
}

// ─────────────────────────────── Prompts ────────────────────────────────
const auditPrompt = (p) =>
  [
    `Audit the Claude Code plugin "${p.name}" located at ${p.path}.`,
    '',
    'Read its files first — at minimum:',
    `  - ${p.path}/README.md`,
    `  - ${p.path}/.claude-plugin/plugin.json`,
    `  - ${p.path}/skills/*/SKILL.md (glob)`,
    `  - ${p.path}/agents/*.md (glob, if any)`,
    `  - ${p.path}/hooks/hooks.json and ${p.path}/.mcp.json (if present)`,
    'Then read the repo-root .claude-plugin/marketplace.json and README.md to check registration and version sync.',
    '',
    'Apply this rubric exactly:',
    RUBRIC,
    '',
    'Return a score per dimension and one finding per real gap. Cite the offending file in each finding. Do not invent issues; if a dimension is clean, score it 5 with no findings.',
  ].join('\n')

const verifyPrompt = (p, f) =>
  [
    `You are a skeptical reviewer. Try to REFUTE this audit finding about plugin "${p.name}".`,
    '',
    `Finding: ${f.title}`,
    `Dimension: ${f.dimension} | Severity: ${f.severity}`,
    `Claim: ${f.detail}`,
    `Cited file: ${f.file || '(none given)'}`,
    '',
    `Open the cited file (and any other file under ${p.path} you need) and check whether the issue is actually present.`,
    'Set confirmed=true ONLY if you independently reproduce the exact problem. If the file does not exist, the claim is vague, or the convention is actually satisfied, set confirmed=false. Default to confirmed=false when uncertain.',
  ].join('\n')

const reportPrompt = (scored) =>
  [
    'Write a concise Markdown audit report for this Claude Code plugin marketplace.',
    'Input is the per-plugin audit data (only verified findings are included):',
    '',
    JSON.stringify(scored, null, 2),
    '',
    'Structure:',
    '  1. "## Plugin Health" — a table: Plugin | Health % | Critical | High | Medium | Low (counts of findings by severity).',
    '  2. "## Findings by Severity" — list every finding ordered critical -> high -> medium -> low; for each show plugin, file, the problem, and the suggested fix.',
    '  3. "## Quick Wins" — the 3-5 lowest-effort fixes that most improve compliance.',
    'Sort the health table worst-first (lowest Health %). Be specific and cite files. No preamble.',
  ].join('\n')

// ─────────────────────────────────────────────────────────────────────────
// VERIFICATION GATE — decides which findings earn an expensive adversarial
// second opinion. Every finding that passes this predicate gets its own
// skeptic agent (verifyPrompt) that tries to refute it; findings that fail
// the gate are reported as-is (treated as confirmed). This is the cost/rigor
// dial for the whole workflow.
//
// `finding` shape: { dimension, severity ('critical'|'high'|'medium'|'low'),
//                    title, detail, file, suggestion }
// ─────────────────────────────────────────────────────────────────────────
function needsVerification(finding) {
  return (['readme', 'manifest'].includes(finding.dimension) && ['critical', 'high'].includes(finding.severity)) ||
  (['skills', 'agents', 'progressiveDisclosure'].includes(finding.dimension) && ['critical', 'high', 'medium'].includes(finding.severity))
}

// ─────────────────────────── Phase 1: discover ──────────────────────────
phase('Discover')
let plugins
if (Array.isArray(args) && args.length) {
  plugins = args.map((name) => ({ name, path: `plugins/${name}` }))
  log(`Auditing ${plugins.length} plugin(s) from args: ${plugins.map((p) => p.name).join(', ')}`)
} else {
  const disc = await agent(
    'List every immediate subdirectory of the plugins/ directory in this repo. Each subdirectory is one plugin. Return its name and repo-relative path (e.g. plugins/tdd).',
    { label: 'discover', phase: 'Discover', schema: DISCOVERY_SCHEMA },
  )
  plugins = disc.plugins || []
  log(`Discovered ${plugins.length} plugins: ${plugins.map((p) => p.name).join(', ')}`)
}

// ─────────────── Phases 2+3: audit each plugin, then verify ──────────────
// Pipelined: a plugin's findings get verified the moment its audit lands,
// while other plugins are still being read. No barrier between stages.
const audited = await pipeline(
  plugins,
  (p) => agent(auditPrompt(p), { label: `audit:${p.name}`, phase: 'Audit', schema: AUDIT_SCHEMA }),
  async (audit, p) => {
    if (!audit) return null
    const findings = audit.findings || []
    const toVerify = findings.filter(needsVerification)
    if (!toVerify.length) {
      return { ...audit, findings: findings.map((f) => ({ ...f, confirmed: true })) }
    }
    const verified = await parallel(
      toVerify.map((f) => () =>
        agent(verifyPrompt(p, f), {
          label: `verify:${p.name}:${f.dimension}`,
          phase: 'Verify',
          schema: VERDICT_SCHEMA,
        })
          .then((v) => ({ ...f, confirmed: v ? v.confirmed : true, verifyReason: v && v.reason }))
          // A failed/skipped verification keeps the finding (surface > hide for an audit).
          .catch(() => ({ ...f, confirmed: true, verifyReason: 'verification errored — reported unverified' })),
      ),
    )
    const passthrough = findings
      .filter((f) => !toVerify.includes(f))
      .map((f) => ({ ...f, confirmed: true }))
    return { ...audit, findings: [...verified, ...passthrough] }
  },
)

// ─────────────────────────── Phase 4: report ────────────────────────────
phase('Report')
const scored = audited
  .filter(Boolean)
  .map((a) => {
    const confirmed = (a.findings || []).filter((f) => f.confirmed)
    const s = a.scores || {}
    const vals = DIMENSIONS.map((d) => s[d] || 0)
    const healthScore = Math.round((vals.reduce((x, y) => x + y, 0) / (DIMENSIONS.length * 5)) * 100)
    return { plugin: a.plugin, healthScore, scores: a.scores, summary: a.summary, findings: confirmed }
  })
  .sort((a, b) => a.healthScore - b.healthScore)

const report = await agent(reportPrompt(scored), { label: 'synthesize', phase: 'Report' })

return { report, audits: scored, auditedPlugins: scored.map((a) => a.plugin) }
