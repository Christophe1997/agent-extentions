# AGENTS.md Validation Checklist

Comprehensive validation checklist for ensuring AGENTS.md quality after creation, migration, or update.

## Quick Validation (Essential)

After any change, verify these critical items:

- [ ] All commands are executable (test them)
- [ ] File is concise (ideally 50-80 lines, max 100)
- [ ] No placeholder content (e.g., "TODO")
- [ ] Essential commands remain inline
- [ ] References folder only created if user explicitly wanted it

## Structure Validation

- [ ] File exists at expected location
- [ ] Uses standard Markdown format
- [ ] Has clear section headers
- [ ] Sections logically organized
- [ ] Consistent formatting throughout

## Content Validation

### Commands
- [ ] All commands are executable (test them)
- [ ] Commands are copy-pasteable
- [ ] No hardcoded paths that won't work universally
- [ ] Package manager commands match project (npm/pnpm/yarn)

### Information
- [ ] Project overview is accurate
- [ ] Setup instructions work from scratch
- [ ] Test commands actually run tests
- [ ] Build commands produce builds
- [ ] No sensitive information exposed

### Completeness
- [ ] Includes recommended sections (or intentionally omits)
- [ ] No placeholder content (e.g., "TODO", "TBD")
- [ ] All referenced files exist
- [ ] No broken links or references

## Progressive Disclosure Validation

**Default**: Single compact AGENTS.md file. Only create references folder if explicitly needed.

- [ ] File is concise (ideally 50-80 lines, max 100)
- [ ] Essential commands remain inline
- [ ] No section longer than ~10 lines of details
- [ ] References folder only exists if user wanted it
- [ ] If references exist: all referenced files exist and are accessible

### When to Use References

**Single file is enough** (default):
- Most projects
- Standard conventions
- Simple build/test commands

**References folder needed** (ask user):
- Complex project-specific patterns
- Detailed architecture documentation
- Extensive tutorials and examples
- Content exceeds 80 lines and cannot be condensed

### Content Placement

**Keep inline** (in AGENTS.md):
- Essential commands (install, test, build)
- Critical conventions (quotes, semicolons, etc.)
- Security requirements (brief reminders)
- Brief project overview (1-2 sentences)

**Move to references** (only if references folder created):
- Detailed architecture explanations
- Extensive code examples (>5 lines)
- Long-form documentation (>10 lines per section)
- Step-by-step tutorials
- Historical context

## Quality Validation

- [ ] Follows best practices from skill
- [ ] Commands are copy-pasteable
- [ ] Style is consistent throughout
- [ ] No sensitive information exposed
- [ ] Uses imperative form consistently
- [ ] Clear section headers

## Reference Files Validation

**Only validate if references folder was created** (user explicitly wanted it):

- [ ] Reference directory created (default: docs/agents/)
- [ ] All referenced files exist
- [ ] References use relative paths
- [ ] Reference content is complete (no placeholders)
- [ ] Cross-references between files work

**If no references folder**: This is the default and expected for most projects.

## Post-Migration Validation

After migrating from other formats:

- [ ] All original content preserved (nothing lost)
- [ ] Content properly mapped to AGENTS.md sections
- [ ] Format follows skill best practices
- [ ] Symlink created for backward compatibility (if requested)
- [ ] Original file handled correctly (deleted, kept, or symlinked)

## Post-Update Validation

After updating existing AGENTS.md:

- [ ] All commands still current and executable
- [ ] No information lost during update
- [ ] Changes align with project state
- [ ] File remains concise
- [ ] Progressive disclosure maintained

## Agent Compatibility Validation

- [ ] Works with target AI agents
- [ ] Symlinks created correctly (if applicable)
- [ ] No agent-specific syntax that breaks others

## Final Checks

- [ ] File renders correctly in Markdown viewers
- [ ] No spelling or grammar errors
- [ ] Consistent terminology throughout
- [ ] Date/version information current (if included)
- [ ] Contact information accurate (if included)
