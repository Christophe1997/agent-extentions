# Migration Example: AGENT.md to AGENTS.md

This example demonstrates migrating a verbose AGENT.md file to a lean AGENTS.md using progressive disclosure.

## Before: AGENT.md (Verbose, 156 lines)

```markdown
# AGENT.md

## Project Overview

This is an e-commerce platform built with Next.js 14, PostgreSQL, and Redis. The platform supports multiple vendors, real-time inventory management, and integrates with Stripe for payments. We use Supabase for authentication and database, and Vercel for deployment.

The architecture follows a microservices pattern with:
- Frontend: Next.js 14 with App Router
- API: Next.js API routes + tRPC
- Database: PostgreSQL via Supabase
- Cache: Redis for sessions and cart
- Queue: BullMQ for background jobs
- Storage: S3 for images
- Email: Resend for notifications

## Environment Setup

### Prerequisites
- Node.js 20.x or higher
- pnpm 8.x or higher
- Docker Desktop (for local services)
- Supabase CLI
- Vercel CLI (for deployment)

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/org/ecommerce-platform.git
   cd ecommerce-platform
   ```

2. Install dependencies:
   ```bash
   pnpm install
   ```

3. Set up environment variables:
   Copy `.env.example` to `.env.local` and fill in the values:
   - `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase project URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Supabase anonymous key
   - `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
   - `STRIPE_SECRET_KEY`: Stripe API secret
   - `REDIS_URL`: Redis connection string
   - `AWS_ACCESS_KEY_ID`: AWS access key
   - `AWS_SECRET_ACCESS_KEY`: AWS secret key
   - `RESEND_API_KEY`: Resend API key

4. Start local services:
   ```bash
   pnpm services:start
   ```
   This starts PostgreSQL, Redis, and MinIO (S3 compatible) in Docker.

5. Run database migrations:
   ```bash
   pnpm db:migrate
   ```

6. Seed the database (optional):
   ```bash
   pnpm db:seed
   ```

### Development Commands

- Start development server: `pnpm dev`
- Start with Turbopack: `pnpm dev:turbo`
- Open specific port: `pnpm dev --port 3001`

The development server runs on http://localhost:3000 by default.

### Build Commands

- Build for production: `pnpm build`
- Build specific package: `pnpm turbo run build --filter @org/package-name`
- Analyze bundle: `pnpm build:analyze`

## Testing Strategy

### Unit Tests
We use Vitest for unit testing with React Testing Library for components.

Run unit tests:
```bash
pnpm test
```

Run in watch mode:
```bash
pnpm test:watch
```

Run with coverage:
```bash
pnpm test:coverage
```

Coverage thresholds:
- Statements: 80%
- Branches: 75%
- Functions: 80%
- Lines: 80%

### E2E Tests
We use Playwright for end-to-end testing.

Run E2E tests:
```bash
pnpm test:e2e
```

Run specific test:
```bash
pnpm playwright test -g "checkout flow"
```

Debug tests:
```bash
pnpm playwright test --ui
```

### Test Writing Guidelines

When writing tests:
1. **Colocate tests**: Place `Component.test.tsx` next to `Component.tsx`
2. **Test behavior, not implementation**: Focus on user interactions
3. **Use testing-library**: Prefer `getByRole`, `getByText` over test IDs
4. **Mock external dependencies**: Mock API calls, third-party services
5. **Test edge cases**: Empty states, error states, loading states
6. **Keep tests isolated**: Each test should be independent
7. **Use descriptive names**: Test names should describe the scenario
8. **Follow AAA pattern**: Arrange, Act, Assert

Example test structure:
```typescript
describe('ProductCard', () => {
  it('should display product name and price', () => {
    // Arrange
    const product = { id: 1, name: 'Widget', price: 9.99 };

    // Act
    render(<ProductCard product={product} />);

    // Assert
    expect(screen.getByText('Widget')).toBeInTheDocument();
    expect(screen.getByText('$9.99')).toBeInTheDocument();
  });
});
```

## Code Style Guidelines

### TypeScript
- Use TypeScript strict mode (enabled in tsconfig.json)
- Avoid `any` type - use `unknown` and type guards instead
- Prefer interfaces over types for object shapes
- Use const assertions for literal types
- Document complex types with JSDoc comments

### React
- Use functional components with hooks
- Follow the Rules of Hooks
- Use custom hooks for reusable logic
- Keep components small and focused (< 150 lines)
- Use React.memo sparingly, only when needed

### Code Formatting
- Single quotes for strings (Prettier enforced)
- No semicolons (Prettier enforced)
- Max line length: 100 characters
- 2-space indentation
- Trailing commas in multiline (ES5)

### Naming Conventions
- **Components**: PascalCase (`ProductCard.tsx`)
- **Utilities**: camelCase (`formatPrice.ts`)
- **Constants**: SCREAMING_SNAKE_CASE (`MAX_RETRIES`)
- **Files**: Match the primary export (`ProductCard.tsx` exports `ProductCard`)
- **Test files**: `.test.tsx` suffix (`ProductCard.test.tsx`)

### Import Organization
Imports should be organized in this order:
1. React imports
2. Third-party libraries
3. Internal aliases (`@/`)
4. Relative imports

Example:
```typescript
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';

import { Button } from '@/components/ui/Button';
import { useCart } from '@/hooks/useCart';

import { ProductImage } from './ProductImage';
```

### Git Commit Guidelines

We follow Conventional Commits specification:

**Format**: `type(scope): subject`

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, semicolons)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(cart): add quantity adjustment
fix(auth): resolve session timeout issue
docs(readme): update installation steps
test(product): add edge case tests
```

**Rules**:
- Use imperative mood ("add feature" not "added feature")
- No period at the end
- Lowercase subject
- Body (optional) should explain what and why, not how

### Pull Request Process

1. **Before creating PR**:
   - Run `pnpm lint && pnpm test`
   - Ensure build passes: `pnpm build`
   - Update tests for changed code
   - Update documentation if needed

2. **PR title**: Use Conventional Commits format
   - Example: `feat(cart): add quantity adjustment`

3. **PR description** should include:
   - What changes were made
   - Why they were needed
   - How to test them
   - Any breaking changes

4. **Link issues**:
   - Use keywords: "Fixes #123", "Closes #456"

5. **Review process**:
   - At least 1 approval required
   - CI must pass
   - No merge conflicts

## Security Guidelines

### Never Commit Secrets
- Never commit `.env` files
- Use `.env.example` for documentation only
- Store secrets in Vercel environment variables
- Use Supabase secrets management for API keys

### Input Validation
- Validate all user inputs with Zod schemas
- Sanitize HTML content
- Use parameterized queries (Supabase handles this)
- Validate file uploads (type, size)

### Authentication & Authorization
- Use Supabase Auth for authentication
- Implement Row Level Security (RLS) in Supabase
- Check permissions on API routes
- Never trust client-side checks alone

### API Security
- Rate limit API endpoints
- Use CSRF protection
- Set secure cookie flags
- Validate redirect URLs

### Dependencies
- Run `pnpm audit` regularly
- Update dependencies promptly
- Review security advisories
- Pin dependency versions

## Deployment

### Staging Deployment
Staging is automatically deployed on every push to `main` branch.

Access staging at: https://staging.ecommerce-platform.com

### Production Deployment
Production is deployed on release tags:
```bash
git tag v1.2.3
git push origin v1.2.3
```

### Deployment Checklist
- [ ] All tests passing
- [ ] No TypeScript errors
- [ ] Lighthouse score > 90
- [ ] Security audit clean
- [ ] Environment variables set
- [ ] Database migrations run
- [ ] CDN cache invalidated

## Troubleshooting

### Common Issues

**Issue**: `pnpm install` fails with permission errors
**Solution**: Run `sudo chown -R $(whoami) ~/.pnpm-store`

**Issue**: Database connection errors
**Solution**: Check if Docker containers are running: `pnpm services:start`

**Issue**: Build fails with out-of-memory
**Solution**: Increase Node memory: `NODE_OPTIONS="--max-old-space-size=4096" pnpm build`

**Issue**: Tests fail with timeout
**Solution**: Increase test timeout: `pnpm test --timeout 10000`

### Getting Help
- Check existing issues on GitHub
- Ask in #engineering Slack channel
- Review documentation in `/docs`
```

## After: AGENTS.md (Lean, 68 lines with progressive disclosure)

```markdown
# AGENTS.md

## Project overview
E-commerce platform: Next.js 14, PostgreSQL, Redis, Stripe.
See docs/agents/architecture.md for detailed system design.

## Setup commands
- Install: `pnpm install`
- Start services: `pnpm services:start`
- Run migrations: `pnpm db:migrate`
- Dev server: `pnpm dev`
- Build: `pnpm build`

See docs/agents/setup.md for detailed installation steps.

## Testing instructions
- Unit tests: `pnpm test`
- E2E tests: `pnpm test:e2e`
- Coverage: `pnpm test:coverage`
- Run specific: `pnpm vitest run -t "pattern"`

See docs/agents/testing.md for detailed guidelines and conventions.

## Code style
- TypeScript strict mode
- Single quotes, no semicolons
- Functional components with hooks

See docs/agents/code-style.md for detailed conventions.

## PR instructions
- Use Conventional Commits (see llm-doc:commit-message skill)
- Run `pnpm lint && pnpm test` before pushing
- Reference issues: Fixes #123

See docs/agents/workflow.md for detailed PR process.

## Security
- Never commit .env files
- Validate inputs with Zod
- Use Row Level Security in Supabase

See docs/agents/security.md for detailed security guidelines.

## Deployment
- Staging: auto-deploy on `main` push
- Production: deploy on git tags

See docs/agents/deployment.md for detailed deployment process.

## Troubleshooting
See docs/agents/troubleshooting.md for common issues and solutions.
```

## Created Reference Files

### docs/agents/architecture.md
```markdown
# Architecture Overview

## System Design

The platform follows a microservices pattern:

- **Frontend**: Next.js 14 with App Router
- **API**: Next.js API routes + tRPC
- **Database**: PostgreSQL via Supabase
- **Cache**: Redis for sessions and cart
- **Queue**: BullMQ for background jobs
- **Storage**: S3 for images
- **Email**: Resend for notifications

## Data Flow

[Detailed architecture diagrams and data flow explanations...]
```

### docs/agents/setup.md
```markdown
# Environment Setup

## Prerequisites
- Node.js 20.x or higher
- pnpm 8.x or higher
- Docker Desktop (for local services)
- Supabase CLI
- Vercel CLI (for deployment)

## Installation Steps

[Detailed installation steps from original AGENT.md...]
```

### docs/agents/testing.md
```markdown
# Testing Guidelines

## Test Types

### Unit Tests
We use Vitest for unit testing with React Testing Library.

[All testing details from original AGENT.md...]

## Test Writing Guidelines

[All test writing best practices from original AGENT.md...]

## Examples

[Example test code from original AGENT.md...]
```

### docs/agents/code-style.md
```markdown
# Code Style Guidelines

## TypeScript
- Use TypeScript strict mode (enabled in tsconfig.json)
- Avoid `any` type - use `unknown` and type guards instead
- Prefer interfaces over types for object shapes
[All TypeScript conventions from original AGENT.md...]

## React
[All React conventions from original AGENT.md...]

## Code Formatting
[All formatting rules from original AGENT.md...]

## Naming Conventions
[All naming conventions from original AGENT.md...]

## Import Organization
[Import organization examples from original AGENT.md...]
```

### docs/agents/workflow.md, docs/agents/security.md, docs/agents/deployment.md, docs/agents/troubleshooting.md
[Similar extraction of detailed content from original AGENT.md...]
```

## Migration Summary

| Aspect | Before (AGENT.md) | After (AGENTS.md + refs) |
|--------|------------------|-------------------------|
| **Total lines** | 156 lines in 1 file | 68 lines in AGENTS.md + 8 reference files |
| **File count** | 1 file | 9 files |
| **AGENTS.md focus** | Everything mixed | Essential commands & references only |
| **Detailed content** | Inline (verbose) | Extracted to dedicated docs |
| **Progressive disclosure** | None | Applied throughout |
| **Maintainability** | Hard to scan | Easy to scan, detailed docs separate |
| **Agent efficiency** | High context usage | Loads only what's needed |

## Benefits of Progressive Disclosure

1. **Faster scanning**: AGENTS.md is now 68 lines instead of 156
2. **On-demand loading**: Agents load detailed docs only when needed
3. **Better organization**: Related content grouped in dedicated files
4. **Easier maintenance**: Update one section without touching others
5. **Reduced context bloat**: Less token usage for routine tasks
6. **Flexible depth**: Quick reference or deep dive as needed

## Validation Checklist

After migration, verify:

- [x] All commands present and executable
- [x] Progressive disclosure applied to verbose sections
- [x] All original content preserved (nothing lost)
- [x] AGENTS.md under 100 lines
- [x] Reference files created for extracted content
- [x] Cross-references work (links to docs/agents/*)
- [x] Format follows skill best practices
- [x] Symlink created: `AGENT.md -> AGENTS.md`
