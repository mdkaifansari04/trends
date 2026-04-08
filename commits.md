# Commit Workflow (`commits.md`)

This file defines the default behavior when you say: **`commit`**.

## Default Behavior

When you say `commit`, the assistant should:

1. Collect the full working tree diff (`git status` + changed files).
2. Group changes into logical commit batches (not one giant commit), usually:
   - `docs/*` and markdown docs
   - migrations/database
   - backend/worker/API code
   - frontend/templates/static
   - tests
   - config/tooling
3. Generate clear conventional commit messages per batch.
4. Create commits non-interactively.
5. Return the final commit list and leave tree clean.

## Message Style

Use concise, descriptive conventional commits:

- `feat(scope): ...`
- `fix(scope): ...`
- `test(scope): ...`
- `docs(scope): ...`
- `chore(scope): ...`
- `refactor(scope): ...`

Examples:

- `feat(ingest): add bulk post upsert endpoint`
- `fix(worker): handle missing DB binding gracefully`
- `test(api): cover partial-success bulk ingest`

## No-Unnecessary-Questions Policy

For `commit` requests, do not ask extra questions unless:

- there is no git repository,
- there are merge conflicts,
- there are dangerous/destructive operations required,
- or the user explicitly asks for a different commit strategy.

## Permission Handling

If sandbox policy blocks git write operations, request **one** escalation and run the full commit batch in that approved flow.

Note: permission prompts are controlled by runtime policy and cannot be fully bypassed by repo files.

## Optional Commands

Inspect plan:

```bash
git status --short
git diff --stat
```

Show result:

```bash
git log --oneline --decorate -n 20
```
