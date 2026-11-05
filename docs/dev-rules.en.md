# Development Rules (DF-HACK26)

## 1. Announce your work before you start

- If your work might overlap with someone else's, or you want to make clear who is working on it, open a GitHub issue and add yourself to Assignees. Each person decides whether to open one; small tweaks don't need an issue
- After opening an issue, post a short note on Discord, e.g. "Working on #12"
- Before touching files that belong to someone else's issue, contact that person first
- If you hit a conflict, **follow what is already in main** and fix it on your own branch

## 2. Branches and PRs

- Don't push directly to main. Always create a branch and open a PR
- Branch name: `type/issue-number-description`
  - Examples: `feat/12-login-page`, `fix/15-api-error`, `docs/3-dev-rules`
- One PR = one piece of work
- Write the PR description using the template in `.github/pull_request_template.md` (related issue and what you checked)
- Don't merge a PR that hasn't passed CI
- Ask one available person to review. If there is no response after half a day, you may merge with only a GitHub Copilot review
- Once approved, the PR author merges it. Merging to main deploys automatically

## 3. Code style

Leave formatting to the auto-formatters; we only decide names and comments ourselves. We will update this section once the backend framework is decided.

|  | Python (backend) | React / TypeScript (frontend) |
| --- | --- | --- |
| Formatting | PEP 8. Run `ruff format` and `ruff check` | Run Prettier and ESLint |
| File names | `snake_case.py` | Components: `PascalCase.tsx`, others: `camelCase.ts` |
| Functions / variables | `snake_case` | `camelCase` |
| Classes / components | `PascalCase` | `PascalCase` |
| Constants | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` |

- In comments, write why you wrote the code this way. Don't describe what the code already makes clear
- Comments, issues, and PRs can be in Japanese or English

## 4. What to check before opening a PR and after merging

Before opening a PR:

- [ ] The app starts locally without errors
- [ ] You manually checked the feature you changed, through the UI or the API
- [ ] You checked `git diff` and confirmed that no `.env` file or API keys are included

After merging (once the auto-deploy finishes):

- [ ] On the deployed URL, you manually went through the demo flow from start to finish. If anything is broken, fix it before any other work

## 5. Secrets and Google Cloud

- Don't put secrets such as API keys in the code. Only commit `.env.example` with empty values
- Keep the real values in Secret Manager, and members get them from there. Don't paste them in Discord
- Keep the credentials used by CI/CD in GitHub Secrets
- Before enabling a new Google Cloud service, ask on Discord first

## 6. Sharing progress and AI tools

- Every day, when you finish working, post a short note on Discord (what you did / what's next / anything blocking you)
