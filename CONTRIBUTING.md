# Contributing

This is a personal infrastructure project. Contributions that improve the generic open-source base are welcome.

## What's in scope

- Bug fixes in the core bot, dashboard, memory system, or setup wizard
- Platform support improvements (macOS, WSL2, Docker)
- Documentation improvements
- New soul file templates

## What's not in scope

- Features that require personal data in the repo
- Vendor-specific integrations that belong in the user's personal overlay
- Sub-agent architectures (see the Future Extensions section in BUILD_PLAN.md)

## How to contribute

1. Fork the repo
2. Create a branch: `git checkout -b fix/your-description`
3. Make your change, test it on a fresh clone
4. Ensure `.gitignore` covers any new personal-data paths
5. Update `CHANGELOG.md` under `[Unreleased]`
6. Open a PR using the template

## Commit style

Plain English imperative: `Fix session resume on empty DB`, `Add macOS launchd plist`, `Document Cloudflare tunnel setup`.

No conventional-commit prefixes required, but fine if you use them.

## No personal data in PRs

Before opening a PR, verify:
- No tokens, user IDs, or real names in committed files
- No `*.personal.md` files staged
- No `workspaces/` content staged

`git status` and `git diff --cached` are your friends.
