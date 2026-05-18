# Plan: Worktree-Volume Dev Env Mode

## Context

`dda env dev` today only supports bind-mounting host checkouts of `../{repo}` into the dev container. This is brittle for several common workflows: working on multiple branches of the same repo, working on private/EMU repos that aren't checked out locally, and onboarding a new machine where every repo must be cloned by hand first. This plan replaces the deprecated `--clone` flag with a **worktree-volume** model where `dda` maintains a shared bare clone per `(org, repo)` on the host and provisions per-env Docker volumes containing git worktrees rooted in those bare repos. Bind-mount remains as a documented fallback. Multi-org support (Datadog's split between `DataDog` open-source and `ddoghq` EMU-managed) is folded in from the start so the storage layout, volume naming, and SSH config flow handle both orgs natively.

## 1. General design goal

The current `dda env dev` flow offers two ways to get repo source code into the container:

1. **Bind-mount** (default): existing checkouts in `../{repo}` on the host are mounted at `/root/repos/{repo}`.
2. **`--clone`**: repos are cloned fresh inside the container at startup via `git dd-clone`.

`--clone` is being replaced by a **worktree-volume** model that becomes the new *golden path* for dev env usage:

- `dda` maintains a **bare repo per repo** inside its data dir on the host, shared across all dev envs.
- Each dev env gets a **named Docker volume per repo**, containing a **git worktree** rooted in that shared bare repo.
- The volume is mounted inside the dev container at a predictable, user-friendly path.
- The bare repo is bind-mounted (read-write) inside the dev container so in-container git operations — including `git fetch` — work transparently and update the shared object store on the host.

**Bind-mount is kept as a best-effort fallback** because a lot of users already rely on it (editing in a host IDE, running host-side git, etc.). It becomes a non-golden path: supported, documented, but with a few known limitations (most notably, it's single-repo per env now).

**Mode selection is context-driven, not flag-driven.** There is no `--worktree` flag; `dda` inspects the CWD and `--repo` arguments at first start to decide which mode to enter. The mode is NOT persisted in `config.json` — the presence or absence of repo-specific Docker volumes is the ground truth at remove time. Re-starting a stopped env is always a plain `docker start`; mounts are baked into the container at initial `docker run`.

All Docker-volume manipulation that doesn't happen through the dev container itself (worktree initialization, dirty checks, cleanup) goes through a **generic `VolumeOps` helper module** that spins up short-lived helper containers (defaulting to `alpine/git`) with the relevant mounts. This keeps the heavy dev-env image out of the volume-manipulation path and concentrates all the "run a command against a volume" logic in one place.

**Multi-org as a first-class concept.** Datadog is splitting its GitHub presence into `DataDog` (open-source) and `ddoghq` (private, EMU-managed). Repo specs accept an `org/` prefix; `[orgs.<name>]` config defines per-org clone URL templates; bare-repo storage, volume names, and dev-container mount paths all carry the org segment. The default org is hardcoded as `DataDog` for backward compatibility. Per-org SSH host aliases live in the user's host `~/.ssh/config`, which `dda` bind-mounts read-only into the dev container so the in-container git client resolves them too. See §2.13 for the full design.

---

## 2. Specific semantics

### 2.1 Mode detection truth table

Runs only on `NONEXISTENT` state (first start). On `STOPPED` state, `start()` unconditionally does `docker start` and returns.

| CWD state               | `--repo` args | Behavior                                                                                                                                                                             |
| ----------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Not inside any git repo | ≥ 1           | **Worktree-volume mode**: one volume + worktree per `--repo`                                                                                                                         |
| Not inside any git repo | 0             | **Error**: `No repository specified. Either cd into a repository, or pass --repo.`                                                                                                   |
| Inside a working tree   | 0             | **Bind-mount mode**: mount the checkout inside the container. If the checkout is a git worktree, also mount the source checkout at the expected spot os it works within the dev env. |
| Inside a working tree   | ≥ 1           | **Error**: `Cannot specify --repo from inside a git repository. cd elsewhere to use --repo, or drop --repo to bind-mount the current repo.`                                          |
| Inside a bare git repo  | any           | **Error**: `Cannot use a bare repository directly as a dev env source. cd elsewhere and pass --repo.`                                                                                |

Detection primitives: `git rev-parse --show-toplevel`, `git rev-parse --is-bare-repository`, `git rev-parse --git-common-dir`. All run via the existing `app.tools.git` wrapper, but we should also take the time to implement helper wrappers for those methods (`get_repo_root` etc.).

**Bind-mount of a local git worktree**: when CWD is itself a git worktree (not the main checkout), the worktree's `.git` file holds an absolute path to the parent repo. The dev container therefore needs a second bind-mount: the parent repo at the parent's exact host path, so the absolute path inside `.git` resolves identically inside the container. Same precedent as the current bind-mount mode.

### 2.2 Repo-name derivation in bind-mount mode

To compute the mount path `/repos/{org}/{repo_name}` when context-detected:

1. Try `git -C {git_root} remote get-url origin`.
2. If found, feed the URL through `dda.utils.git.remote.Remote` and take both `Remote.org` and `Remote.repo` (existing code).
3. If no `origin` remote: fall back to `git_root.name` for `repo_name`, and the default org `DataDog` for `org`.

The resulting `org` and `repo_name` together form the spec stored in `config.repos` as a single qualified entry (`{org}/{repo_name}`). A free-function helper centralizes this derivation so the CLI handler doesn't reimplement it inline.

### 2.3 Branch / ref resolution (worktree-volume mode)

For each `--repo repo[@ref]` spec:

| `@ref` given? | `ref` resolvable in bare repo?        | Action                                                                                                                                    |
| ------------- | ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| yes           | yes (branch)                          | `git worktree add {setup_path} {ref}` — checkout existing branch                                                                          |
| yes           | yes (tag)                             | `git worktree add {setup_path} {ref}` — detached HEAD at tag                                                                              |
| yes           | yes (commit SHA)                      | same — detached HEAD at commit                                                                                                            |
| yes           | **no**                                | `git worktree add -b {ref} {setup_path} {base_ref}` — create new branch named `ref` from `--base-ref`                                     |
| no            | `devenv/{instance}[-n]` exists        | `git worktree add {setup_path} devenv/{instance}[-n]` — **resume**. Emit INFO: `Resumed existing branch devenv/{instance}[-n] for {repo}` |
| no            | `devenv/{instance}[-n]` doesn't exist | `git worktree add -b devenv/{instance}[-n] {setup_path} {base_ref}` — create new                                                          |

Errors from `git worktree add` (e.g. "branch already checked out at `/dda-worktrees/other__{org}__{repo}`") are forwarded verbatim to the user.

### 2.4 `--base-ref` semantics

- CLI option, default **`origin/HEAD`**. After `git fetch`, `origin/HEAD` resolves to the repo's remote default branch (`main`, `master`, whatever). Users may override (`--base-ref origin/7.59.x`).
- Used **only** when a new branch is being created (rows 4 and 6 of §2.3). Ignored when `@ref` already resolves to an existing ref.
- **In bind-mount mode**: `--base-ref` has no meaning. If the user passed it explicitly (non-default value), emit a warning: `--base-ref has no effect in bind-mount mode; ignored`. Otherwise silent.

### 2.5 Duplicate `--repo` entries

User may pass the same repo name multiple times (e.g. to work on two branches of the same repo in one env — useful when splitting a PR with an AI agent that needs both as context).

For the `n`-th occurrence of a given `repo` (0-indexed), the suffix is:
- `""` for `n == 0`
- `f"-{n + 1}"` for `n > 0` (so `-2`, `-3`, …)

Suffix is applied uniformly to:
- **Volume name**: `devenv-{instance}-{org}-{repo}{suffix}`
- **Dev-container mount**: `/repos/{org}/{repo}{suffix}`
- **Helper-container worktree-init path**: `/dda-worktrees/{instance}__{org}__{repo}{suffix}`
- **Auto-default branch name**: `devenv/{instance}{suffix}` (only when `@ref` omitted for that instance — branches are scoped to instance, not org)

`{org}` is the resolved org for that repo (see §2.13). Including org in volume/mount/worktree-init names disambiguates same-named repos across orgs (e.g. `DataDog/foo` vs `ddoghq/foo`) without forcing a pre-flight error.

**Pre-flight checks** (run before any docker call):

- If two specs resolve to the same `(org, repo, resolved_ref)` triple, abort: `Cannot create two worktrees for the same (org, repo, ref): {org}/{repo}@{ref}. Git does not allow two worktrees on one branch.`
- If a target volume name already exists (e.g. left over from a crashed `remove`), `git worktree add` would fail because the volume isn't empty. Detect with the volume-existence check from §2.9 and surface the §2.12 stale-volume error.

**Cosmetic note**: `git worktree list` inside the dev container shows the helper-container init path (`/dda-worktrees/{instance}__{org}__{repo}{suffix}`), not the dev-container mount (`/repos/{org}/{repo}{suffix}`). The `worktrees/{name}/gitdir` file in the bare repo records the path git saw at creation time. Running `git worktree repair` inside the container would fix the display but would also rewrite the path to one we can't filter by `{instance}__` prefix at remove time. We deliberately do not repair.

### 2.6 Instance ID (`--id`) semantics

**Validation** (both modes): if `--id` is manually specified, it must match `^[a-zA-Z0-9][a-zA-Z0-9_-]*$`. The regex is permissive enough to be a Docker name component and a git branch suffix (slashes come from the `devenv/` prefix, not from `--id`). This is a tightening of the prior behavior, which accepted anything Click did; the §2.12 invalid-id error message guides users through the change.

**Defaults**:

- *Bind-mount mode*: `--id` defaults to `default-bind-{repo}`. Used only as part of the container name (existing behavior). Invalid characters in `repo` are replaced with `_` when forming the default.
- *Worktree-volume mode*: `--id` defaults to `default-{repo1}-{repo2}-...` across all configured repos. Invalid characters in any `repo` are replaced with `_` when forming the default. Used as:
  - Docker container name component (existing behavior).
  - Worktree basename prefix: `{instance}__{org}__{repo}[-n]`.
  - Default branch name component: `devenv/{instance}[-n]`.

**Resume behavior**: removing an env deletes its volumes and worktree metadata but **not** the underlying branches. Creating a new env with the same `--id` and no `@ref` resumes the existing `devenv/{instance}` branch automatically — this is intentional and surfaces as the §2.3 INFO log.

### 2.7 Global config: `[orgs]` and `[repos]`

Two top-level config sections in `config.toml`, both `dda`-wide (not under `env.dev`):

```toml
[orgs.DataDog]
url-template = "git@github.com:DataDog/{repo}.git"   # default — can be omitted

[orgs.ddoghq]
url-template = "<TBD>"                                # placeholder — defaults still under investigation
                                                     # any SSH alias referenced here must exist in the
                                                     # user's ~/.ssh/config; dda mounts that file into
                                                     # the dev container (see §2.13)

[repos.dd-source]
org = "ddoghq"                                        # so a bare `dd-source` resolves to ddoghq/dd-source
url = "..."                                           # optional — full URL override, wins over url-template
```

Fields:

- `OrgConfig.url_template: str` — Python `.format(...)`-style template with a single `{repo}` placeholder. Required for any org other than `DataDog` (which ships a hardcoded default). `ddoghq` defaults are TBD pending investigation of how Datadog's automation provisions developer machines.
- `RepoConfig.org: str | None = None` — the org this repo belongs to when the spec is unqualified.
- `RepoConfig.url: str | None = None` — full clone URL override. Wins over `url-template` when set.

Per-org `github` token and `author` identity are deliberately **not** part of `OrgConfig`: Datadog's EMU users share their public-org email and full name, so the global `[github.auth]` and `[tools.git.author]` blocks cover both orgs. Room is left for future per-repo extensions (fetch depth, sparse-checkout patterns, post-clone hooks).

### 2.8 Helper image for volume operations

A new config option governs the image used by `VolumeOps` for short-lived volume helper containers. Lives under `env.dev` (sub-feature of dev env), tunable dda-wide via `config.toml`:

```toml
[env.dev]
worktree-helper-image = "alpine/git"
```

- Default: **`alpine/git`** (~30MB, contains git + basic shell, pulled once and cached by Docker).
- Requirements: must provide `git` and a POSIX shell (`/bin/sh`). `scratch` is rejected — no binaries means any command would fail with an exec error.
- Rationale: the dev-env image is several hundred MB and overkill for `git worktree add` / `git status`. Using a small dedicated image keeps init + remove fast.
- First-use latency: the first `start` on a fresh machine triggers a one-time `~30MB` pull of `alpine/git`. Acceptable given the payoff vs. pulling the dev-env image for every volume operation.

The user can override if they need a different image (e.g. private registry, additional tools baked in).

### 2.9 Volume operations via `VolumeOps`

A generic Docker-volume helper module (not worktree-specific). The worktree feature will be its first consumer; future features (shared dir transfers, cache inspection, etc.) can reuse it.

API sketch:

```python
class VolumeOps:
    def __init__(self, app, helper_image: str): ...

    def exists(self, volume_name: str) -> bool: ...
    def remove(self, volume_name: str) -> None: ...

    def exec(
        self,
        *,
        command: list[str],
        volumes: dict[str, str] | None = None,     # volume_name -> container_path
        bind_mounts: dict[Path, str] | None = None, # host_path -> container_path
        capture: bool = False,
        message: str | None = None,
    ) -> str | None:
        """Run a command in a throwaway helper container with the given mounts.
           Uses the configured helper_image. Returns stdout iff capture=True."""

    def copy_in(self, volume_name: str, src: Path, dst: str) -> None:
        """Copy file/directory from host into a path inside the volume."""

    def copy_out(self, volume_name: str, src: str, dst: Path) -> None:
        """Copy file/directory from inside a volume to the host."""
```

- `copy_in` / `copy_out` are scaffolded using `docker cp` against a short-lived container that mounts the volume. The existing `LinuxContainer.export_path` / `import_path` methods (in `src/dda/env/dev/types/linux_container.py`) cover similar ground; they are migrated to delegate through `VolumeOps` so all "run a command against a volume" flows go through one path.
- `exec` is what the worktree code primarily uses.
- All methods respect the configured helper image.

**Why a helper container is the only portable shape**: Docker doesn't provide a "mount this volume to a host path" primitive — volumes are container-side storage, accessible only via a running container (or, on Linux only, the volume's driver-specific mountpoint under `/var/lib/docker/volumes/`). Spinning up a small helper container with the volume(s) mounted, running the command inside, and capturing stdout is the only cross-platform way to operate on a volume's contents.

### 2.10 Dirty-check and remove confirmation

Triggered only when `remove` is called on an env that has repo volumes (worktree-volume mode). Uses a **single helper container** via `VolumeOps.exec` with all repo volumes and their bare repos mounted at once:

1. Build a batch command that for each repo volume runs `git -C /repos/{org}/{repo}[-n] status --porcelain` and prints its output prefixed by the repo.
2. Invoke `VolumeOps.exec(command=..., volumes=..., bind_mounts=..., capture=True)`.
3. Parse the output; collect per-repo dirty file lists.
4. If any are non-empty: print them for the user, then `click.confirm("Proceed with removal despite dirty worktrees?", abort=True)`.
5. If confirmation is declined, `click.Abort` aborts the command; nothing has been touched yet.

**Worktree-metadata cleanup on the host**: after volumes are removed, prune the matching entries under `{bare}/worktrees/` on the host using a targeted `rm -rf {bare}/worktrees/{instance}__*`. We do **not** use `git worktree prune` from the host: all worktree paths live inside Docker volumes (invisible to host git), so prune would mark every other env's worktree as orphaned and wipe them all.

### 2.11 Bare repo lifecycle

- **Location**: `{app.config.storage.data}/repos/{org}/{repo}.git` (single copy per `(org, repo)` pair, shared across envs). The `{org}/` segment prevents collisions between same-named repos across orgs (e.g. `DataDog/foo` vs `ddoghq/foo`).
- **Auto-created** on first use: when a dev env is being set up and the bare repo doesn't exist.
- **Auto-fetched** before creating any new worktree.
- **Never auto-deleted**. Even when the last env using it is removed, the bare repo stays. Deliberate: re-cloning a large repo is expensive; disk cost is cheap. A future `dda env dev repo clean` command is out of scope.

**Initial-clone sequence**:

```
git clone --bare {url} {path}
git -C {path} config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
git -C {path} fetch origin
git -C {path} remote set-head origin --auto
```

`git clone --bare` does not populate `refs/remotes/origin/*`, so out of the box `origin/HEAD`, `origin/main`, etc. don't resolve — that breaks `--base-ref` defaults. The reconfig + re-fetch + `set-head` steps fix this so all `origin/*` refs resolve inside `git worktree add` and inside any container that mounts the bare repo.

**Shared-state behavior**: the bare repo is bind-mounted read-write into every dev container that uses it. Concurrent fetches from multiple envs are safe (git file-locks). However, any user could in principle run `git gc`/`git prune` inside a container and affect other envs sharing the same bare repo — accepted risk, same as any shared bare repo.

**Concurrent first-start race**: if two envs target the same `(org, repo)` and both find the bare repo missing, they race on `git clone --bare`. One wins; the other fails with "destination path already exists". A file lock is a future improvement; for now the user retries.

### 2.12 Error summary (all surfaced with clear messages)

| Condition                                                       | Message                                                                        |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Not in git + no `--repo`                                        | `No repository specified. cd into a repository, or pass --repo.`               |
| In working tree + `--repo`                                      | `Cannot specify --repo from inside a git repository.`                          |
| In bare repo                                                    | `Cannot use a bare repository directly as a dev env source.`                   |
| Two `--repo` specs resolve to same `(repo, ref)`                | `Cannot create two worktrees for the same (repo, ref): {repo}@{ref}.`          |
| `--id` contains invalid chars                                   | `Invalid --id: must match [a-zA-Z0-9][a-zA-Z0-9_-]*.`                          |
| Volume already exists on first start                            | `Stale volume {name} exists. Run 'docker volume rm {name}' and retry.`         |
| `git worktree add` reports branch already checked out elsewhere | git's own error text, forwarded verbatim                                       |
| Spec uses unknown org                                           | `Unknown org '{org}'. Define [orgs.{org}] in config.toml with a url-template.` |

### 2.13 Multi-org support

Datadog is splitting its GitHub presence across two orgs: `DataDog` (open-source, public) and `ddoghq` (private, GitHub Enterprise Managed Users). Devs have separate SSH profiles for each org, and clone URLs differ. `dda` makes the org axis a first-class concept across repo specs, config, storage paths, and container mounts.

**Repo spec format**: `[org/]repo[@ref]`. Concrete:
- `datadog-agent` — uses default org
- `DataDog/datadog-agent@7.59.x`
- `ddoghq/dd-source@user/feat`

Parser splits the trailing `@` first (so branch names containing `/` survive), then splits a single leading `/` if present to extract the org.

**Default org**: hardcoded as `"DataDog"`. Any spec that omits the `org/` prefix is resolved against the default unless `[repos.<name>].org` says otherwise.

**Org resolution** for a parsed spec:
1. If the spec was qualified (`org/repo`), use that org.
2. Else if `[repos.<repo>].org` is set, use that.
3. Else use the hardcoded default `"DataDog"`.

**URL resolution** for a `(org, repo)` pair:
1. If `[repos.<repo>].url` is set, use it as-is. (Wins regardless of org.)
2. Else apply `[orgs.<org>].url_template.format(repo=repo)`.
3. The `DataDog` org's `url_template` defaults to `git@github.com:DataDog/{repo}.git` if not overridden.
4. If the org is unknown (no `[orgs.<org>]` block and not `DataDog`), abort with the §2.12 unknown-org error.

**SSH config in the dev container**: when an org's clone URL references an SSH host alias (e.g. `git@github-emu:...`), the in-container git client must resolve that alias too. Solution: bind-mount the user's host `~/.ssh/config` (read-only) into the dev container at `/root/.ssh/config`. SSH keys themselves are not bind-mounted — they continue to flow via SSH agent forwarding (existing behavior). Host `~/.ssh/config` is the source of truth; `dda` does not write to it.

**Out of scope (known limitation)**: `dda`'s GitHub-API operations on behalf of a repo (PR review etc.) currently use the global `[github.auth]` token only. Per-org GitHub auth is a future refactor — most work happens in `DataDog` so this isn't blocking.

## 3. System diagram

```
                 HOST FILESYSTEM
   ┌─────────────────────────────────────────────────────────┐
   │ {storage.data}/repos/                                   │
   │   ├── DataDog/                                          │
   │   │     ├── datadog-agent.git/    ◄── shared bare repo  │
   │   │     └── integrations-core.git/   (one per org/repo) │
   │   └── ddoghq/                                           │
   │         └── dd-source.git/                              │
   │ ~/.ssh/config            ◄── host SSH aliases (RO mount)│
   └────────────┬────────────────────────────┬───────┬───────┘
                │ bind-mount (rw)            │ bm rw │ bm ro
                │                            │       │
   ┌────────────▼─────────────┐  ┌───────────▼───────▼──────┐
   │  HELPER CONTAINER         │  │  DEV CONTAINER           │
   │  (alpine/git, ephemeral)  │  │  (linux-container)       │
   │                           │  │                          │
   │ /dda-repos/{org}/         │  │ /dda-repos/{org}/        │
   │   {repo}.git ◄────────────┘  │   {repo}.git ◄───────────┘
   │ /dda-worktrees/              │ /repos/{org}/            │
   │   {instance}__{org}__       │    {repo}{suffix} ──────┐
   │   {repo} ────────────────┐   │ /root/.ssh/config ◄─────┼── (RO)
   │                          │   └──────────────────────────┼─┐
   │  Runs:                   │                              │ │
   │   - git worktree add     │   ┌──────────────────────────┘ │
   │   - git status (dirty)   │   │                            │
   └──────────────────────────┼───┘                            │
                              │                                │
                ┌─────────────▼────────────────────────────────▼──┐
                │  DOCKER NAMED VOLUME                            │
                │  devenv-{instance}-{org}-{repo}{suffix}         │
                │  └── (worktree contents — checked out branch)   │
                └─────────────────────────────────────────────────┘
                  ▲ created by helper container,
                  │ consumed by dev container

   CWD detection (host):
     ┌─────────────────────┐         (no --repo, in working tree)
     │  user runs `dda env │ ──► bind-mount mode
     │  dev start` from X  │
     └─────────────────────┘         (--repo given, X outside any repo)
                                  ──► worktree-volume mode
```

Key invariants:
- Volume root **is** the worktree. Helper container creates it at `/dda-worktrees/{instance}__{org}__{repo}` while the volume is mounted there; dev container then mounts the same volume at `/repos/{org}/{repo}` (cosmetic mismatch in `git worktree list`; see §4.1).
- Bare repo is mounted r/w in *both* containers at the same path `/dda-repos/{org}/{repo}.git`, so the worktree's `gitdir` pointer resolves identically everywhere.
- Host `~/.ssh/config` is mounted **read-only** at `/root/.ssh/config` so the in-container git client resolves SSH host aliases (e.g. `github-emu`) the same way the host does. Keys flow via SSH agent forwarding, not the mount.
- Volume name prefix `devenv-` is distinct from the cache-volume prefix `dda-env-dev-*`, so existing `cache remove` skips repo volumes for free.

## 4. Module structure

The previous attempt scattered worktree logic across `dda.utils.git.{cwd,bare}`, `dda.utils.container.volume`, and `dda.env.dev.types.linux_container`, with `LinuxContainer` doing both container lifecycle *and* worktree orchestration. The proposal below organizes around **two layers** so generic concerns are reusable and the dev-env-specific concerns stay focused:

1. **Generic git-repo abstractions** (`utils/git/repo.py`): `Repo` ABC + `BareRepo` and `Worktree` concrete classes wrapping any on-disk git repository. No knowledge of dev envs, Docker, or duplicate-index suffixes. Reusable for CWD detection, bare-clone management, and any future feature that needs to operate on a host-side git repo.
2. **Dev-env worktree-volume orchestration** (`env/dev/worktree_volumes.py`): `WorktreeVolume` class (knows about Docker volumes, instance ID, suffix-for-duplicates) + free-function orchestrators that compose `BareRepo` from layer 1 with the volume primitives.

This keeps `LinuxContainer` focused on container lifecycle.

```
src/dda/
├── config/model/
│   ├── orgs.py                        # NEW: [orgs.<name>] config (OrgConfig, hardcoded DataDog default)
│   ├── repos.py                       # NEW: [repos.<name>] config + parse_repo_spec + resolve_org + resolve_clone_url
│   └── env.py                         # MOD: + worktree_helper_image
├── env/dev/
│   ├── interface.py                   # (unchanged — base_ref + create_worktrees go on LinuxContainerConfig instead)
│   ├── worktree_volumes.py            # NEW: WorktreeVolume class + provision_for_specs / discover_for_instance / inspect_dirty / teardown_all
│   └── types/linux_container.py       # MOD: thin start/remove delegate to worktree_volumes orchestrators
├── utils/container/
│   └── volumes.py                     # NEW: free-function volume primitives (exists, remove, list_with_prefix, exec, copy_in/out)
├── utils/git/
│   └── repo.py                        # NEW: generic Repo ABC + BareRepo/Worktree concrete classes (replaces the just-landed utils/git/bare.py)
├── tools/
│   ├── docker.py                      # MOD: Add volume create/list/remove primitives consumed by volumes.py
│   └── git.py                         # ALREADY LANDED in a2e4d6c: clone, fetch, has_ref, get_git_dir/toplevel/common_dir, is_bare_repository, get_remote
└── cli/env/dev/
    ├── start/__init__.py              # MOD: CWD detection (inline, via Worktree(app, cwd)) + mode dispatch. --id validation already landed.
    └── remove/__init__.py             # MOD: docstring
```

### Key shape choices

**A. Mode dispatch via `LinuxContainerConfig.create_worktrees: bool`.** Feature-specific config lives on the container-type's config subclass, not on the generic `DeveloperEnvironmentConfig` (which must stay portable across all dev env types). Flow:

1. CLI handler runs CWD detection + truth-table validation (§2.1).
2. Based on the outcome, sets `create_worktrees=True` (worktree-volume mode) or `False` (bind-mount mode) on the constructed `LinuxContainerConfig`. In bind-mount mode, the CLI also derives the single-element `repos` list from CWD (§2.2).
3. `LinuxContainer.start()` reads `self.config.create_worktrees` and branches. No CWD probing inside the env class. Everything else it needs is already on `self.config` (`repos`, `base_ref`) or `self.instance`.

`base_ref` also lives on `LinuxContainerConfig` (not the base config) since it only makes sense for container-like envs that own bare-repo lifecycle.

**B. Volume/worktree lifecycle as free functions in `worktree_volumes.py`.** No orchestrator class. Functions take `app`, `instance`, and whatever else they need; called directly from `LinuxContainer.start`/`remove`. Public surface:

- `provision_for_specs(app, instance, specs, base_ref) -> list[VolumeMount]`
- `discover_for_instance(app, instance) -> list[WorktreeVolume]`
- `inspect_dirty(app, worktree_volumes) -> dict[WorktreeVolume, str]`
- `teardown_all(app, worktree_volumes) -> None`

**C. Naming as `WorktreeVolume` properties.** `volume_name`, `container_mount_path`, `helper_setup_path`, `auto_branch`, `suffix` — computed properties on `WorktreeVolume(app, *, instance, org, repo, n)`. Org axis is required so the same-named repo across orgs (`DataDog/foo` vs `ddoghq/foo`) gets distinct paths. The backing bare-repo is exposed via `WorktreeVolume.bare` (cached_property → `BareRepo` from layer 1, pointed at `{storage.data}/repos/{org}/{repo}.git`).

**D. Volume-name parsing for remove via `WorktreeVolume.from_volume_name(app, instance, volume) -> WorktreeVolume`** — round-trip pair with the `volume_name` property. Used during `remove()` to rehydrate `WorktreeVolume` objects from `volumes.list_with_prefix(app, f"devenv-{instance}-")`.

**E. `volumes` is a module of free functions, not a class.** `volumes.exists`, `volumes.remove`, `volumes.list_with_prefix`, `volumes.exec`, `volumes.copy_in`, `volumes.copy_out`. Each takes `app` and operates on Docker volumes. The "helper image" (default `alpine/git`) is a per-call argument; callers pull it from `app.config.env.dev.worktree_helper_image` at the call site (typically inside `WorktreeVolume.provision`/`is_dirty`/`teardown`). Pattern matches `utils/fs.py` — a library of related functions, not a stateful service.

**F. Low-level helpers go on `app.tools.docker` and `app.tools.git`.** Volume create/list/remove primitives extend `tools/docker.py`. Git operations (clone, fetch, has_ref, get_git_dir, get_toplevel, get_git_common_dir, is_bare_repository, get_remote) are already on `tools/git.py` (commit `a2e4d6c`). The `Repo` subclasses in `utils/git/repo.py`, `WorktreeVolume` in `worktree_volumes.py`, and the `volumes` module orchestrate these primitives but don't reimplement them.

## 5. Verification

Golden path:
1. `cd ~ && dda env dev start -r datadog-agent --id my-feature` → bare repo cloned to `{data}/repos/DataDog/datadog-agent.git`, `alpine/git` helper pulled, volume `devenv-my-feature-DataDog-datadog-agent` created, worktree on `devenv/my-feature` from `origin/HEAD`, container up.
2. `dda env dev shell` → `cd /repos/DataDog/datadog-agent && git status / log / branch` work.
3. `git fetch origin` inside container updates host bare repo.
4. `dda env dev remove --id my-feature` (clean) → batch dirty check passes, volume gone, `{bare}/worktrees/my-feature__DataDog__datadog-agent` gone, branch retained.
5. Re-run (1) with same `--id` → INFO: `Resumed existing branch devenv/my-feature`.

Worktree variations:
6. `-r datadog-agent@7.59.x` → detached HEAD or tracking branch by ref type.
7. `-r datadog-agent -r datadog-agent --id split-pr` → `/repos/DataDog/datadog-agent` + `/repos/DataDog/datadog-agent-2`, branches `devenv/split-pr` + `devenv/split-pr-2`.
8. `-r datadog-agent@main -r datadog-agent@main` → pre-flight error.

Bind-mount:
9. `cd ~/dd/datadog-agent && dda env dev start` → bind-mount at `/repos/DataDog/datadog-agent`.
10. `cd ~/dd/datadog-agent-wt && dda env dev start` (CWD is a worktree) → bind-mount + parent-repo mount; in-container `git status` works.
11. `cd ~/dd/datadog-agent && dda env dev start --base-ref origin/main` → warning emitted.

Errors:
12. `cd ~ && dda env dev start` → "No repository specified …".
13. `cd ~/dd/datadog-agent && dda env dev start -r integrations-core` → "Cannot specify --repo …".
14. `cd ~/dd/some-bare.git && dda env dev start` → "Cannot use a bare repository …".
15. `dda env dev start -r datadog-agent --id "has spaces"` → invalid `--id` error.

Dirty path:
16. Make a file dirty inside `/repos/DataDog/datadog-agent` → `dda env dev remove` lists it via batch dirty check, prompts confirm; abort keeps everything.

Config:
17. `[repos.datadog-agent] url = "git@github.com:MyFork/datadog-agent.git"` → used for initial bare clone.
18. `[env.dev] worktree-helper-image = "myregistry/git-tools:latest"` → used for all `volumes.exec` helper-container invocations.

Cache filter regression:
19. `dda env dev cache remove` with active worktree envs → touches only `dda-env-dev-*` cache volumes; `devenv-*` repo volumes untouched.

Multi-org:
20. `[orgs.ddoghq] url-template = "git@github-emu:ddoghq/{repo}.git"` and host `~/.ssh/config` has a `github-emu` alias → `dda env dev start -r ddoghq/dd-source --id emu-test`:
    - Bare repo cloned to `{data}/repos/ddoghq/dd-source.git` using the EMU template URL.
    - Volume `devenv-emu-test-ddoghq-dd-source` created, mount `/repos/ddoghq/dd-source`.
    - In-container `git fetch origin` resolves `github-emu` via the bind-mounted `~/.ssh/config`, succeeds via SSH agent.
21. `[repos.dd-source] org = "ddoghq"` configured → `dda env dev start -r dd-source --id implicit-org` resolves to the same paths as `ddoghq/dd-source` above.
22. `dda env dev start -r unknown-org/foo` → aborts with the §2.12 unknown-org error.
23. `dda env dev start -r DataDog/datadog-agent -r ddoghq/dd-source --id mixed` → both bare repos cloned under their respective `{org}/` directories; two distinct volumes provisioned; `/repos/DataDog/datadog-agent` and `/repos/ddoghq/dd-source` both mounted.

## 6. Implementation roadmap

Each numbered item is intended as one commit unless explicitly grouped. Dependencies between items are noted in parentheses.

### Status

Already landed on this branch:

- Stripped `--clone`, `clone` field, `clone-repos` config, and the `git dd-clone` block from `start()`.
- Refactored the bind-mount loop in `LinuxContainer.start()` into `_local_repo_mount_specs() -> list[tuple[Path, str]]`. Tests mock this directly instead of staging real `repos/datadog-agent` dirs.
- Loosened `DeveloperEnvironmentConfig.repos` default to `[]`, with a generic help text describing both modes; introduced a `save_default_env_config(temp_dir, **fields)` test helper for commands that don't go through `start`.
- ✅ `--id` regex validation in the CLI start handler (commit `d800259`).
- ✅ `[repos]` config with default `DataDog`/`ddoghq` entries + `resolve_clone_url` helper (commit `82ee9c8`). NOTE: schema will be revisited in phase 2.2 below to introduce `[orgs.<name>]` and the `org` field on `RepoConfig` for full multi-org support.
- ✅ Per-env `base-ref` field + global `worktree-helper-image` config (commit `d800259`).
- ✅ Git tool helpers landed (commit `a2e4d6c`): `clone`, `fetch`, `has_ref`, `get_git_dir`, `get_toplevel`, `get_git_common_dir`, `is_bare_repository`, `get_remote` (extended with `cwd` + `Remote | None` return).
- `BareRepo` was briefly landed in `src/dda/utils/git/bare.py` and rolled back so it can be re-introduced as part of `utils/git/repo.py` (phase 2.7) with the proper layered design.

### Phase 1 — Modify existing

**1.4. Bind-mount host `~/.ssh/config` into the dev container.** (only remaining phase-1 item — `--id` validation already landed)
Add a read-only mount `~/.ssh/config:/root/.ssh/config:ro` in `LinuxContainer.start()` so the in-container git client can resolve any SSH host alias defined in the user's host config (needed for multi-org EMU URLs — see §2.13). Existing keys flow via SSH agent forwarding; this mount only carries config. Tests: extend `TestStart.test_default` (or a small variant) to assert the mount appears in the docker run command. No-op if `~/.ssh/config` doesn't exist on the host (skip silently).

### Phase 2 — Low-level helpers and building blocks

These are mostly independent of each other; ordering within the phase is by dependency only.

**2.1. Config additions (single commit).**
- `LinuxContainerConfig`: add `create_worktrees: bool = False`, `base_ref: str = "origin/HEAD"` with `name="base-ref"`. (Used in phase 3 — fields land first so later commits don't co-mingle config + behavior changes.)
- `DevEnvConfig`: add `worktree_helper_image: str = field(name="worktree-helper-image", default="alpine/git")`.
- Update `tests/cli/config/test_show.py` and `tests/env/dev/types/test_linux_container.py` default-config assertions.

**2.2. Global `[orgs]` + `[repos]` config, spec parser, resolvers (single commit).**
This is the multi-org foundation per §2.7 + §2.13. Lands as one commit because the pieces are tightly coupled.
- New `src/dda/config/model/orgs.py`: `OrgConfig(url_template: str)` plus `DEFAULT_ORG = "DataDog"` and `DEFAULT_DATADOG_URL_TEMPLATE = "git@github.com:DataDog/{repo}.git"`.
- New `src/dda/config/model/repos.py`:
  - `RepoConfig(org: str | None = None, url: str | None = None)`.
  - `ParsedRepoSpec` dataclass (`org`, `repo`, `ref`).
  - `parse_repo_spec(spec: str) -> ParsedRepoSpec` (split `@` first, then leading `/`).
  - `resolve_org(app, parsed: ParsedRepoSpec) -> str` per §2.13 resolution rules.
  - `resolve_clone_url(app, org: str, repo: str) -> str` per §2.13 URL rules; aborts on unknown org.
- Wire into `src/dda/config/model/__init__.py`:
  - `RootConfig.orgs: dict[str, OrgConfig] = field(default_factory=dict)`.
  - `RootConfig.repos: dict[str, RepoConfig] = field(default_factory=dict)`.
- Tests: spec parsing edge cases (`org/repo`, `repo`, `org/repo@branch/with/slash`), org resolution priority, URL resolution (template, full URL override, unknown org abort).

**2.3. Extend `app.tools.git`.** ✅ ALREADY LANDED in commit `a2e4d6c`. Helpers added: `clone(url, path, *, bare=False)`, `fetch(remote, *, prune=False, cwd=None)`, `has_ref(name, *, cwd=None) -> bool`, `get_git_dir() -> Path | None`, `get_toplevel() -> Path | None`, `get_git_common_dir() -> Path`, `is_bare_repository() -> bool`, and `get_remote(name, *, cwd=None) -> Remote | None` (extended). The bare-clone refspec-reconfig + `remote set-head` sequence (§3.5) is NOT in `tools/git`; it's part of `BareRepo.initialize` (phase 2.7).

**2.4. Extend `app.tools.docker`** with volume primitives:
- `volume_exists(name) -> bool`.
- `volume_remove(name)`.
- `volume_list(filter_prefix) -> list[str]`.

**2.5. New `src/dda/utils/container/volumes.py`** (plural — matches `utils/fs.py` style): free-function volume primitives per §2.9.
- `exists(app, name) -> bool`
- `remove(app, name) -> None`
- `list_with_prefix(app, prefix) -> list[str]`
- `exec(app, *, image, command, volumes=None, bind_mounts=None, capture=False, message=None) -> str | None`
- `copy_in(app, *, image, volume, src, dst) -> None`
- `copy_out(app, *, image, volume, src, dst) -> None`

(Depends on 2.4.) Tests: command construction, helper-container exec round-trip with a known volume.

**2.6. CWD detection inline in CLI start handler.** No separate `cwd.py` module — the logic is small and only used here. The handler uses `app.tools.git.get_git_dir() / is_bare_repository() / get_toplevel()` (already landed) plus `Worktree(app, toplevel)` from `utils/git/repo.py` (lands in 2.7) to read `is_linked` / `common_dir` / `org` / `name`. CWD detection contributes one branch of the truth table in §2.1. Tests cover the three CWD shapes (not in git, in worktree, in bare repo) plus an EMU-style remote URL via the existing CLI-test scaffolding.

**2.7. New `src/dda/utils/git/repo.py`** — generic git-repo classes per §4 (layer 1). Replaces the just-landed `src/dda/utils/git/bare.py`.

- `Repo(ABC)`: `path`, `exists`, `is_bare` (abstract), `fetch`, `has_ref`, `remote` (cached_property, may take a name param at impl time), `org`, `name` (basename fallback when no remote).
- `BareRepo(Repo)`: `is_bare = True`. `initialize(url)` runs the §3.5 fetch-refspec / fetch / set-head sequence. `list_worktree_names()`, `remove_worktree_entry(name)`.
- `Worktree(Repo)`: `is_bare = False`. `common_dir` (cached_property → resolved absolute path), `is_linked` (= `common_dir != path/.git`).

Migrate `tests/utils/git/test_bare.py` → `tests/utils/git/test_repo.py`; existing `BareRepo` cases carry over verbatim. Add new tests for `Worktree` (linked vs main worktree, `org`/`name`/`common_dir`/`is_linked` properties).

### Phase 3 — Wire everything together

**3.1. New `src/dda/env/dev/worktree_volumes.py`** — dev-env-specific worktree-volume layer per §4 (layer 2).

`WorktreeVolume(app, *, instance, org, repo, n=0)` class:
- Properties (computed): `suffix`, `volume_name`, `container_mount_path`, `helper_setup_path`, `auto_branch`.
- `bare` (cached_property → `BareRepo` from 2.7 at `{storage.data}/repos/{org}/{repo}.git`).
- `provision(*, ref, base_ref) -> VolumeMount` — ensures bare exists/fresh, creates volume, runs `git worktree add` via helper container (per §2.3 resume-vs-create logic).
- `is_dirty() -> bool`.
- `teardown()` — removes volume + `{bare}/worktrees/{name}` entry.
- `from_volume_name(cls, app, instance, volume) -> WorktreeVolume` (classmethod).

Free-function orchestrators per §4.B:
- `provision_for_specs(app, instance, specs, base_ref) -> list[VolumeMount]` (each spec runs through `parse_repo_spec` + `resolve_org` + `resolve_clone_url` from 2.2; assigns duplicate-`n` per `(org, repo)` pair)
- `discover_for_instance(app, instance) -> list[WorktreeVolume]`
- `inspect_dirty(app, worktree_volumes) -> dict[WorktreeVolume, str]` (single-helper-container batch, per §2.10)
- `teardown_all(app, worktree_volumes) -> None`

Pulls together `BareRepo` from 2.7, `volumes.exec` from 2.5, `app.tools.docker` from 2.4. Self-contained tests mocking subprocess.

**3.2. CLI start handler — mode dispatch.**
Implement §3.1 of the plan: probe CWD, validate truth table, on bind-mount mode derive `(org, repo)` from `git remote get-url origin` via `Remote.org` / `Remote.repo` (with directory-name + default-org fallback). On worktree-volume mode run §2.5 duplicate pre-flight on `(org, repo, ref)` triples. Set `create_worktrees=True/False` on the constructed `LinuxContainerConfig`. In bind-mount mode, when `--base-ref` is non-default, emit the §2.4 warning.

**3.3. `LinuxContainer.start()` — branching.**
Read `self.config.create_worktrees`. Worktree-volume branch calls `provision_worktrees(...)` and splices the returned mounts into the `docker run` command. Bind-mount branch keeps the helper from 1.1. Both share the cache/shared-dir/shell-config mount setup.

**3.4. `LinuxContainer.remove()` — worktree cleanup.**
Implement §3.3 of the plan: `list_worktree_volumes` → `inspect_dirty_worktrees` → `click.confirm` if dirty → `docker rm -f` → `teardown_worktrees`. Plain `docker rm -f` path remains for envs with no `devenv-*` volumes (covers legacy / bind-mount).

### Phase 4 — Polish UX

**4.1. Error catalog tightening.**
Apply §2.12 message text exactly as written. Add tests covering each error row.

**4.2. INFO and warnings.**
- Resume log line `Resumed existing branch devenv/{instance}[-n] for {repo}` per §2.3.
- `--base-ref has no effect in bind-mount mode; ignored` warning per §2.4.

**4.3. Stale-volume preflight.**
Surface the §2.12 stale-volume error before any `docker run` / `git worktree add`.

**4.4. End-to-end verification sweep.**
Run through §5 checklist items 1–23. Anything that's hard to test as a unit gets a manual-verification note in `worktree-support.md` for the reviewer.

### Phase 5 — Docs

**5.1. mkdocs pages.**
Rewrite the `env dev` page so worktree-volume is the golden path and bind-mount is the documented fallback. Cover §2.5 duplicate-repo split-PR pattern, §2.6 resume behavior, §2.11 bare-repo storage location.

**5.2. CLI help text.**
- `--repo`: covers both modes with examples.
- `--base-ref`: when it applies, what `origin/HEAD` resolves to.
- `--id`: character constraint, role in branch naming.
- `start` / `remove` command docstrings updated.

**5.3. Config docs.**
- `[orgs.<name>]` schema, hardcoded `DataDog` default, and the EMU-style example (`ddoghq` with `github-emu` SSH alias). Note that host `~/.ssh/config` is the source of truth for aliases (§2.13).
- `[repos.<name>]` schema (`org` and `url` overrides) with use cases (per-repo fork URL, implicit-org assignment).
- `[env.dev] worktree-helper-image` requirements (§2.8 — git + POSIX shell; `scratch` rejected).

