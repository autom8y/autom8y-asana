# Tool Selection

**Default**: Use Claude Code native tools for file operations. Use shell CLI for git, GitHub, and project commands.

## Decision Tree

```
File operation (read/write/search/find)?
├─ YES: Use native tool (Read, Write, Edit, Grep, Glob)
└─ NO: Git/GitHub operation?
       ├─ GitHub (PRs, issues): Use `gh` CLI via Bash
       └─ Git (status, diff, commit): Use git commands via Bash

Directory structure visualization?
├─ YES: Use `eza --tree --git-ignore` via Bash
└─ NO: Project command (test, build, dev)?
       ├─ YES: Use `just` or `make` via Bash (prefer `just`)
       └─ NO: Default to native tool if available
```

## Quick Reference

| Task | Use This | NOT This |
|------|----------|----------|
| Search file contents | `Grep` tool | `rg`, `grep` commands |
| Find files by pattern | `Glob` tool | `fd`, `find` commands |
| Read file contents | `Read` tool | `cat`, `bat`, `head`, `tail` |
| Edit files | `Edit` tool | `sed`, `awk` |
| Write files | `Write` tool | `echo >`, heredocs |
| Directory tree | `eza --tree` via Bash | `tree` command |
| Git operations | `git` via Bash | (no native equivalent) |
| GitHub operations | `gh` via Bash | (no native equivalent) |
| Run tests | `make test` via Bash | (no native equivalent) |

## Hard Rules

1. **Never use interactive tools** - `fzf` picker, `zi` directory picker cannot receive agent input
2. **Always use Read for files** - handles text, images, PDFs; context-optimized
3. **Always use Grep for search** - structured output, respects sandboxing
4. **Always use Glob for finding** - faster than shell, integrated results
5. **Always use Edit/Write for changes** - atomic, integrated, safer

## Shell Tools Worth Using

| Tool | When | Example |
|------|------|---------|
| `eza --tree` | Visualize directory structure | `eza --tree --level=3 --git-ignore` |
| `gh` | GitHub PR/issue operations | `gh pr list`, `gh pr create` |
| `git` | All version control | `git status`, `git diff`, `git commit` |
| `just` | Project commands (preferred) | `just test`, `just dev`, `just lint` |
| `make` | Project commands (legacy) | `make test`, `make dev`, `make lint` |

For additional shell patterns, see the `justfile` skill.

## Task Runner Selection

| Runner | When to Use |
|--------|-------------|
| `just` | New projects, complex workflows, multi-file organization |
| `make` | Existing projects with Makefile, simple needs |
| `npm scripts` | JavaScript/Node.js projects |
| Shell scripts | One-off automation, complex logic (> 10 lines) |

**Decision**: For new Python/Go projects, prefer `just` with modular organization. See [justfile skill](../../templates/justfile/INDEX.lego.md).

## Development Commands

**Preferred**: Use `just` for task automation. See [justfile skill](../../templates/justfile/INDEX.lego.md) for patterns.

```bash
just test              # Run tests
just test:unit         # Run unit tests only
just dev               # Start development
just lint              # Run linter
just ci                # Run full CI pipeline locally
```

**Legacy/Alternative**: Some projects use `make`:

```bash
make test              # Run tests
make test FILE=path    # Run specific test
make dev               # Start development
make lint              # Run linter
make coverage          # Generate coverage
```

## Shell Tools Availability

The shell environment follows a three-tier tool availability model:

### Tier 1: Integrated Tools (Aliased in .zshrc)

- **eza** (`ls`, `ll`, `tree`) - Modern ls replacement with git integration
- **bat** (`cat`) - Syntax-highlighted file viewer
- **fd** - Fast find alternative (used by fzf)
- **zoxide** (`z`, `zi`) - Smart directory jumping
- **fzf** (`Ctrl+R`, `Ctrl+T`, `Alt+C`) - Fuzzy finder

### Tier 2: Available Tools (Installed, Not Aliased)

- **jq** - JSON query and transformation (`jq '.field' file.json`)
- **yq** - YAML query and transformation (`yq '.field' file.yaml`)
- **ripgrep** (`rg`) - Fast text search
- **mise** - Polyglot version manager
- **direnv** - Auto-load project environments
- **gh** - GitHub CLI

### Tier 3: On-Demand Tools (Install When Needed)

- **httpie/curlie** - Modern HTTP clients for API exploration
- **tokei** - Code statistics and language breakdown
- **difftastic** - Syntax-aware diffs
- **hyperfine** - Command benchmarking

### Decision Framework

**Add to Tier 1 if:** Used daily, improves core workflow, worth muscle memory investment

**Add to Tier 2 if:** Used weekly or occasionally, fills capability gap, low integration cost

**Keep in Tier 3 if:** Used rarely, solves specific problem, can install quickly when needed
