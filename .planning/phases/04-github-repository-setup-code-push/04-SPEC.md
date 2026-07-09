# Phase 4: GitHub Repository Setup & Code Push — Specification

**Created:** 2026-07-09
**Ambiguity score:** 0.183 (gate: ≤ 0.20)
**Requirements:** 5 locked

## Goal

Create a public GitHub repository named `youtube-video-downloader` using the user's GitHub token (scopes: repo + workflow), push the application code and planning artifacts to it, add README.md and an MIT LICENSE, configure a basic GitHub Actions CI workflow, and store the token as a GitHub Actions repository secret — without ever committing or logging the token.

## Background

The project is a complete, working YouTube Video Downloader (Flask + yt-dlp) with all 3 phases executed and committed to a local git repository on the `master` branch. There is no GitHub remote configured and no GitHub repository exists yet. The user wants the code published to GitHub so it can run on other machines (the `.exe` packaging from Phase 3's follow-up enables Windows distribution). The `.planning/` directory contains the GSD workflow artifacts (ROADMAP, STATE, specs, plans, summaries) which the user wants included in the repo for transparency. No secrets are currently present in the codebase.

## Requirements

1. **Repository creation**: A public GitHub repository `youtube-video-downloader` is created using the user's GitHub token (with `repo` + `workflow` scopes).
   - Current: No GitHub remote, no GitHub repository exists for this project
   - Target: A public repo `youtube-video-downloader` owned by the user's account exists on GitHub
   - Acceptance: `gh repo view <owner>/youtube-video-downloader` (or equivalent API call) returns the repo with `isPrivate: false`; the authenticated user is the owner or has admin

2. **Code + planning push**: The application code (app.py, templates/index.html, requirements.txt, requirements-build.txt, build.bat, youtube-downloader.spec, BUILD-EXE.md) and the `.planning/` directory are pushed to the repo's default branch, with caches/build artifacts excluded via `.gitignore`.
   - Current: Local `master` branch has all files committed; no remote
   - Target: Remote `origin` points to the new GitHub repo; `master` is pushed; `.gitignore` excludes `__pycache__/`, `*.exe`, temp files
   - Acceptance: `git ls-remote origin` shows `master`; `git ls-files` on the remote includes `app.py`, `templates/index.html`, `.planning/ROADMAP.md`; `git ls-files` does NOT include any `__pycache__/` or `*.exe`

3. **Documentation**: README.md and LICENSE (MIT) are added to the repository root.
   - Current: No README.md or LICENSE in the project
   - Target: README.md describes the app, install, run, and build-.exe steps; LICENSE is the MIT license text with the author/year
   - Acceptance: Both files exist at repo root; LICENSE contains the MIT license body; README.md references the `.exe` build path

4. **CI workflow**: A basic GitHub Actions workflow is added at `.github/workflows/ci.yml` that installs Python dependencies and runs a smoke test (app imports, route enumeration) on every push.
   - Current: No CI configuration exists
   - Target: `.github/workflows/ci.yml` runs on `push` with a job that sets up Python, `pip install -r requirements.txt`, and runs `python -c "from app import app; print(len(app.url_map._rules))"`
   - Acceptance: Workflow file is valid YAML and present; a manual `act`/API trigger or push shows the job completing (install + smoke test pass)

5. **Token as secret**: The user's GitHub token is stored as a GitHub Actions repository secret (e.g. `GH_TOKEN` or `GITHUB_TOKEN`), never committed to the repo or printed in logs.
   - Current: Token provided by user at execution time, not stored anywhere
   - Target: Repository secret exists; token is absent from all tracked files and CI logs
   - Acceptance: `gh secret list` shows the secret; `git grep -n "<token-value>"` over all tracked files returns no matches; the CI workflow does not echo the secret

## Boundaries

**In scope:**
- Create the public GitHub repository via the user's token
- Configure `origin` remote and push `master` (code + `.planning/`)
- Add/update `.gitignore` to exclude caches and build artifacts
- Write README.md (app description, run, build-.exe instructions)
- Write LICENSE (MIT)
- Write `.github/workflows/ci.yml` (install deps + smoke test)
- Store the token as a GitHub Actions repository secret

**Out of scope:**
- Dockerfile / containerization — deferred; user wants repo + CI only for now
- Release tagging / GitHub Releases / automated `.exe` publishing — separate backlog item
- Advanced CI (linting, coverage, multi-Python matrix beyond smoke test) — keep minimal
- Forking or transferring ownership to an org — personal account only
- Writing tests beyond the CI smoke test — not requested
- Storing the token in `.env` or any committed file — explicitly forbidden (see Prohibitions)

## Constraints

- Repository visibility MUST be **public** (user decision)
- Token MUST have `repo` + `workflow` scopes (required for repo creation and CI workflow file push)
- License MUST be **MIT**
- `.gitignore` MUST exclude `__pycache__/`, `*.exe`, and temp/download artifacts
- The token MUST NOT be committed, pushed, or echoed in any log
- Repo name MUST be exactly `youtube-video-downloader`
- Push strategy: create empty repo then push `master` (force if needed — user decision "Push normal")

## Acceptance Criteria

- [ ] A public GitHub repository `youtube-video-downloader` exists under the user's account
- [ ] `git remote -v` shows `origin` pointing to the new GitHub repo
- [ ] `master` branch is pushed to `origin` with code AND `.planning/` included
- [ ] `.gitignore` excludes `__pycache__/` and `*.exe`; no such files are tracked remotely
- [ ] README.md exists at repo root and documents install/run/build
- [ ] LICENSE (MIT) exists at repo root
- [ ] `.github/workflows/ci.yml` exists and is valid YAML
- [ ] CI workflow installs dependencies and passes the smoke test (app imports + route count)
- [ ] A GitHub Actions repository secret holds the user's token
- [ ] No tracked file contains the token value (`git grep` returns nothing)
- [ ] CI workflow does NOT echo/print the token

## Edge Coverage

**Coverage:** 7/7 applicable edges resolved · 0 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| idempotency | R1 | 🧪 backstop | Re-running creation force-recreates (user decision): detect existing repo, delete + recreate or update visibility to public |
| concurrency | R1 | ✅ covered | Single API call; re-runnable — if interrupted, re-run detects existing repo |
| concurrency | R2 | ✅ covered | `git push` is resumable; re-run pushes remaining commits; remote rejects only on divergence |
| unclassified | R3 | ✅ covered | README/LICENSE overwritten if present (generated files) |
| unclassified | R4 | ✅ covered | CI workflow file overwritten if present (our generated file) |
| idempotency | R5 | ✅ covered | Secret set via API; updating existing secret is idempotent (user decision: force recreate) |
| concurrency | R5 | ✅ covered | Single API call; re-runnable after interruption |

## Prohibitions (must-NOT)

**Coverage:** 3/3 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT create the repository as private — it MUST be public | R1 | resolved / test | `gh repo view` returns `isPrivate: false`; CI check asserts visibility field == "public" |
| MUST NOT commit, push, or stage the GitHub token in any tracked file | R5 | resolved / test | `git grep -n "<token>"` over all tracked files returns no matches; pre-push hook or CI guard runs `git ls-files \| xargs grep -l` for token pattern |
| MUST NOT echo or print the GitHub token in CI logs or console output | R4 | resolved / test | CI workflow does not use `echo $SECRET`, `printenv SECRET`, or `set -x` with the secret; CI guard greps step logs for the token value |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                              |
|--------------------|-------|------|--------|------------------------------------|
| Goal Clarity       | 0.85  | 0.75 | ✓      | Public repo + push + CI + secret   |
| Boundary Clarity   | 0.80  | 0.70 | ✓      | Explicit in/out scope list        |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Public, MIT, repo+workflow, exclude caches |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | 11 pass/fail criteria              |
| **Ambiguity**      | 0.183 | ≤0.20| ✓      |                                    |

## Interview Log

| Round | Perspective     | Question summary                        | Decision locked                    |
|-------|-----------------|-----------------------------------------|------------------------------------|
| 1     | Researcher      | Repo visibility / name / content        | Public, youtube-video-downloader, Code+planning |
| 2     | Simplifier      | Auth method / docs / gitignore          | Auto auth, README+LICENSE (MIT), exclude caches |
| 3     | Boundary Keeper | CI scope / token handling               | With CI (GitHub Actions), token as GitHub secret |
| 4     | Failure Analyst | Token scopes / push strategy            | repo+workflow scopes, push normal (force if needed) |
| 5     | Seed Closer     | Idempotency (R1/R5) / file overwrite    | Force recreate; overwrite if exists |
| 5     | Seed Closer     | Prohibitions + verification tier        | All 3 must-NOT; test tier checks |

---

*Phase: 04-github-repository-setup-code-push*
*Spec created: 2026-07-09*
*Next step: /gsd-discuss-phase 4 — implementation decisions (how to build what's specified above)*
