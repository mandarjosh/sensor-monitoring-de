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

## Up next (not started)

- [ ] First commit (folders + NOTES.md + .gitignore)
- [ ] Python producer: minimal sensor simulator writing to local JSON (no Kafka yet)
- [ ] Local Kafka via Docker Compose (Redpanda or real Kafka — decision pending)
- [ ] Kafka consumer → GCS bronze writer (batched, to respect free-tier write-ops limit)
- [ ] Snowflake account creation + warehouse/database/role setup
- [ ] Iceberg External Volume (Snowflake-managed catalog) pointing at a dedicated
      GCS bucket
- [ ] dbt project init against Snowflake
- [ ] Airflow (local Docker) orchestrating the above
- [ ] GitHub repo + GitHub Actions CI/CD

We are taking this one fully-understood step at a time — no jumping ahead.
