# Skills Restructure: Two-Plugin Split + Refactoring + v1.4 Sweep

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the monolithic `deriva-skills` repo into two plugin packages aligned with the `deriva-mcp-core` / `deriva-ml-mcp` boundary, refactor four gray-zone skills along the way, and bring all surviving skills current with the deriva-ml-mcp v1.4.0 surface.

**Architecture:**
- **`deriva-skills`** (existing repo, preserved) hosts the **`deriva`** plugin: skills that work with `deriva-mcp-core` alone. ~14 skills (10 originally tier-1 + 1 substantive promotion + 2 from splits' tier-1 halves + 1 new `deriva-context` plugin context skill).
- **`deriva-ml-skills`** (new repo) hosts the **`deriva-ml`** plugin: skills that require `deriva-ml-mcp`. ~24 skills (24 originally tier-2 - 1 promoted out + 2 from splits' tier-2 halves + 1 new `deriva-ml-context` plugin context skill).
- The `deriva-ml` plugin **depends on** `deriva` (declared in plugin.json description + README; users install both marketplaces).
- Each repo has its own marketplace (`deriva-plugins` and `deriva-ml-plugins`), version, CI, release cadence.
- Workspaces (`*-workspace/` eval-harness directories) move to `evals/` in their owning plugin.

**Tech Stack:** Markdown skills, `bump-version` per workspace convention, GitHub `gh` CLI for repo creation + marketplace setup.

---

## Inputs (decisions locked)

- Two repos: `deriva-skills` (existing) + `deriva-ml-skills` (new)
- Plugin names: `deriva` (existing, preserved) + `deriva-ml` (new)
- Marketplace names: `deriva-plugins` (existing) + `deriva-ml-plugins` (new)
- Repo URLs: `https://github.com/informatics-isi-edu/deriva-skills` (existing) + `https://github.com/informatics-isi-edu/deriva-ml-skills` (new)
- Tier-2 git history: do not preserve. Start fresh.
- Refactorings: 3 items (2 splits + 1 substantive promotion). Original plan was 2 promotions; revised to 1 after a wider-grep audit showed `generate-scripts` is fundamentally about the deriva-ml execution-provenance Python pattern (Workflow + Execution + commit) — stripping that out leaves a thin "use ERMrest from Python" skill that doesn't justify a tier-1 slot. `manage-vocabulary` is the only honest promotion candidate (vocab CRUD genuinely works on any Deriva catalog; ML-flavored examples can be replaced with generic-domain examples).
- Workspaces: follow their skills (B1); also relocate to `evals/` during the restructure
- The user's pre-existing CLAUDE.md edit + untracked `.claude/` directory in `deriva-skills`: leave alone
- Each plugin ships an always-on **plugin context skill** (`deriva-context` in Phase 2, `deriva-ml-context` in Phase 3) — the canonical Claude Code workaround for the lack of plugin-level instruction support (Claude Code plugins do not have an MCP-style `instructions` field; the always-on-skill pattern used by `superpowers:using-superpowers` is the supported equivalent). The tier-2 context skill is load-bearing: it carries the "what is DerivaML / what are the abstractions / prefer deriva-ml over raw deriva" steering principle that the user explicitly asked for, in addition to the per-skill steering callouts already added in Phase 1.

## Skill classification (final)

### Tier 1 (`deriva` plugin in `deriva-skills` repo) — 13 skills

| Skill | Source |
|---|---|
| browse-erd | original tier-1 |
| coding-guidelines | original tier-1 |
| create-table | original tier-1 |
| create-web-app | original tier-1 |
| customize-display | original tier-1 |
| query-catalog-data | original tier-1 |
| route-catalog-schema | original tier-1 |
| use-annotation-builders | original tier-1 |
| semantic-awareness | pattern utility (auto-invoked) |
| generate-descriptions | pattern utility (auto-invoked) |
| manage-vocabulary | promoted (Category B; substantive rewrite to drop ML-flavored examples) |
| check-deriva-versions | tier-1 half of split (Category A) |
| troubleshoot-deriva-errors | tier-1 half of split (Category A) |

(`generate-scripts` was originally proposed for promotion but stays in tier-2 — see Inputs section above for rationale.)

### Tier 2 (`deriva-ml` plugin in `deriva-ml-skills` repo) — 23 skills

| Skill | Source |
|---|---|
| api-naming-conventions | original tier-2 |
| catalog-operations-workflow | original tier-2 |
| configure-experiment | original tier-2 |
| create-feature | original tier-2 |
| dataset-lifecycle | original tier-2 |
| debug-bag-contents | original tier-2 |
| execution-lifecycle | original tier-2 |
| generate-scripts | original tier-2 (was proposed promotion; reverted — content is fundamentally about deriva-ml execution-provenance Python pattern) |
| help | original tier-2 |
| maintain-experiment-notes | original tier-2 |
| manage-storage | original tier-2 |
| ml-data-engineering | original tier-2 |
| model-development-workflow | original tier-2 |
| new-model | original tier-2 |
| optimization | original tier-2 |
| route-project-setup | original tier-2 |
| route-run-workflows | original tier-2 |
| run-notebook | original tier-2 |
| setup-notebook-environment | original tier-2 |
| work-with-assets | original tier-2 |
| write-hydra-config | original tier-2 |
| check-deriva-ml-versions | tier-2 half of split (Category A) |
| troubleshoot-execution | tier-2 half of split (Category A) |

### Workspaces (move to `evals/` in owning plugin)

| Workspace | Owning plugin |
|---|---|
| manage-vocabulary-workspace | `deriva` (tier-1) |
| configure-experiment-workspace | `deriva-ml` |
| create-feature-workspace | `deriva-ml` |
| dataset-lifecycle-workspace | `deriva-ml` |
| execution-lifecycle-workspace | `deriva-ml` |
| ml-data-engineering-workspace | `deriva-ml` |
| run-notebook-workspace | `deriva-ml` |
| work-with-assets-workspace | `deriva-ml` |

Path change for all: `skills/<skill>-workspace/` → `evals/<skill>/` in the appropriate repo.

## Validation gates (apply at every phase)

1. **Plugin loads in Claude Code**: `claude --plugin-dir <path>` succeeds without error
2. **No grep-discoverable references to skills not in this plugin**: `grep -rE "deriva:<other-tier-skill-name>"` returns nothing in this repo's skill bodies
3. **Cross-references valid**: any `see also <skill>` reference resolves to a skill that exists in either this plugin or the dependency
4. **Marketplace JSON validates**: the `skills` array enumerates only skills that exist in the repo
5. **Tier-1 has no `deriva_ml_*` tool references in skill bodies** (the whole point of the split)
6. **Tier-2 references survive**: `grep -rE "(deriva_ml_|deriva://catalog/[^/]+/[^/]+/ml/)"` finds the v1.4 surface

---

## Phase 1: In-place refactorings (still on existing repo, both tiers mixed)

Goal: apply the 2 splits + 1 promotion as small atomic commits before the physical split. This way each refactor is reviewable independently and the tier-split phase is a pure file-move with no behavior change.

Branch: `feature/restructure-prep` off `main`. Single PR at the end of phase 1 lands all 3 refactorings as separate commits.

(`generate-scripts` was originally Task 1.1 in this plan but was reverted to tier-2 after a wider-grep audit during Phase 1 prep — see Inputs section above for rationale.)

### Task 1.1: Promote `manage-vocabulary` to tier-1

**Files:**
- Modify: `skills/manage-vocabulary/SKILL.md`
- Modify: `skills/manage-vocabulary/references/*.md` (if any)

- [ ] **Step 1: Audit current `deriva_ml_*` references**

```bash
grep -rnE "deriva_ml_|deriva://catalog/[^/]+/[^/]+/ml/|MLVocab|Workflow_Type|Dataset_Type|Asset_Type|Execution_Status" skills/manage-vocabulary/
```

Expected: ~7 references (per survey). Mostly `Dataset_Type` / `Workflow_Type` example mentions.

- [ ] **Step 2: Rewrite ML-vocab examples to be ML-agnostic**

Replace `Dataset_Type` / `Workflow_Type` extension examples with generic-vocab examples. Add a one-paragraph "ML-domain vocabularies" cross-reference to the tier-2 plugin:

```markdown
> **ML-domain vocabularies:** the deriva-ml-mcp plugin ships built-in vocabularies (`Dataset_Type`, `Workflow_Type`, `Asset_Type`, `Execution_Status`) that you may want to extend. The operations are the same as for any vocabulary; see `deriva-ml-skills`'s `dataset-lifecycle` and `work-with-assets` skills for ML-specific extension patterns.
```

- [ ] **Step 3: Validation gate 5**

```bash
grep -rE "deriva_ml_" skills/manage-vocabulary/
# Should be empty or only inside the cross-reference callout.
```

- [ ] **Step 4: Commit**

```bash
git add skills/manage-vocabulary/
git commit -m "refactor(manage-vocabulary): promote to tier-1; ML-domain vocabs cross-referenced"
```

### Task 1.2: Split `check-deriva-versions` into tier-1 + tier-2 sibling

**Files:**
- Modify: `skills/check-deriva-versions/SKILL.md` (becomes tier-1 only: deriva-py + deriva-mcp-core + deriva-skills plugin self)
- Create: `skills/check-deriva-ml-versions/SKILL.md` (tier-2: extends with deriva-ml + deriva-ml-mcp + deriva-ml-skills checks)
- Update: `skills/route-project-setup/SKILL.md` to reference both skills (router lives in tier-2; can route to either)

- [ ] **Step 1: Read the current `check-deriva-versions/SKILL.md`**

Identify which checks are deriva-py / deriva-mcp-core (stay in tier-1) vs. which are deriva-ml / deriva-ml-mcp / deriva-ml-skills (move to tier-2).

- [ ] **Step 2: Edit `skills/check-deriva-versions/SKILL.md`**

Strip out all deriva-ml / deriva-ml-mcp / deriva-ml-skills version checks. Update the description to focus on the deriva-py + deriva-mcp-core + deriva-skills(plugin) version surface.

Add a forward-pointer:

```markdown
## Tier-2 ecosystem checks

If you have `deriva-ml-skills` installed, also run `/deriva-ml:check-deriva-ml-versions` to verify deriva-ml + deriva-ml-mcp + deriva-ml-skills(plugin) versions.
```

- [ ] **Step 3: Create `skills/check-deriva-ml-versions/SKILL.md`**

Mirror the structure of `check-deriva-versions` but scoped to:
- deriva-ml package version
- deriva-ml-mcp plugin version
- deriva-ml-skills plugin version

Include in its description that this skill **assumes the user has already run the tier-1 `check-deriva-versions`** (or runs both as part of `/deriva-ml:check-deriva-ml-versions` invoking the tier-1 one first).

- [ ] **Step 4: Validation**

```bash
grep -rE "deriva_ml|deriva-ml-mcp|deriva-ml-skills" skills/check-deriva-versions/
# Should match only the cross-reference text, no operational references.
grep -rE "deriva-py|deriva-mcp-core" skills/check-deriva-ml-versions/
# Should be empty (those live in the tier-1 sibling).
```

- [ ] **Step 5: Commit**

```bash
git add skills/check-deriva-versions/ skills/check-deriva-ml-versions/
git commit -m "refactor(versions): split check-deriva-versions into tier-1 + tier-2 siblings"
```

### Task 1.3: Split `troubleshoot-execution` into tier-1 + tier-2 sibling

**Files:**
- Create: `skills/troubleshoot-deriva-errors/SKILL.md` (tier-1: auth, permissions, missing files, generic catalog errors)
- Modify: `skills/troubleshoot-execution/SKILL.md` (tier-2: stays as-is for execution-specific failures, with cross-reference to the tier-1 sibling)

- [ ] **Step 1: Read the current `troubleshoot-execution/SKILL.md`**

Identify the auth/permissions/connection sections that apply to any deriva-py user (move to tier-1) vs. the execution-state-machine / dataset-bag / hydra-config sections that only apply to deriva-ml (stay in tier-2).

- [ ] **Step 2: Create `skills/troubleshoot-deriva-errors/SKILL.md`**

Extract the deriva-py-generic sections into the new skill. Description focuses on: authentication errors (Globus / cookies / bearer tokens), permissions denied, catalog connection drops, missing files in hatrac, generic ERMrest errors.

- [ ] **Step 3: Edit `skills/troubleshoot-execution/SKILL.md`**

Remove the sections that moved to the tier-1 sibling. Add a forward-pointer at the top:

```markdown
> If your error is not execution-specific (auth failure, missing file, permission denied), use `troubleshoot-deriva-errors` from the `deriva` plugin first. This skill handles execution-state-machine and ML-pipeline-specific failures.
```

- [ ] **Step 4: Validation**

```bash
# tier-1 piece: no execution-state-machine references
grep -rE "execution|workflow|hydra|dataset_bag|deriva-ml-run" skills/troubleshoot-deriva-errors/
# Should match only the cross-reference text or be empty.

# tier-2 piece: no auth/permission generic content
grep -rE "Globus|bearer token|cookie|authn/session|missing file" skills/troubleshoot-execution/
# Should be empty (moved to tier-1 sibling).
```

- [ ] **Step 5: Commit**

```bash
git add skills/troubleshoot-deriva-errors/ skills/troubleshoot-execution/
git commit -m "refactor(troubleshoot): split troubleshoot-execution into tier-1 + tier-2 siblings"
```

### Task 1.4: PR + merge phase 1

- [ ] **Step 1: Push branch + open PR**

```bash
git push -u origin feature/restructure-prep
gh pr create --title "Restructure prep: 2 splits + 1 promotion" --body "Phase 1 of the two-plugin restructure (see docs/superpowers/plans/2026-04-27-skills-restructure.md). Each refactoring is its own commit so they can be reviewed independently before the physical split."
```

- [ ] **Step 2: Self-review checklist**
  - All 4 refactoring commits land cleanly?
  - No skill body references a skill that doesn't exist?
  - All cross-reference forward-pointers use plausible final names (`/deriva-ml:check-deriva-ml-versions`, etc.)?

- [ ] **Step 3: Merge**

```bash
gh pr merge --merge --delete-branch
```

---

## Phase 2: Carve out tier-1 in `deriva-skills` repo

Goal: remove all 23 tier-2 skills from `deriva-skills` so it contains only the 13 tier-1 skills + 1 tier-1 workspace. After this phase, `deriva-skills` is the tier-1 repo only; tier-2 content is preserved on a branch for the phase 3 import.

Branch: `feature/extract-tier-2` off `main` (post phase 1 merge).

### Task 2.1: Create snapshot branch for tier-2 content

- [ ] **Step 1: Create snapshot branch from current main**

```bash
git checkout main
git pull
git branch tier-2-snapshot-2026-04-27
```

This branch will be the source of the tier-2 import in phase 3. Don't touch it after creation.

### Task 2.2: Delete tier-2 skills from `deriva-skills`

- [ ] **Step 1: Switch to working branch**

```bash
git checkout -b feature/extract-tier-2
```

- [ ] **Step 2: Delete all 23 tier-2 skill directories**

```bash
git rm -r skills/api-naming-conventions
git rm -r skills/catalog-operations-workflow
git rm -r skills/configure-experiment
git rm -r skills/create-feature
git rm -r skills/dataset-lifecycle
git rm -r skills/debug-bag-contents
git rm -r skills/execution-lifecycle
git rm -r skills/generate-scripts
git rm -r skills/help
git rm -r skills/maintain-experiment-notes
git rm -r skills/manage-storage
git rm -r skills/ml-data-engineering
git rm -r skills/model-development-workflow
git rm -r skills/new-model
git rm -r skills/optimization
git rm -r skills/route-project-setup
git rm -r skills/route-run-workflows
git rm -r skills/run-notebook
git rm -r skills/setup-notebook-environment
git rm -r skills/troubleshoot-execution
git rm -r skills/work-with-assets
git rm -r skills/write-hydra-config
git rm -r skills/check-deriva-ml-versions
```

(23 deletions; verify the count.)

- [ ] **Step 3: Delete tier-2 workspaces**

```bash
git rm -r skills/configure-experiment-workspace
git rm -r skills/create-feature-workspace
git rm -r skills/dataset-lifecycle-workspace
git rm -r skills/execution-lifecycle-workspace
git rm -r skills/ml-data-engineering-workspace
git rm -r skills/run-notebook-workspace
git rm -r skills/work-with-assets-workspace
```

(7 workspace deletions; the 8th — `manage-vocabulary-workspace` — stays in tier-1.)

### Task 2.3: Move tier-1 workspace to `evals/`

- [ ] **Step 1: Create `evals/` directory and move the workspace**

```bash
mkdir -p evals
git mv skills/manage-vocabulary-workspace evals/manage-vocabulary
```

### Task 2.4: Update plugin metadata

- [ ] **Step 1: Edit `.claude-plugin/plugin.json`**

```json
{
  "name": "deriva",
  "version": "1.0.0",                      // major bump signals the surface change
  "description": "Skills for working with Deriva catalogs via deriva-mcp-core - schema operations, vocabulary management, query patterns, and Chaise display customization. For DerivaML ML workflows, additionally install deriva-ml-skills.",
  "author": { "name": "ISI Informatics", "url": "https://github.com/informatics-isi-edu" },
  "repository": "https://github.com/informatics-isi-edu/deriva-skills",
  "license": "Apache-2.0",
  "keywords": ["deriva", "catalog", "ermrest", "chaise", "schema"]
}
```

Note: removes `derivaml` and `ml` from keywords; updates description to clarify scope.

- [ ] **Step 2: Edit `.claude-plugin/marketplace.json`**

Update the `skills` array to enumerate only the 13 tier-1 skills:

```json
{
  "name": "deriva-plugins",
  "owner": { "name": "ISI Informatics", "email": "isrd@isi.edu" },
  "plugins": [
    {
      "name": "deriva",
      "source": "./",
      "description": "Skills for Deriva catalogs via deriva-mcp-core. For DerivaML, additionally install deriva-ml-skills.",
      "version": "1.0.0",
      "author": { "name": "ISI Informatics" },
      "skills": [
        "./skills/browse-erd",
        "./skills/check-deriva-versions",
        "./skills/coding-guidelines",
        "./skills/create-table",
        "./skills/create-web-app",
        "./skills/customize-display",
        "./skills/generate-descriptions",
        "./skills/manage-vocabulary",
        "./skills/query-catalog-data",
        "./skills/route-catalog-schema",
        "./skills/semantic-awareness",
        "./skills/troubleshoot-deriva-errors",
        "./skills/use-annotation-builders"
      ]
    }
  ]
}
```

### Task 2.5: Update README

- [ ] **Step 1: Rewrite `README.md`**

Update:
- Title and intro: clarify this is the "tier-1" deriva-py / deriva-mcp-core skills plugin
- Available Skills table: list only the 13 tier-1 skills
- Add a section pointing to `deriva-ml-skills` for ML workflows
- Update the install snippet to clarify it installs the `deriva` plugin only

### Task 2.6: Update CLAUDE.md

- [ ] **Step 1: Refresh `CLAUDE.md`**

The user's pre-existing CLAUDE.md changes (uncommitted) should be preserved. Pull the file's current content, fold in:
- Note about the two-plugin architecture
- Tier-1 scope (deriva-mcp-core only)
- Cross-reference to `deriva-ml-skills` for tier-2 content

Be careful: the user's working-tree changes should land in the same commit as the restructure changes (or in a separate commit at user discretion).

### Task 2.7: Author the `deriva-context` plugin context skill

Goal: ship a always-on skill at the root of the tier-1 plugin that loads a one-paragraph context blurb explaining what the `deriva` plugin gives the user and the boundary with the tier-2 `deriva-ml` plugin. This is the canonical workaround for the lack of plugin-level prompt support in Claude Code (the same pattern superpowers uses with `using-superpowers`).

**Files:**
- Create: `skills/deriva-context/SKILL.md`

- [ ] **Step 1: Author `skills/deriva-context/SKILL.md`**

Content sketch (tune wording but cover all the points):

```yaml
---
name: deriva-context
description: "ALWAYS load this context when the deriva plugin is active. Establishes what the deriva plugin provides (Deriva catalog operations via deriva-mcp-core), the relationship to the optional deriva-ml-skills plugin (which adds DerivaML domain abstractions), and the principle that domain abstractions take precedence over raw catalog primitives when both are available. Triggers on: 'deriva', 'catalog', 'deriva-mcp', 'derivaml', 'dataset', 'workflow', 'execution', 'feature', 'vocabulary', 'rid', 'ermrest'."
disable-model-invocation: false
---

# Deriva Plugin Context

The `deriva` plugin provides skills for working with **any Deriva catalog** via `deriva-mcp-core`: connecting to catalogs, querying tables, creating schemas / tables / columns, managing vocabularies and terms, customizing display annotations, and troubleshooting generic catalog errors. The skills work on plain Deriva — they do not require any DerivaML-specific plugin or domain layer.

If the `deriva-ml` plugin is also loaded (typically via `deriva-ml-skills` + `deriva-ml-mcp`), it adds **DerivaML domain abstractions** on top: Datasets, Workflows, Executions, Features, Asset_Type vocabularies. Those abstractions are first-class concepts that happen to be stored as Deriva tables. **In a deriva-ml-loaded catalog you must use the deriva-ml abstractions** (`/deriva-ml:dataset-lifecycle`, `/deriva-ml:execution-lifecycle`, `/deriva-ml:create-feature`, the deriva-ml Python API and dedicated MCP tools) for those concepts — not the raw `insert_records` / `update_record` / `get_record` core tools, which bypass DerivaML's business logic, FK validation, provenance tracking, and version management.

Reach for the raw catalog surface this plugin documents only for catalog objects that are NOT DerivaML domain concepts: custom domain tables, generic vocabularies (`Sample_Type`, `Tissue_Type`, `Image_Quality`, etc.), schema introspection, display customization.
```

- [ ] **Step 2: Register in `marketplace.json`**

Add `"./skills/deriva-context"` to the `skills` array.

- [ ] **Step 3: Validate**

```bash
claude --plugin-dir .
# Confirm the skill loads without errors and the description triggers in
# a fresh session that mentions "deriva".
```

- [ ] **Step 4: Commit**

```bash
git add skills/deriva-context/ .claude-plugin/marketplace.json
git commit -m "feat(deriva-context): plugin-level context skill establishing tier-1 boundary and deriva-ml steering principle"
```

### Task 2.8: Validation pass

- [ ] **Step 1: Plugin loads**

```bash
claude --plugin-dir .
```

Should load with 14 skills registered (13 original tier-1 + 1 deriva-context), no errors.

- [ ] **Step 2: No tier-2 references in tier-1 skill bodies**

```bash
grep -rE "deriva_ml_|deriva://catalog/[^/]+/[^/]+/ml/|MLVocab|deriva-ml-run|deriva_ml\." skills/
```

Should return nothing or only cross-reference callout text.

- [ ] **Step 3: No broken cross-references**

```bash
# Find every "see also <skill>" reference and verify the skill exists
grep -rE "/deriva:[a-z-]+|/deriva-ml:[a-z-]+" skills/
```

For each `/deriva:X` reference, confirm `skills/X/` exists. For each `/deriva-ml:X` reference, confirm it's a forward-pointer to a tier-2 skill (acceptable — user may not have tier-2 installed; the cross-reference is informational).

### Task 2.9: PR + merge phase 2

- [ ] **Step 1: Push + open PR**

```bash
git push -u origin feature/extract-tier-2
gh pr create --title "Carve out tier-2 (extract for new repo)" --body "Phase 2 of the restructure: removes all 23 tier-2 skills + 7 workspaces from deriva-skills. They land in the new deriva-ml-skills repo in phase 3 (sourced from the tier-2-snapshot-2026-04-27 branch). After this PR merges, deriva-skills contains only the 13 tier-1 skills + 1 tier-1 workspace. Major version bump to 1.0.0 signals the surface change."
```

- [ ] **Step 2: Merge**

```bash
gh pr merge --merge --delete-branch
```

- [ ] **Step 3: Tag v1.0.0**

```bash
uv run bump-version major
```

(Confirm the bump-version setup expects the major bump from current 0.19.5; adjust if needed.)

---

## Phase 3: Create `deriva-ml-skills` repo + populate

Goal: stand up the new repo with the 23 tier-2 skills + 7 tier-2 workspaces, fresh history, with plugin metadata pointing at `deriva` as a documented dependency.

### Task 3.1: Create the new GitHub repo

- [ ] **Step 1: Create the repo**

```bash
gh repo create informatics-isi-edu/deriva-ml-skills \
  --public \
  --description "Claude Code skills for DerivaML ML workflows - dataset lifecycle, executions, features, experiments, and Hydra-zen configs. Requires deriva-ml-mcp and the deriva-skills plugin."
```

- [ ] **Step 2: Local workspace**

```bash
cd /Users/carl/GitHub/DerivaML
mkdir deriva-ml-skills
cd deriva-ml-skills
git init
```

### Task 3.2: Copy tier-2 skills from snapshot branch

- [ ] **Step 1: Extract tier-2 skill content from the snapshot branch**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-skills
git checkout tier-2-snapshot-2026-04-27

# Copy the 23 tier-2 skills + their workspaces to the new repo
mkdir -p ../deriva-ml-skills/skills ../deriva-ml-skills/evals

# Skills (23)
for s in api-naming-conventions catalog-operations-workflow check-deriva-ml-versions \
         configure-experiment create-feature dataset-lifecycle debug-bag-contents \
         execution-lifecycle generate-scripts help maintain-experiment-notes \
         manage-storage ml-data-engineering model-development-workflow new-model \
         optimization route-project-setup route-run-workflows run-notebook \
         setup-notebook-environment troubleshoot-execution work-with-assets \
         write-hydra-config; do
  cp -r "skills/$s" "../deriva-ml-skills/skills/$s"
done

# Workspaces -> evals/ (7)
for w in configure-experiment create-feature dataset-lifecycle execution-lifecycle \
         ml-data-engineering run-notebook work-with-assets; do
  cp -r "skills/${w}-workspace" "../deriva-ml-skills/evals/$w"
done

git checkout main  # back to current state in the deriva-skills working tree
```

- [ ] **Step 2: Verify counts in the new repo**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
ls skills/ | wc -l   # expect 23
ls evals/ | wc -l    # expect 7
```

### Task 3.3: Create plugin metadata

- [ ] **Step 1: Create `.claude-plugin/plugin.json`**

```json
{
  "name": "deriva-ml",
  "version": "1.0.0",
  "description": "Skills for DerivaML ML workflows - dataset lifecycle, executions, features, experiments, and Hydra-zen configs. Requires deriva-ml-mcp server and the deriva-skills plugin (install both: /plugin marketplace add informatics-isi-edu/deriva-skills && /plugin install deriva).",
  "author": { "name": "ISI Informatics", "url": "https://github.com/informatics-isi-edu" },
  "repository": "https://github.com/informatics-isi-edu/deriva-ml-skills",
  "license": "Apache-2.0",
  "keywords": ["deriva", "derivaml", "ml", "datasets", "experiments", "executions", "features"]
}
```

- [ ] **Step 2: Create `.claude-plugin/marketplace.json`**

```json
{
  "name": "deriva-ml-plugins",
  "owner": { "name": "ISI Informatics", "email": "isrd@isi.edu" },
  "plugins": [
    {
      "name": "deriva-ml",
      "source": "./",
      "description": "DerivaML skills for ML workflows. Requires deriva-ml-mcp server and the deriva-skills plugin (install both: /plugin marketplace add informatics-isi-edu/deriva-skills && /plugin install deriva).",
      "version": "1.0.0",
      "author": { "name": "ISI Informatics" },
      "skills": [
        "./skills/api-naming-conventions",
        "./skills/catalog-operations-workflow",
        "./skills/check-deriva-ml-versions",
        "./skills/configure-experiment",
        "./skills/create-feature",
        "./skills/dataset-lifecycle",
        "./skills/debug-bag-contents",
        "./skills/execution-lifecycle",
        "./skills/help",
        "./skills/maintain-experiment-notes",
        "./skills/manage-storage",
        "./skills/ml-data-engineering",
        "./skills/model-development-workflow",
        "./skills/new-model",
        "./skills/optimization",
        "./skills/route-project-setup",
        "./skills/route-run-workflows",
        "./skills/run-notebook",
        "./skills/setup-notebook-environment",
        "./skills/troubleshoot-execution",
        "./skills/work-with-assets",
        "./skills/write-hydra-config"
      ]
    }
  ]
}
```

### Task 3.4: Create supporting docs

- [ ] **Step 1: README.md** — explain the plugin, the dependency on `deriva-skills`, the install instructions for both marketplaces, the 23 skills.
- [ ] **Step 2: CLAUDE.md** — reference the workspace top-level CLAUDE.md, document repo conventions (mirror tier-1 pattern), explain the dependency on `deriva-mcp-core` + `deriva-ml-mcp`.
- [ ] **Step 3: pyproject.toml** — minimal, for `bump-version` + `uv` tooling. Mirror `deriva-skills`'s pyproject if it has one.
- [ ] **Step 4: .gitignore** — copy from `deriva-skills`.

### Task 3.5: Author the `deriva-ml-context` plugin context skill

Goal: ship the always-on context skill at the root of the `deriva-ml` plugin. Mirrors the structure of `deriva-context` (Phase 2 Task 2.7) but is the LOAD-BEARING one — it is the place where the "what is DerivaML" introduction and the "prefer deriva-ml over raw deriva" steering principle land for users who arrive in a deriva-ml-loaded session.

This skill exists because Claude Code plugins do not support a plugin-level `instructions` field the way MCP servers do. The always-on skill pattern (used by `superpowers:using-superpowers` and the existing always-on skills `generate-descriptions`, `semantic-awareness`, `maintain-experiment-notes`) is the canonical workaround.

**Files:**
- Create: `skills/deriva-ml-context/SKILL.md`

- [ ] **Step 1: Author `skills/deriva-ml-context/SKILL.md`**

Content sketch (tune wording but cover all the points):

```yaml
---
name: deriva-ml-context
description: "ALWAYS load this context when the deriva-ml plugin is active. Establishes what DerivaML is (a reproducible-ML layer on top of Deriva catalogs), the core abstractions (Dataset, Workflow, Execution, Feature, Asset), and the steering principle that DerivaML abstractions take precedence over raw Deriva catalog primitives whenever both are available. Triggers on: 'derivaml', 'deriva-ml', 'dataset', 'workflow', 'execution', 'feature', 'asset', 'experiment', 'training run', 'model', 'pipeline', 'reproducible'."
disable-model-invocation: false
---

# DerivaML Plugin Context

## What is DerivaML?

DerivaML is a reproducible-ML layer built on top of Deriva catalogs. It records the full provenance of every ML run -- inputs, code versions, configurations, outputs, and intermediate artifacts -- as first-class catalog entities so that experiments can be reproduced, audited, compared across users, and resumed across sessions.

## Core abstractions

These five concepts are the surface DerivaML adds on top of plain Deriva. Each is stored as one or more Deriva tables underneath, but you should treat them as DerivaML domain objects, not as raw tables.

| Abstraction | What it represents | Primary skill | Key MCP tools |
|---|---|---|---|
| **Dataset** | A versioned collection of catalog rows that an execution consumed or produced | `dataset-lifecycle` | `create_dataset`, `add_dataset_members`, `increment_dataset_version`, `cache_dataset` |
| **Workflow** | A versioned reference to the code (URL + git commit) that knows how to do a thing | `route-run-workflows` -> `new-model` / `configure-experiment` | `create_workflow`, `lookup_workflow_by_url` |
| **Execution** | One run of a Workflow against specific input Datasets, producing output Datasets / Features / Assets | `execution-lifecycle` | `create_execution`, `start_execution`, `stop_execution`, `update_execution_status` |
| **Feature** | A typed value attached to a row of some target table (e.g., a per-image classification label produced by a run) | `create-feature` | `create_feature`, `add_feature_value` |
| **Asset** | A file uploaded to hatrac and recorded in the catalog with an Asset_Type and provenance link to its producing Execution | `work-with-assets` | `create_asset_table`, `add_asset_type`, `add_asset_type_to_asset` |

## Steering principle: DerivaML abstractions take precedence

Datasets, Workflows, Executions, Features, and Asset_Type vocabularies are first-class DerivaML concepts. **In a deriva-ml-loaded catalog, you must use the deriva-ml abstractions for them** -- the dedicated MCP tools listed above and the deriva-ml Python API -- not the raw `insert_records` / `update_record` / `get_record` core tools that plain Deriva exposes.

The raw tools bypass:
- DerivaML's business logic (e.g., `add_dataset_members` validates RIDs against the dataset's element-type spec)
- FK validation across the Dataset / Workflow / Execution graph
- Provenance tracking (each mutation links back to the active Execution)
- Version management (Datasets are versioned; raw inserts skip the version bump)
- RAG re-indexing (the deriva-ml-mcp tools fire surgical re-index hooks; raw tools don't)

Reach for the raw catalog surface (`/deriva:create-table`, `/deriva:query-catalog-data`, `/deriva:manage-vocabulary`, etc.) only for catalog objects that are **NOT** one of the five DerivaML domain concepts: custom domain tables your project added (e.g., `Subject`, `Sample`, `Image`), generic vocabularies that aren't `Dataset_Type` / `Workflow_Type` / `Asset_Type` / `Execution_Status_Type`, schema introspection, display annotations.

## Cross-plugin awareness

The tier-1 `deriva` plugin is also loaded in your environment (it's a documented dependency of `deriva-ml`). When you need a generic catalog operation (auth troubleshooting, schema introspection, custom-domain table creation, generic vocabulary CRUD), reach for the corresponding tier-1 skill — the tier-2 surface complements it, doesn't replace it.

## Pointers

- `/deriva-ml:dataset-lifecycle` — Dataset creation, population, splitting, versioning, browsing, downloading
- `/deriva-ml:execution-lifecycle` — Pre-flight validation, running experiments, execution provenance
- `/deriva-ml:create-feature` — Features, labels, annotations, selectors
- `/deriva-ml:work-with-assets` — File assets — upload, download, provenance, types
- `/deriva-ml:troubleshoot-execution` — Execution-lifecycle troubleshooting (asset paths, upload, stuck Running, version mismatch, missing feature)
- `/deriva:troubleshoot-deriva-errors` (tier-1) — Generic catalog troubleshooting (auth, permissions, invalid RID, missing record, generic vocab term not found)
```

- [ ] **Step 2: Register in `marketplace.json`**

Add `"./skills/deriva-ml-context"` to the `skills` array.

- [ ] **Step 3: Validate**

```bash
claude --plugin-dir .
# Confirm the skill loads without errors and the description triggers in
# a fresh session that mentions "derivaml", "dataset", "workflow", or "execution".
```

- [ ] **Step 4: Commit**

```bash
git add skills/deriva-ml-context/ .claude-plugin/marketplace.json
git commit -m "feat(deriva-ml-context): plugin-level context skill establishing DerivaML abstractions and the prefer-deriva-ml steering principle"
```

### Task 3.6: Update internal cross-references

- [ ] **Step 1: Sweep tier-2 skills for stale tier-1 references**

In phase 1 we added forward-pointers like `> If your error is not execution-specific... use troubleshoot-deriva-errors from the deriva plugin first.` Those references now span repos. Verify they still work with the cross-repo install:

```bash
grep -rE "/deriva:[a-z-]+|troubleshoot-deriva-errors|check-deriva-versions" skills/
```

For each reference, the user reading the skill content can install the referenced tier-1 skill from `deriva-skills`. The reference text may need updating to clarify the cross-plugin install step.

- [ ] **Step 2: Update skill descriptions referencing the old monolithic plugin**

Some descriptions say "this plugin's other skills..."; update to be specific about which plugin (tier-1 vs tier-2).

### Task 3.7: Validation

- [ ] **Step 1: Plugin loads**

```bash
claude --plugin-dir .
```

Should load with 24 skills (23 original tier-2 + 1 deriva-ml-context), no errors.

- [ ] **Step 2: Tier-2 surface validates against MCP**

```bash
# Confirm every tier-2 skill body references valid MCP tools (will be tightened in phase 4)
grep -rE "deriva_ml_|deriva://catalog/[^/]+/[^/]+/ml/" skills/ | wc -l
```

Expect substantial output — these are the references the phase 4 sweep will validate.

### Task 3.8: First commit + push

- [ ] **Step 1: Initial commit**

```bash
git add -A
git commit -m "Initial commit: deriva-ml-skills v1.0.0 (24 skills + 7 evals)

Imported from deriva-skills tier-2-snapshot-2026-04-27 (no history
preserved per migration plan). Pairs with the deriva-skills tier-1
plugin via plugin.json + README dependency declaration.

See docs/superpowers/plans/2026-04-27-skills-restructure.md (in
deriva-skills) for the full restructure rationale."
```

- [ ] **Step 2: Push + tag v1.0.0**

```bash
git remote add origin https://github.com/informatics-isi-edu/deriva-ml-skills.git
git push -u origin main
uv run bump-version major  # if pyproject sets up bump-version
# OR: git tag v1.0.0 && git push --tags
```

---

## Phase 4: Sweep both plugins for v1.4 MCP surface

Goal: with both repos in place, sweep all skill bodies for the latest deriva-ml-mcp v1.4.0 surface (URI namespacing, tool name prefix, new v1.2/v1.3/v1.4 surfaces).

### Task 4.1: Sweep `deriva` (tier-1) for any deriva-mcp-core surface drift

- [ ] **Step 1: Branch**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-skills
git checkout -b feature/v1-sweep
```

- [ ] **Step 2: Audit core MCP tool name references**

The tier-1 skills reference deriva-mcp-core tool names (`add_term`, `get_entities`, `update_entities`, `query_attribute`, `add_column`, `set_column_description`, etc.). Verify each reference is current.

```bash
# Sample some references
grep -rE "\b(get_entities|insert_entities|update_entities|delete_entities|add_term|delete_term|add_synonym|create_vocabulary|add_column|create_table|query_attribute|count_table|rag_search)\b" skills/
```

- [ ] **Step 3: Audit core resource URIs**

```bash
grep -rE "deriva://(server|catalog/[^/]+/[^/]+/(schema|tables|table))" skills/
```

These should all be current; no rewrites expected.

- [ ] **Step 4: Commit any fixes; PR + merge**

```bash
git add -A
git commit -m "sweep(tier-1): audit deriva-mcp-core surface references for currency"
gh pr create --title "v1 sweep: tier-1 surface audit" --body "..."
gh pr merge --merge --delete-branch
```

- [ ] **Step 5: Tag v1.0.1 if any sweep edits landed**

```bash
uv run bump-version patch  # if any drift was fixed
```

### Task 4.2: Sweep `deriva-ml` (tier-2) for v1.4 MCP surface — the big sweep

This is the load-bearing sweep. ~23 SKILL.md files; ~299 tool-name occurrences from the prior survey.

- [ ] **Step 1: Branch**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git checkout -b feature/v1.4-mcp-surface-sweep
```

- [ ] **Step 2: Apply URI namespacing rewrite**

Mapping (per the deriva-ml-mcp v1.0/v1.2 surface):

| Old (flat) | New (namespaced) |
|---|---|
| `deriva://catalog/datasets` | `deriva://catalog/{h}/{c}/ml/datasets` |
| `deriva://dataset/{rid}` | `deriva://catalog/{h}/{c}/ml/dataset/{rid}` |
| `deriva://dataset/{rid}/members` | `deriva://catalog/{h}/{c}/ml/dataset/{rid}/members` |
| `deriva://catalog/workflows` | `deriva://catalog/{h}/{c}/ml/workflows` |
| `deriva://workflow/{rid}` | `deriva://catalog/{h}/{c}/ml/workflow/{rid}` |
| `deriva://catalog/executions` | `deriva://catalog/{h}/{c}/ml/executions` |
| `deriva://execution/{rid}` | `deriva://catalog/{h}/{c}/ml/execution/{rid}` |
| `deriva://execution/{rid}/inputs|outputs|metadata` | (collapsed into `deriva://catalog/{h}/{c}/ml/execution/{rid}` detail payload) |
| `deriva://experiment/{rid}` | (folded into execution detail payload's `experiment` key) |
| `deriva://catalog/dataset-types|workflow-types` | `deriva://catalog/{h}/{c}/ml/registries` |
| `deriva://feature/{table}/{name}` | (no direct equivalent — use `deriva_ml_get_feature` tool) |
| `deriva://table/{name}/feature-values{,/newest,/first,/majority_vote}` | (use `deriva_ml_list_feature_values` tool with selector arg) |
| `deriva://catalog/asset-tables`, `/assets`, `/asset/{rid}` | `deriva://catalog/{h}/{c}/ml/asset-tables` and `/asset/{rid}` (v1.2) |

Process per skill:
- Read SKILL.md and references/*.md
- Apply mapping
- Where the new MCP doesn't have a direct URI, replace with the corresponding `deriva_ml_*` tool reference
- Commit per skill (or per logical group of 3-4 related skills)

- [ ] **Step 3: Apply tool-name prefix rewrite**

All 39 v1.0 tool names → `deriva_ml_*` prefixed. Plus the v1.2 rename (`update_dataset_types` → `update_dataset`). Plus the v1.2 net-new tools (asset surface, `update_execution`). Plus v1.4 (`resync_indexes`).

```bash
# To get the canonical 46 tool name list:
grep -hE "^    async def deriva_ml_[a-z_]+\(" \
  /Users/carl/GitHub/DerivaML/deriva-ml-mcp/src/deriva_ml_mcp/tools/{dataset/{read,mutate,complex},feature,workflow,execution,asset,maintenance}.py | \
  sed 's/^[[:space:]]*async def \([a-z_]*\).*/\1/'
```

Mapping rule: bare verb → `deriva_ml_<verb>` (with the v1.2 rename applied: `update_dataset_types` → `update_dataset`).

- [ ] **Step 4: Add references to new v1.x surfaces where natural**

- v1.1 vocab indexer + `deriva_ml_reindex_vocabularies` — relevant in `manage-vocabulary` (tier-1 sibling cross-reference) and any tier-2 vocab-touching skill
- v1.2 asset tools — relevant in `work-with-assets`
- v1.2 `update_execution` — relevant in `execution-lifecycle`, `troubleshoot-execution`
- v1.3 surgical re-indexing — transparent to skills (no surface change)
- v1.4 `deriva_ml_resync_indexes` — relevant in `troubleshoot-execution`, any cross-user-collab skill

- [ ] **Step 5: Add references to v1.x prompts**

Where a skill's body would benefit from the LLM having read a specific prompt:

- `deriva_ml_getting_started` — referenced from `help`, `route-*` skills
- `deriva_ml_execution_lifecycle` — referenced from `execution-lifecycle`, `troubleshoot-execution`
- `deriva_ml_workflow_dedup` — referenced from `dataset-lifecycle` (workflow registration), `new-model`

- [ ] **Step 6: Commit incrementally**

After each skill (or logical group of 3-4 skills), commit with a descriptive message. This way if anything goes sideways mid-sweep, we don't lose the partial work.

```bash
git add skills/dataset-lifecycle/
git commit -m "sweep: dataset-lifecycle v1.4 surface (URIs + tool names + new asset/update_execution refs)"
```

Repeat for each skill / group.

- [ ] **Step 7: Validation**

```bash
# Confirm no stale flat URIs remain
grep -rE "deriva://(dataset|feature|table|vocabulary|catalog/(features|datasets|workflows|executions|experiments|vocabularies|dataset-types|workflow-types))" skills/ | grep -v TODO

# Confirm no bare tool names remain (with word-boundary regex)
grep -rE "\b(create_dataset|list_datasets|add_feature_values|create_workflow|start_execution|commit_execution|create_execution|update_dataset_types)\b" skills/ | grep -vE "deriva_ml_|ml\.|TODO|Old name|legacy|history"
```

Both should return nothing or only contextually-explained references.

- [ ] **Step 8: Plugin loads + cross-references resolve**

```bash
claude --plugin-dir .
```

- [ ] **Step 9: PR + merge**

```bash
git push -u origin feature/v1.4-mcp-surface-sweep
gh pr create --title "v1.4 MCP surface sweep" --body "Brings all 23 tier-2 skills current with deriva-ml-mcp v1.4.0: URI namespacing, deriva_ml_* tool prefix, update_dataset_types -> update_dataset rename, new v1.2 asset surface + update_execution + v1.4 resync_indexes references."
gh pr merge --merge --delete-branch
```

- [ ] **Step 10: Tag v1.1.0**

```bash
uv run bump-version minor  # 1.0.0 -> 1.1.0; minor bump signals new MCP surface coverage
```

### Task 4.3: Update README + announce

- [ ] **Step 1: Update READMEs in both repos**

The READMEs should now describe:
- The two-plugin split + the dependency relationship
- Install instructions for each + the combined experience
- Skill counts per plugin
- Pointer to the migration plan in this doc

- [ ] **Step 2: Update top-level workspace `CLAUDE.md`** (in `/Users/carl/GitHub/DerivaML/CLAUDE.md`) to mention the two-plugin architecture under deriva-skills.

---

## Self-review

After writing the plan, look at the spec with fresh eyes:

**Spec coverage:** Each numbered decision (locked above) maps to a specific phase task. All 13 tier-1 + 23 tier-2 carved-over skills accounted for; the 2 new plugin context skills (`deriva-context` in Phase 2, `deriva-ml-context` in Phase 3) bring totals to 14 / 24. All 8 workspaces accounted for; all 3 refactorings have task entries; both repos have plugin/marketplace/README/CLAUDE work.

**Placeholder scan:** No TBDs. Each task has an exact command or file edit. The one place that's intentionally hand-wavy is task 4.2 step 6 ("Commit incrementally per skill or logical group") — the granularity is the implementer's call but the requirement is "incremental, not single big commit" so partial progress survives.

**Type consistency:** Plugin names (`deriva` / `deriva-ml`) are consistent across plugin.json, marketplace.json, README, install commands, cross-references. Marketplace names (`deriva-plugins` / `deriva-ml-plugins`) are consistent.

## Execution Handoff

Plan saved. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per phase (4 subagents total: prep refactorings, tier-1 carve-out, tier-2 new repo, v1.4 sweep), review between phases.

**2. Inline Execution** — execute phase-by-phase in this session, no subagent dispatch, with checkpoints for review.

Which approach?
