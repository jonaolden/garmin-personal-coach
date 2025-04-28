```bash
training-pipeline/
├── .gitignore
├── config/
│   ├── default.yaml
│   ├── staging.yaml
│   └── prod.yaml
├── dags/
│   ├── __init__.py
│   └── flows.py
├── src/
│   ├── __init__.py
│   ├── garmin_client.py
│   ├── storage.py
│   ├── analytics.py
│   ├── llm.py
│   ├── planner_interface.py
│   ├── monitoring.py
│   └── settings.py
├── plans/            # gitignored
├── notebooks/
├── tests/
│   ├── test_garmin_client.py
│   └── test_flows.py
├── Dockerfile
└── pyproject.toml
```

---

### .gitignore
```gitignore
# ignore Python artifacts
__pycache__/
*.py[cod]
*.pyo

# local env
.env

# plans cache\ nplans/

# DuckDB file
data/garmin.duckdb
```

---

### config/default.yaml
```yaml
overrides_allowed: true
ramp_percentage_max: 0.10
ctl_atl_ratio_max: 1.3
hrv_drop_zscore: -1.0
sleep_min_hours: 6
llm_volume_change_max: 0.20
retry:
  max_attempts: 5
  base: 2
  jitter: true
sync_daily_cron: "0 1 * * *"
sync_catchup_cron: "0 10 * * *"
adapt_weekly_cron: "0 17 * * SUN"
```

---

### dags/flows.py
```python
from prefect import flow
from src.settings import load_settings
from src import garmin_client, storage, analytics, llm, planner_interface, monitoring

settings = load_settings()

@flow(name="sync_daily", schedule=settings.sync_daily_cron)
def sync_daily():
    activities = garmin_client.get_activities()
    storage.write_df(activities, "raw_activities")
    monitoring.log_event("sync_daily_ok")

@flow(name="sync_catchup", schedule=settings.sync_catchup_cron)
def sync_catchup():
    activities = garmin_client.get_activities(delta_only=True)
    storage.write_df(activities, "raw_activities")

@flow(name="adapt_weekly", schedule=settings.adapt_weekly_cron)
def adapt_weekly():
    df = storage.read_df("SELECT * FROM raw_activities")
    metrics = analytics.compute_ctl_atl(df)
    flags = analytics.evaluate_flags(metrics)
    if flags:
        diff = llm.propose_revision("current_plan.yaml", flags)
        planner_interface.patch_and_push(diff)
    monitoring.alert(metrics, flags)
```

---

*(Stubs for `src/*.py`, `tests/`, `Dockerfile`, `pyproject.toml` omitted for brevity — ready to fill in)*
```

