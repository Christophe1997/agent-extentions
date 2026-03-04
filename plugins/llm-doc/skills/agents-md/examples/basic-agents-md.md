# Basic AGENTS.md Example

A complete, practical example for an e-commerce platform built with Next.js, PostgreSQL, and Redis.

## The File

```markdown
# AGENTS.md

## Project overview
E-commerce platform built with Next.js, PostgreSQL, and Redis.

## Setup commands
- Install deps: `pnpm install`
- Setup database: `pnpm db:setup`
- Start dev: `pnpm dev`
- Run tests: `pnpm test`
- Lint: `pnpm lint`

## Dev environment tips
- Use `pnpm dlx turbo run <task> --filter <package>` for monorepo tasks
- Check `.env.example` for required environment variables
- Database migrations go in `supabase/migrations/`

## Testing instructions
- Unit tests: `pnpm test`
- E2E tests: `pnpm test:e2e`
- Run specific test: `pnpm vitest run -t "test pattern"`
- Always run tests before committing
- Add tests for new features

## Code style
- TypeScript strict mode enabled
- Single quotes, no semicolons
- Functional components with hooks
- Colocate tests: `Component.test.tsx` next to `Component.tsx`

## PR instructions
- Title: `type(scope): description`
- Run `pnpm lint && pnpm test` before pushing
- Link issues: Fixes #123

## Security
- Never commit secrets or .env files
- Validate all API inputs with Zod
- Use Row Level Security in Supabase
```

## Key Elements Demonstrated

1. **Clear project overview** - One line describing the stack
2. **Actionable commands** - All commands can be copy-pasted and run
3. **Monorepo awareness** - Includes turbo commands for filtering packages
4. **Testing culture** - Emphasizes running and adding tests
5. **Code conventions** - Specific style rules (quotes, semicolons, colocation)
6. **PR workflow** - Commit conventions and pre-push checks
7. **Security reminders** - Critical security practices highlighted
