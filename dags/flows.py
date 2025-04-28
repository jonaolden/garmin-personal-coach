"""
Prefect 3 Flows for the Automated Garmin Training Pipeline.
"""

from prefect import flow, task
from src.settings import load_settings
from src import garmin_client, storage, analytics, llm, planner_interface, monitoring

settings = load_settings()

@flow(name="sync_daily", schedule=settings.sync_daily_cron)
def sync_daily():
    """
    Daily flow to ingest recent Garmin data and update the bronze layer.
    """
    print("Running sync_daily flow.")
    activities = task(garmin_client.get_activities)()
    task(storage.write_df)(activities, "raw_activities")
    task(monitoring.log_event)("sync_daily_ok")

@flow(name="sync_catchup", schedule=settings.sync_catchup_cron)
def sync_catchup():
    """
    Catch-up flow to ingest any missed Garmin data.
    """
    print("Running sync_catchup flow.")
    activities = task(garmin_client.get_activities)(delta_only=True)
    task(storage.write_df)(activities, "raw_activities")

@flow(name="adapt_weekly", schedule=settings.adapt_weekly_cron)
def adapt_weekly():
    """
    Weekly flow to analyze training load, potentially revise the plan with LLM,
    and push updates to Garmin.
    """
    print("Running adapt_weekly flow.")
    current_plan_yaml = """
email: "example@gmail.com"
password: "password"

settings:
  deleteSameNameWorkout: true

definitions:
  GA: 6:35-7:00
  Threshold: 5:20-5:45
  VO2MaxP: 3:30-4:00

workouts:
  interval_Vo2Max:
    - warmup: 15min @H(z2)
    - repeat(8):
      - run: 30sec @P($VO2MaxP) # can use definition here or raw value 3:30-4:00
      - recovery: 1200m
    - cooldown: 15min @H(z2)

schedulePlan:
  start_from: 2024-10-08
  workouts:
    - interval_Vo2Max   # will be schedule on 2024-10-08
    - ga_5k             # will be schedule on 2024-10-09
    - rest              # if no "rest" workout found on garmin connect, skip this day
"""

    df = task(storage.read_df)("SELECT * FROM raw_activities")
    ctl_atl_metrics = task(analytics.compute_ctl_atl)(df)
    hrv_zscore = task(analytics.compute_hrv_zscore)(df)
    # Combine metrics - assuming evaluate_flags can handle a combined dictionary or similar structure
    metrics = {**ctl_atl_metrics, "hrv_zscore": hrv_zscore}
    flags = task(analytics.evaluate_flags)(metrics)

    if flags:
        print("Flags detected, proposing revision.")
        diff = task(llm.propose_revision)(current_plan_yaml, flags)
        task(planner_interface.patch_and_push)(diff)
    else:
        print("No flags detected, no plan revision needed.")

    task(monitoring.alert)(metrics, flags)