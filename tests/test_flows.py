"""Tests for Prefect flows."""

from pathlib import Path
import sys
import types
from unittest.mock import patch

# Ensure project root is on sys.path for importing dags module
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Make Prefect's flow decorator accept a schedule kwarg for tests
import prefect

_orig_flow = prefect.flow

def flow_with_schedule(*args, **kwargs):
    kwargs.pop("schedule", None)
    return _orig_flow(*args, **kwargs)

prefect.flow = flow_with_schedule

# Stub modules with heavy dependencies to simplify testing
llm_stub = types.ModuleType("llm")
llm_stub.propose_revision = lambda *args, **kwargs: None
sys.modules.setdefault("src.llm", llm_stub)

planner_stub = types.ModuleType("planner_interface")
planner_stub.patch_and_push = lambda *args, **kwargs: None
sys.modules.setdefault("src.planner_interface", planner_stub)

settings_stub = types.ModuleType("settings")
class Settings:
    sync_daily_cron = None
    sync_catchup_cron = None
    adapt_weekly_cron = None
settings_stub.Settings = Settings
settings_stub.load_settings = lambda: Settings()
sys.modules.setdefault("src.settings", settings_stub)

from dags import flows


@patch("dags.flows.monitoring.log_event")
@patch("dags.flows.storage.write_df")
@patch("dags.flows.garmin_client.get_activities")
def test_sync_daily_flow(mock_get_activities, mock_write_df, mock_log_event):
    """Test the sync_daily flow."""
    mock_get_activities.return_value = "activities"

    flows.sync_daily()

    mock_get_activities.assert_called_once_with()
    mock_write_df.assert_called_once_with("activities", "raw_activities")
    mock_log_event.assert_called_once_with("sync_daily_ok")


@patch("dags.flows.storage.write_df")
@patch("dags.flows.garmin_client.get_activities")
def test_sync_catchup_flow(mock_get_activities, mock_write_df):
    """Test the sync_catchup flow."""
    mock_get_activities.return_value = "activities"

    flows.sync_catchup()

    mock_get_activities.assert_called_once_with(delta_only=True)
    mock_write_df.assert_called_once_with("activities", "raw_activities")


@patch("dags.flows.monitoring.alert")
@patch("dags.flows.planner_interface.patch_and_push")
@patch("dags.flows.llm.propose_revision")
@patch("dags.flows.analytics.evaluate_flags")
@patch("dags.flows.analytics.compute_hrv_zscore")
@patch("dags.flows.analytics.compute_ctl_atl")
@patch("dags.flows.storage.read_df")
def test_adapt_weekly_flow_with_flags(
    mock_read_df,
    mock_compute_ctl_atl,
    mock_compute_hrv_zscore,
    mock_evaluate_flags,
    mock_propose_revision,
    mock_patch_and_push,
    mock_alert,
):
    """Test adapt_weekly flow when flags are returned."""
    mock_read_df.return_value = "df"
    mock_compute_ctl_atl.return_value = {"ctl": 1}
    mock_compute_hrv_zscore.return_value = 0.5
    mock_evaluate_flags.return_value = ["flag"]
    mock_propose_revision.return_value = "diff"

    flows.adapt_weekly()

    mock_read_df.assert_called_once_with("SELECT * FROM raw_activities")
    mock_compute_ctl_atl.assert_called_once_with("df")
    mock_compute_hrv_zscore.assert_called_once_with("df")
    mock_evaluate_flags.assert_called_once_with({"ctl": 1, "hrv_zscore": 0.5})
    mock_propose_revision.assert_called_once()
    mock_patch_and_push.assert_called_once_with("diff")
    mock_alert.assert_called_once_with({"ctl": 1, "hrv_zscore": 0.5}, ["flag"])


@patch("dags.flows.monitoring.alert")
@patch("dags.flows.planner_interface.patch_and_push")
@patch("dags.flows.llm.propose_revision")
@patch("dags.flows.analytics.evaluate_flags")
@patch("dags.flows.analytics.compute_hrv_zscore")
@patch("dags.flows.analytics.compute_ctl_atl")
@patch("dags.flows.storage.read_df")
def test_adapt_weekly_flow_no_flags(
    mock_read_df,
    mock_compute_ctl_atl,
    mock_compute_hrv_zscore,
    mock_evaluate_flags,
    mock_propose_revision,
    mock_patch_and_push,
    mock_alert,
):
    """Test adapt_weekly flow when no flags are returned."""
    mock_read_df.return_value = "df"
    mock_compute_ctl_atl.return_value = {"ctl": 1}
    mock_compute_hrv_zscore.return_value = 0.5
    mock_evaluate_flags.return_value = []

    flows.adapt_weekly()

    mock_read_df.assert_called_once_with("SELECT * FROM raw_activities")
    mock_compute_ctl_atl.assert_called_once_with("df")
    mock_compute_hrv_zscore.assert_called_once_with("df")
    mock_evaluate_flags.assert_called_once_with({"ctl": 1, "hrv_zscore": 0.5})
    mock_propose_revision.assert_not_called()
    mock_patch_and_push.assert_not_called()
    mock_alert.assert_called_once_with({"ctl": 1, "hrv_zscore": 0.5}, [])
