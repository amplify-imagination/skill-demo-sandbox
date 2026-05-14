---
name: watch-ci
description: Check the latest GitHub Actions run on this repo. If failed, find the cause, draft a one-commit patch on a fix branch, open a PR, then stop. Never auto-merge.
triggers:
  - "watch ci"
  - "check ci"
  - "check the build"
  - "any builds failing"
  - "is the build green"
tools:
  - bash (gh CLI, git)
  - read_file
  - write_file
---

# watch-ci

Monitor the GitHub Actions workflow status for this repository. If something
broke, draft a candidate fix and surface it as a PR for human review.

## Pre-conditions

- The current working directory is a git clone of the target repo.
- `gh` CLI is authenticated with `repo` + `workflow` scopes.
- The default branch is `main`.

## Steps

1. **Fetch the latest workflow run on main:**

   ```bash
   gh run list --branch main --limit 1 --json databaseId,status,conclusion,headSha,workflowName,displayTitle
   ```

2. **If `conclusion == "success"`:** log `{timestamp} green | nothing to do` to
   `skills/watch-ci/log.txt` and exit cleanly. Do nothing else.

3. **If `conclusion == "failure"`:**

   a. Check whether an auto-fix PR already exists for this commit SHA:

      ```bash
      gh pr list --search "head:fix/ci-<sha-prefix>" --state open --json number,title
      ```

      If one exists, log `{timestamp} failed | PR #N already open` and exit.
      Don'''t open a duplicate.

   b. Get the failed run'''s logs to identify the cause:

      ```bash
      gh run view <runId> --log-failed | head -200
      ```

      Parse for the first `Error`, `Failed`, or non-zero exit. Summarize the
      likely cause in one sentence.

   c. **Draft a one-commit patch** on a fresh branch:

      - Branch name: `fix/ci-<sha-prefix>-<short-cause-slug>`
      - Make the minimum change you believe will turn the build green
      - Commit message: `fix(ci): <one-line summary>` + body `auto-drafted by /watch-ci`

   d. **Push the branch + open a PR:**

      ```bash
      git push origin <branch-name>
      gh pr create \
        --base main \
        --head <branch-name> \
        --title "fix(ci): <one-line summary>" \
        --body "<analysis> Auto-drafted by /watch-ci. Review carefully before merging." \
        --label "auto-fix"
      ```

   e. **STOP.** Do not merge. A human reviews and merges.

   f. Log `{timestamp} failed | drafted PR #N` to `skills/watch-ci/log.txt`.

## Out of scope

- Never push directly to main.
- Never auto-merge a PR — even if tests pass.
- Never modify history (no rebase / force-push).
- Don'''t touch files outside the offending area. Smallest possible patch.

## Safety

If the failure cause is unclear after reading 200 lines of logs, log
`{timestamp} failed | cause unclear | skipped` and exit. Better to alert a
human than to push speculative fixes.

## How to call this skill

- Manually: `/watch-ci` in a Claude session inside the repo clone.
- Looped: add a scheduled task that runs `/watch-ci` every 5 minutes (or hour).
