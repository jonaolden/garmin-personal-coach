## Automated Garmin Training Pipeline – Updated Blueprint

---
## 1 Objective
Build a fully autonomous pipeline that ingests Garmin data, analyses training-load trends, rewrites next-week training plans with LLM guidance, and pushes them back to Garmin—while remaining observable, explainable, and safe-by-default.

## 2 High-Level Principles
- **Single-source config** – all thresholds, API keys, and env toggles live in `config/`.
- **Fail-open** – on any failure, original workouts flow through unmodified.
- **Observable** – structured logs (Loki) + metrics (Prometheus); zero silent failures.
- **Environment parity** – staging mirrors prod (flows, Docker, secrets) minus athlete accounts.

## 3 Repository Structure
```text
training-pipeline/
├── .gitignore                # includes `plans/`
├── config/
│   ├── default.yaml          # thresholds & back-off
│   ├── staging.yaml          # overrides diff
│   └── prod.yaml
├── dags/                     # Prefect 3 flows
│   └── flows.py
├── src/
│   ├── __init__.py
│   ├── garmin_client.py      # Garmin auth + retry
│   ├── storage.py            # DuckDB I/O
│   ├── analytics.py          # CTL/ATL, HRV z-scores
│   ├── llm.py                # OpenAI wrapper + Pydantic
│   ├── planner_interface.py  # RFC6902 patch + garmin_planner
│   ├── monitoring.py         # logs ➜ Loki, metrics ➜ Prometheus, Slack
│   └── settings.py           # pydantic loader
├── plans/                    # local cache of last-pushed YAML (gitignored)
├── notebooks/                # exploratory analysis
├── tests/                    # pytest + flow tests
│   ├── test_garmin_client.py
│   └── test_flows.py
├── Dockerfile
└── pyproject.toml
```

## 4 Configuration Schema (`config/default.yaml`)
```yaml
overrides_allowed: true
# thresholds
ramp_percentage_max: 0.10
ctl_atl_ratio_max: 1.3
hrv_drop_zscore: -1.0
sleep_min_hours: 6
llm_volume_change_max: 0.20
# retries & back-off
retry:
  max_attempts: 5
  base: 2
  jitter: true
# scheduling
sync_daily_cron: "0 1 * * *"
sync_catchup_cron: "0 10 * * *"
adapt_weekly_cron: "0 17 * * SUN"
```

## 5 Secrets & Environment
- **Garmin & OpenAI tokens** in Prefect Secret blocks → env-vars in Docker.
- **DB path**: `DATA_PATH=/data/garmin.duckdb` (mounted volume).
- `.env` for local; Prefect blocks override in staging/prod.

## 6 Modules & Interfaces
| Module                  | Responsibility                                    | Key Functions                              |
|-------------------------|---------------------------------------------------|--------------------------------------------|
| `garmin_client.py`      | Auth, token refresh, GET requests with retry logic| `login()`, `get_activities()`, `get_hrv()`|
| `storage.py`            | DuckDB read/write, concurrency safe               | `write_df()`, `read_df()`                  |
| `analytics.py`          | CTL/ATL, HRV z-scores, flag gen                   | `compute_ctl_atl()`, `evaluate_flags()`    |
| `llm.py`                | Build prompt + OpenAI call + Pydantic validation  | `propose_revision()`                       |
| `planner_interface.py`  | Apply RFC6902 diff; call `garmin_planner` CLI    | `patch_and_push()`                         |
| `monitoring.py`         | Structured logs, Prom rule generator, Slack      | `log_event()`, `alert()`                   |
| `settings.py`           | Load & merge YAML + env → Settings                | `load_settings(env)`                       |

**`garmin_planner` integration** uses JSON-Patch (RFC6902). Exit code 0 = success; non-zero or stderr = failure → fail-open.

## 7 Prefect 3 Flows
```python
@flow(name="sync_daily", schedule=settings.sync_daily_cron)
def sync_daily():
    ingest()
    update_bronze()
    monitoring.log_event("sync_daily_ok")

@flow(name="sync_catchup", schedule=settings.sync_catchup_cron)
def sync_catchup():
    ingest(delta_only=True)

@flow(name="adapt_weekly", schedule=settings.sync_weekly_cron)
def adapt_weekly():
    metrics = analytics.compute_ctl_atl()
    flags   = analytics.evaluate_flags(metrics)
    if flags:
        diff = llm.propose_revision(current_plan_yaml, flags)
        planner_interface.patch_and_push(diff)
    monitoring.alert(metrics, flags)
```

## 8 Testing Strategy
1. **Unit**: test auth, retries, JSON schema, failure paths.
2. **Integration**: Prefect flows against mocks; dry-run of `garmin_planner`.
3. **E2E Smoke**: GitHub Actions → Mini-Garmin mock → full flows → metrics & alerts.

## 9 CI/CD (GitHub Actions)
```yaml
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - checkout
      - setup-python@v5 with python-version: '3.12'
      - pip install poetry && poetry install
      - poetry run pytest -q
  docker-build:
    if: github.ref == 'refs/heads/dev'
    runs-on: ubuntu-latest
    steps:
      - checkout
      - docker build -t pipeline:staging .
      - docker push ghcr.io/org/pipeline:staging
  promote-prod:
    needs: [test, docker-build]
    if: github.ref == 'refs/heads/main' && github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    steps:
      - docker pull ghcr.io/org/pipeline:staging
      - docker tag ghcr.io/org/pipeline:staging ghcr.io/org/pipeline:prod
      - docker push ghcr.io/org/pipeline:prod
```

## 10 Monitoring & Alerting
- **Metrics**: `flow_success_total`, `activities_ingested_total`, `hrv_last_timestamp`, `db_lock_seconds`.
- **Alerts** (via Prometheus rules generated from `config/*.yaml`):
  - Flow failed twice in 24 h
  - No activities ingested in 24 h
  - `hrv_last_timestamp` > 36 h
- Slack webhook for notifications.

## 11 Data Retention & Archiving
- Raw activity tables retained **90 days**.
- Monthly Prefect job: `VACUUM` + drop partitions older than 90 days.

## 12 Deployment Targets
| Env       | Docker Tag            | Prefect Blocks     | DB                     |
|-----------|-----------------------|--------------------|------------------------|
| Staging   | `pipeline:staging`    | `garmin-staging-*` | DuckDB (local volume)  |
| Production| `pipeline:prod`       | `garmin-prod-*`    | DuckDB on EFS          |

## 13 Suggested Order of Implementation
1. **Config & Settings**: scaffold `config/` and implement `settings.py` for YAML + env loading.
2. **Garmin Client**: build `garmin_client.py` with auth, token refresh, retries.
3. **Storage Layer**: implement `storage.py` for DuckDB I/O and concurrency-safe writes.
4. **Analytics Module**: compute CTL/ATL and HRV z-scores in `analytics.py`.
5. **LLM Integration**: write `llm.py` to construct prompts, call OpenAI, validate with Pydantic.
6. **Planner Interface**: implement RFC6902 patching and `garmin_planner` calls in `planner_interface.py`.
7. **Monitoring**: add structured logging, metrics emitters, and Slack alerts in `monitoring.py`.
8. **Prefect Flows**: finalize `dags/flows.py` with schedules and flow orchestration.
9. **Testing**: add unit, integration, and smoke tests under `tests/`.
10. **CI/CD & Docker**: write `Dockerfile`, `pyproject.toml`, and GitHub Actions workflows.
11. **Observability & Alerts**: generate Prometheus rules from config and wire up Loki.
12. **Deployment**: deploy to staging, verify flows, then promote to production.

---
*Blueprint updated with implementation order.*

## Current Status
* HRV z-score function exists but is not integrated into the main flow.
* No user-facing mechanism for setting goals (date, distance), available weekdays, or blocked dates.
* garmindb is not used directly in Python; data is ingested via CLI.
* The training plan is not dynamically loaded/updated; it is currently hardcoded.

## To-Do / Next Steps
* Integrate HRV z-score into analytics and adaptation logic.
* Implement a user-facing, revisable configuration for goals, available days, and blocked dates (via YAML or environment variables).
* Refactor to use the garmindb Python API directly for data ingestion and analysis.
* Ensure the training plan is dynamically loaded and updated, not hardcoded.
* (Optionally) Update the implementation order if needed.
