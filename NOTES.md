# Project Journal — Sensor Monitoring Data Platform

Learning project simulating an Encardio-style structural/geotechnical sensor
monitoring platform. Stack: Kafka → GCP (GCS + Iceberg) → Snowflake → dbt →
Airflow, wrapped in GitHub Actions CI/CD.

**Purpose of this file**: record every setup step, *why* we made each choice,
and any "challenge" (deliberately induced failure/edge case) we hit — so this
becomes real interview prep material, not just working code.

Format per entry: **What we did → Why → Interview talking point → Challenges observed**

---

## 2026-09-03 — GCP project setup

**What we did**
- Confirmed `gcloud` was already authenticated (account `mandarjoshi575@gmail.com`)
- Created a brand-new GCP project `sensor-monitoring-de` (kept separate from an
  older unrelated project `naukri-agent-mj575`)
- Linked billing account (`My Billing Account`, INR, free trial credit ₹28,694 confirmed)
- Enabled APIs: Cloud Storage, Pub/Sub, Cloud Run, Artifact Registry, IAM,
  IAM Credentials, Cloud Resource Manager, Billing Budgets
- Created bucket `gs://sensor-monitoring-de-bronze` in `us-central1`
  (uniform bucket-level access, Standard storage class)
- Created a budget alert (₹1,000 threshold, 50/90/100% notification triggers)
  scoped to this project only

**Why**
- Dedicated project = clean separation, easy to delete/reset later without
  touching unrelated work, and easy to explain scope in an interview ("here's
  exactly what this project touches").
- `us-central1` was chosen because it's one of the regions eligible for GCS's
  always-free tier (5GB storage, 5,000 write-ops/month, 50,000 read-ops/month
  forever, not just during trial).
- Budget alert = safety net so a mistake (e.g., an oversized Snowflake
  warehouse or a runaway loop) surfaces as an email, not a bill surprise.

**Interview talking point**
- "I scoped cloud resources into a dedicated project with a budget alert
  before writing any pipeline code — shows cost-awareness and blast-radius
  thinking, which matters in any real data platform."

**Challenges observed**
- None yet — straightforward setup step.

---

## 2026-09-07 — Repo skeleton + journal

**What we did**
- Created the initial folder structure:
  - `producer/` — Python Kafka producer / sensor simulator (not yet built)
  - `consumer/` — Kafka consumer that will batch-write to GCS bronze (not yet built)
  - `dbt_project/` — dbt models split into `staging/`, `intermediate/`, `marts/`
    (medallion bronze→silver→gold pattern)
  - `airflow/dags/` — orchestration DAGs (not yet built)
  - `infra/` — will hold Terraform for GCP/Snowflake resources (not yet built)
  - `.github/workflows/` — CI/CD pipelines (not yet built)
- Created this `NOTES.md` journal

**Why**
- Scaffolding the shape of the repo *before* writing code makes the
  bronze→silver→gold medallion architecture visible just from the folder
  structure — a reviewer (or interviewer looking at the repo) immediately
  understands the pipeline stages without reading a line of code.
- We are deliberately NOT setting up git remote / GitHub / Docker / Kafka /
  Snowflake yet — one concept at a time, per the user's explicit request to
  go step-by-step rather than setting up everything at once.

**Interview talking point**
- "I designed the repo layout to mirror the medallion architecture (bronze/
  silver/gold) so the project structure itself documents the data flow."

**Challenges observed**
- None yet.

---

## 2026-09-07 — Local git init + .gitignore

**What we did**
- Confirmed GitHub account for this project: `github.com/mandarjosh` (personal
  profile). Actual project repo will be created there later as its own repo
  (e.g. `mandarjosh/data-engineering-project`), NOT inside the profile README repo.
- Ran `git init` locally — **no GitHub remote connected yet, no push**. This is
  a local-only repo for now.
- Confirmed git identity already configured globally (`Mandar <mandar@woodfrog.tech>`)
  so commits will be attributed correctly.
- Added `.gitignore` covering: secrets/credentials (`.env`, `*.key`, service
  account JSON files, `profiles.yml`), Python venv/cache, dbt `target/`/`logs/`/
  `dbt_packages/`, Airflow logs/db/config, Terraform state/`.tfvars`, and OS/editor
  junk (`.DS_Store`, `.vscode/`).

**Why**
- We init git *before* writing any real code so history starts clean from
  commit #1 — no risk of accidentally committing something before the
  `.gitignore` existed.
- The `.gitignore` is written proactively (before we even have a `.env` or
  `profiles.yml` file yet) specifically to prevent the single most common,
  most embarrassing data-engineering mistake: committing a Snowflake password,
  GCP service-account JSON key, or Terraform state file (which can contain
  secrets in plaintext) to git history. Once a secret is committed, it's in
  history forever unless you rewrite history — much easier to never let it
  happen.
- `profiles.yml` is dbt's connection-credentials file (Snowflake account/user/
  password) — it lives outside the dbt project by convention (`~/.dbt/`)
  specifically for this reason, but we ignore it here too as defense in depth
  in case anyone ever points it locally.

**Interview talking point**
- "I set up `.gitignore` for secrets and generated artifacts before writing
  any code, not after — treating credential hygiene as a day-1 concern rather
  than a cleanup task. I can also explain why tools like dbt keep
  `profiles.yml` outside the repo by convention, and why Terraform state can
  itself contain secrets and needs the same treatment."

**Challenges observed**
- None yet — this is a preventative step, no failure to observe here.

---

## 2026-09-07 — Fixed git identity (repo-local override)

**What we did**
- Discovered the *global* git identity on this Mac (`Mandar <mandar@woodfrog.tech>`)
  is tied to a work/org GitHub account, not the personal account
  (`github.com/mandarjosh`) this project will be pushed to.
- Set a **repo-local** git identity (`git config user.name` / `user.email`,
  without `--global`) scoped to just this project:
  `Mandar Joshi <mandarjoshi575@gmail.com>`.
- Confirmed the global config was left untouched (still the org identity, for
  other/work repos on this machine).
- Amended the one existing commit (`git commit --amend --reset-author`) to fix
  its author, since it hadn't been pushed anywhere yet — safe to rewrite local
  history at this stage.

**Why**
- Git identity is resolved per-repo: local config (set inside a repo directory)
  overrides global config (machine-wide default). Without a local override,
  every commit here would've inherited the org email.
- This matters because GitHub attributes commits to accounts by matching the
  commit's email to a *verified* email on that account. A commit made with an
  org email won't show as authored by your personal account, and depending on
  org policy, an org-owned identity might not even be appropriate to use on a
  personal learning repo pushed to a personal account.
- We fixed it *before* pushing to GitHub — rewriting commit authorship
  (`--amend`, or `rebase` for multiple commits) is only safe to do on commits
  that haven't been shared/pushed yet. Once pushed and others may have pulled,
  rewriting history requires force-push and coordination — a good rule to
  internalize now.

**Interview talking point**
- "I know git identity resolves per-repo — global config is just a default,
  and you can override `user.name`/`user.email` locally per repository. I also
  know the difference between amending unpushed history (safe) versus rewriting
  already-pushed/shared history (requires force-push and can break
  collaborators) — I fixed an identity mistake here while it was still
  local-only, before it became a shared-history problem."

**Challenges observed**
- Real one: caught a genuine identity misconfiguration before it caused a
  problem (wrong account attribution on GitHub, or an org-owned email ending
  up on a personal public repo). This is a legitimate "attention to detail"
  story, not a manufactured exercise.

---

## 2026-09-07 — Connected repo to GitHub + auth troubleshooting

**What we did**
- Created empty repo `github.com/mandarjosh/sensor-monitoring-de` on GitHub (browser).
- Connected local repo: `git remote add origin https://github.com/mandarjosh/sensor-monitoring-de.git`.
- Hit a real, unstaged problem: `git push -u origin main` appeared to "hang"
  with no visible prompt. Debugged systematically instead of guessing:
  1. Verified the `osxkeychain` credential helper binary itself works fine
     (tested directly, resolved instantly) — ruled out the helper being broken.
  2. Verified network/TLS/DNS to `github.com` works fine (`GIT_TRACE`/
     `GIT_CURL_VERBOSE` + a manual `git ls-remote`) — ruled out network/proxy issues.
  3. Inspected the actual stuck process tree (`ps -ef`) for the hung terminal's
     PID — found the real cause: **Cursor's IDE Git integration was intercepting
     the credential prompt via its own `askpass.sh`/`askpass-main.js`**, popping
     up a small input box inside the Cursor UI (not inside the terminal panel
     itself) — easy to miss, looked identical to a genuine hang.
  4. Bypassed it explicitly: `GIT_ASKPASS= SSH_ASKPASS= GIT_TERMINAL_PROMPT=1 git -c credential.helper= push -u origin main`
     — this forces git to prompt directly in the terminal, no GUI helper in the way.
  5. Got a clear, different error this time: `remote: Invalid username or
     token. Password authentication is not supported for Git operations.`
     — root cause: a plain GitHub account **password** was entered as the
     password field. GitHub deprecated password auth for git over HTTPS in 2021.
  6. Fix: generated a GitHub **Personal Access Token** (classic, `repo` scope,
     90-day expiry) at github.com/settings/tokens, used that as the password
     instead. Push succeeded: `main -> main [new branch]`, upstream tracking set.
- Verified locally: `git status` shows `up to date with 'origin/main'`, clean
  working tree, both commits present with correct author.

**Why**
- This is a genuinely common real-world debugging sequence: "is it the tool,
  is it the network, is it the environment/IDE, or is it a credentials
  problem?" — worked through in that order, from most-general to
  most-specific, using process inspection (`ps -ef`) rather than guessing.
- GitHub requiring a PAT (or SSH key) instead of a password is a hard security
  requirement now industry-wide, not GitHub-specific — same is true for GitLab,
  Bitbucket, etc. Understanding *why* (passwords are weaker, non-revocable
  per-purpose, and don't support scoped permissions the way tokens do) matters
  more than just knowing the fix.
- IDE Git integrations (VS Code, Cursor, etc.) commonly inject their own
  askpass helper that intercepts terminal credential prompts and renders them
  as a GUI element instead — worth recognizing this pattern immediately next
  time, since it looks exactly like a frozen terminal.

**Interview talking point**
- "I debugged a git push that looked hung by isolating each layer independently
  — credential helper, network/TLS, then the actual OS process tree — rather
  than assuming the first candidate cause. Found it was the IDE's own askpass
  integration intercepting the prompt into a UI element outside the terminal.
  Separately, I know why GitHub requires a Personal Access Token or SSH key
  instead of a password for git operations, and how token scopes (`repo`,
  fine-grained permissions) work."
- Also worth mentioning: PATs should be scoped minimally and rotated (we set
  a 90-day expiry deliberately, not "no expiration") — a good security hygiene
  habit to mention.

**Challenges observed**
- Real, unplanned challenge (not manufactured): git auth failure with a
  misleading "hang" symptom, root-caused via systematic process/network
  isolation rather than trial-and-error. Good, honest interview story.

---

---

## 2026-09-07 — Token exposure caught + rotated, repo fully synced

**What we did**
- While debugging the auth flow (previous entry), a PAT was accidentally typed
  as part of a shell command (`GIT_ASKPASS= ghp_xxx= git ...`) instead of at
  the interactive password prompt — this put the token in plaintext in shell
  history / terminal logs, which counts as a credential exposure even though
  no one else saw it directly.
- Caught this by re-reading the terminal transcript carefully rather than just
  checking "did the push succeed."
- **Revoked** the exposed token on GitHub immediately
  (github.com/settings/tokens → Delete), then generated a fresh replacement
  token (classic, `repo` scope, 90-day expiry) and used *that* correctly — only
  entering it at the actual `Password for 'https://...':` prompt.
- Re-ran plain `git push` (no `credential.helper=` override this time) so the
  default `osxkeychain` helper stores the working token for future pushes.
- Verified full sync: `git fetch` + `git status` shows `up to date with
  'origin/main'`, all 3 commits present on GitHub.

**Why**
- The rule with any leaked secret (token, password, API key) is: **treat it as
  compromised the moment it's exposed anywhere it shouldn't be** — shell
  history, logs, chat, screenshots — and revoke/rotate immediately, rather than
  assuming "probably fine, nobody saw it." Revocation is cheap; a compromised
  token being used maliciously is not.
- This is exactly why PATs have scopes and expirations by design (we chose
  90 days, not "no expiration") — short-lived, narrowly-scoped credentials
  limit the blast radius when a mistake like this happens, which it will,
  to everyone, eventually.
- Command-line arguments and environment variable assignments are visible in
  shell history (`~/.zsh_history`) and process listings (`ps -ef` shows full
  command lines) — never pass secrets as CLI args; only via interactive
  prompts, environment variables sourced from a `.env` file (already
  gitignored), or a secrets manager.

**Interview talking point**
- "I treat credential exposure as compromised-by-default, not
  compromised-only-if-misused — I caught a token accidentally typed into a
  command line instead of an interactive prompt, and rotated it immediately
  rather than assuming it was fine. I also default to short-lived, narrowly
  scoped tokens specifically so mistakes like this have limited impact."

**Challenges observed**
- Real challenge: a genuine near-miss credential leak, caught and remediated
  correctly (revoke + rotate), not just a "gotcha" exercise. Good, honest
  story about security hygiene under real conditions.

---

## 2026-09-07 — Python sensor simulator (local, no Kafka/cloud yet)

**What we did**
- Created a Python virtual environment (`.venv/`) scoped to this project
  (never install packages globally/system-wide).
- Built `producer/sensors.py`: a dependency-free (standard-library-only)
  sensor simulator modeling 4 Encardio-style instrument types:
  - `Piezometer` (pore water pressure, kPa) — dam/embankment safety
  - `StrainGauge` (microstrain) — structural load/fatigue
  - `Tiltmeter` (tilt angle, degrees) — slope/wall stability
  - `CrackMeter` (crack displacement, mm) — tunnel/structure crack tracking
  - Each sensor keeps internal **state** (a running baseline) and perturbs it
    slightly per reading (drift + Gaussian noise), rather than pure random
    values each call — real sensors drift slowly, they don't teleport.
  - Each has a small deliberate probability of an "alarm" spike, so
    downstream layers (dbt marts, later) have real threshold-breach events
    to detect, mirroring Encardio's Drishti/Proqio real-time alerting.
  - Output format: **JSON Lines** (one JSON object per line, appended), not
    a single JSON array — this is the standard format for streaming/log-style
    data (can append forever without re-parsing the whole file) and matches
    what a real Kafka-consumer-to-object-storage batch writer typically does.
- Built `producer/generate_local.py`: a CLI to run the simulator and write
  output to `producer/output/readings.jsonl` (gitignored — generated data,
  not source).
- Ran it: 12 devices (3 per sensor type × 4 types) × 4 ticks = 48 readings.
  Verified output by eye — realistic baselines per type, 2 genuine ALARM
  events triggered naturally by the spike logic, battery voltage slowly
  draining across ticks.
- Fixed a small path bug along the way: the default output path was relative
  and produced a nested `producer/producer/output/` when run from inside the
  `producer/` folder — fixed by resolving the default path from
  `Path(__file__).resolve().parent` instead of a relative string, so the
  script behaves correctly regardless of the caller's current working
  directory.

**Why**
- No external dependencies at this stage keeps the "does the data model make
  sense" question separate from "does Kafka/networking work" — one variable
  at a time, easier to debug either layer independently later.
- Stateful, drifting simulation (vs. pure `random.uniform()` every call)
  matters because it's what makes the eventual dbt tests/marts meaningful —
  e.g. a "value changed too fast" anomaly check only means something if
  normal values *don't* jump around wildly in the first place.
- `Path(__file__).resolve().parent`-based defaults are a general good habit
  for any CLI script: makes behavior independent of the caller's current
  working directory, which avoids a whole class of "works on my machine
  depending on which folder I ran it from" bugs.

**Interview talking point**
- "I modeled sensor telemetry as stateful processes with drift and noise
  rather than pure randomness, specifically so downstream data-quality tests
  and anomaly detection would have realistic signal to work with — a
  simulator that's 'too random' teaches you nothing about anomaly detection
  because everything already looks anomalous."
- "I chose JSON Lines over a JSON array for the output format because it's
  append-friendly and matches how streaming data actually gets batch-written
  in real pipelines — you don't want to re-serialize an entire growing array
  every time you add one record."
- Can also speak to the CWD-independent path bug as a real, small debugging
  moment — habit of using `__file__`-relative paths in scripts now.

**Challenges observed**
- Real (small) bug: default output path was relative to *current working
  directory*, not the script's location — produced an incorrect nested
  folder path when invoked from within `producer/`. Fixed properly rather
  than just deleting the wrong file and re-running from the right directory.

---

## Up next (not started)

- [ ] Kafka (local, Docker) — producer sends these readings to a topic instead of a file
- [ ] Local Kafka via Docker Compose (Redpanda or real Kafka — decision pending)
- [ ] Kafka consumer → GCS bronze writer (batched, to respect free-tier write-ops limit)
- [ ] Snowflake account creation + warehouse/database/role setup
- [ ] Iceberg External Volume (Snowflake-managed catalog) pointing at a dedicated
      GCS bucket
- [ ] dbt project init against Snowflake
- [ ] Airflow (local Docker) orchestrating the above
- [ ] GitHub repo + GitHub Actions CI/CD

We are taking this one fully-understood step at a time — no jumping ahead.
