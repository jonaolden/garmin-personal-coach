"""
Integration Tests for Prefect Flows.
"""

import pytest
from unittest.mock import patch, MagicMock
from prefect.testing.utilities import prefect_test_harness

# Import flows from dags.flows
from dags import flows

# TODO: Add integration tests for flows using mocks for external dependencies
@prefect_test_harness
@patch('dags.flows.GarminClient')
@patch('dags.flows.Storage')
@patch('dags.flows.Analytics')
def test_sync_daily_flow(mock_analytics, mock_storage, mock_garmin_client):
    """
    Test the sync_daily flow with mocked dependencies.
    """
    # Configure mocks
    mock_garmin_instance = MagicMock()
    mock_garmin_client.return_value = mock_garmin_instance
    mock_garmin_instance.get_activities.return_value = [{"activityId": 1, "activityName": "Running"}]
    mock_garmin_instance.get_hrv.return_value = {"hrvSummary": {"avgHrv": 50}}

    mock_storage_instance = MagicMock()
    mock_storage.return_value = mock_storage_instance

    mock_analytics_instance = MagicMock()
    mock_analytics.return_value = mock_analytics_instance

    # Run the flow
    flows.sync_daily_flow()

    # Assertions
    mock_garmin_client.assert_called_once()
    mock_garmin_instance.login.assert_called_once()
    mock_garmin_instance.get_activities.assert_called_once()
    mock_garmin_instance.get_hrv.assert_called_once()
    mock_storage.assert_called_once()
    mock_storage_instance.save_activities.assert_called_once_with([{"activityId": 1, "activityName": "Running"}])
    mock_storage_instance.save_hrv.assert_called_once_with({"hrvSummary": {"avgHrv": 50}})
    mock_analytics.assert_called_once()
    mock_analytics_instance.process_daily_data.assert_called_once()

@prefect_test_harness
@patch('dags.flows.GarminClient')
@patch('dags.flows.Storage')
@patch('dags.flows.Analytics')
def test_sync_catchup_flow(mock_analytics, mock_storage, mock_garmin_client):
    """
    Test the sync_catchup flow with mocked dependencies.
    """
    # Configure mocks
    mock_garmin_instance = MagicMock()
    mock_garmin_client.return_value = mock_garmin_instance
    mock_garmin_instance.get_activities.return_value = [{"activityId": 2, "activityName": "Hiking"}]
    mock_garmin_instance.get_hrv.return_value = {"hrvSummary": {"avgHrv": 55}}

    mock_storage_instance = MagicMock()
    mock_storage.return_value = mock_storage_instance

    mock_analytics_instance = MagicMock()
    mock_analytics.return_value = mock_analytics_instance

    # Run the flow
    flows.sync_catchup_flow()

    # Assertions
    mock_garmin_client.assert_called_once()
    mock_garmin_instance.login.assert_called_once()
    mock_garmin_instance.get_activities.assert_called_once()
    mock_garmin_instance.get_hrv.assert_called_once()
    mock_storage.assert_called_once()
    mock_storage_instance.save_activities.assert_called_once_with([{"activityId": 2, "activityName": "Hiking"}])
    mock_storage_instance.save_hrv.assert_called_once_with({"hrvSummary": {"avgHrv": 55}})
    mock_analytics.assert_called_once()
    mock_analytics_instance.process_catchup_data.assert_called_once()

@prefect_test_harness
@patch('dags.flows.Storage')
@patch('dags.flows.Analytics')
@patch('dags.flows.LLM')
@patch('dags.flows.PlannerInterface')
def test_adapt_weekly_flow(mock_planner, mock_llm, mock_analytics, mock_storage):
    """
    Test the adapt_weekly flow with mocked dependencies.
    """
    # Configure mocks
    mock_storage_instance = MagicMock()
    mock_storage.return_value = mock_storage_instance
    mock_storage_instance.load_activities_for_week.return_value = [{"activityId": 3, "activityName": "Swimming"}]
    mock_storage_instance.load_hrv_for_week.return_value = [{"hrvSummary": {"avgHrv": 60}}]

    mock_analytics_instance = MagicMock()
    mock_analytics.return_value = mock_analytics_instance
    mock_analytics_instance.analyze_weekly_performance.return_value = {"performance": "good"}

    mock_llm_instance = MagicMock()
    mock_llm.return_value = mock_llm_instance
    mock_llm_instance.generate_weekly_plan.return_value = {"plan": "new plan"}

    mock_planner_instance = MagicMock()
    mock_planner.return_value = mock_planner_instance

    # Run the flow
    flows.adapt_weekly_flow()

    # Assertions
    mock_storage.assert_called_once()
    mock_storage_instance.load_activities_for_week.assert_called_once()
    mock_storage_instance.load_hrv_for_week.assert_called_once()
    mock_analytics.assert_called_once()
    mock_analytics_instance.analyze_weekly_performance.assert_called_once_with([{"activityId": 3, "activityName": "Swimming"}], [{"hrvSummary": {"avgHrv": 60}}])
    mock_llm.assert_called_once()
    mock_llm_instance.generate_weekly_plan.assert_called_once_with({"performance": "good"})
    mock_planner.assert_called_once()
    mock_planner_instance.update_plan.assert_called_once_with({"plan": "new plan"})

@prefect_test_harness
@patch('dags.flows.Storage')
@patch('dags.flows.Analytics')
@patch('dags.flows.LLM')
@patch('dags.flows.PlannerInterface')
def test_adapt_weekly_flow_with_flags(mock_planner, mock_llm, mock_analytics, mock_storage):
    """
    Test the adapt_weekly flow when flags are detected.
    """
    # Configure mocks
    mock_storage_instance = MagicMock()
    mock_storage.return_value = mock_storage_instance
    mock_storage_instance.load_activities_for_week.return_value = [{"activityId": 3, "activityName": "Swimming"}]
    mock_storage_instance.load_hrv_for_week.return_value = [{"hrvSummary": {"avgHrv": 60}}]

    mock_analytics_instance = MagicMock()
    mock_analytics.return_value = mock_analytics_instance
    mock_analytics_instance.analyze_weekly_performance.return_value = {"performance": "good"}
    mock_analytics_instance.evaluate_flags.return_value = ["flag1", "flag2"] # Flags detected

    mock_llm_instance = MagicMock()
    mock_llm.return_value = mock_llm_instance
    mock_llm_instance.propose_revision.return_value = {"plan": "new plan"}

    mock_planner_instance = MagicMock()
    mock_planner.return_value = mock_planner_instance

    # Run the flow
    flows.adapt_weekly_flow()

    # Assertions
    mock_storage.assert_called_once()
    mock_storage_instance.load_activities_for_week.assert_called_once()
    mock_storage_instance.load_hrv_for_week.assert_called_once()
    mock_analytics.assert_called_once()
    mock_analytics_instance.analyze_weekly_performance.assert_called_once_with([{"activityId": 3, "activityName": "Swimming"}], [{"hrvSummary": {"avgHrv": 60}}])
    mock_analytics_instance.evaluate_flags.assert_called_once()
    mock_llm.assert_called_once()
    mock_llm_instance.propose_revision.assert_called_once()
    mock_planner.assert_called_once()
    mock_planner_instance.patch_and_push.assert_called_once()

@prefect_test_harness
@patch('dags.flows.Storage')
@patch('dags.flows.Analytics')
@patch('dags.flows.LLM')
@patch('dags.flows.PlannerInterface')
def test_adapt_weekly_flow_no_flags(mock_planner, mock_llm, mock_analytics, mock_storage):
    """
    Test the adapt_weekly flow when no flags are detected.
    """
    # Configure mocks
    mock_storage_instance = MagicMock()
    mock_storage.return_value = mock_storage_instance
    mock_storage_instance.load_activities_for_week.return_value = [{"activityId": 3, "activityName": "Swimming"}]
    mock_storage_instance.load_hrv_for_week.return_value = [{"hrvSummary": {"avgHrv": 60}}]

    mock_analytics_instance = MagicMock()
    mock_analytics.return_value = mock_analytics_instance
    mock_analytics_instance.analyze_weekly_performance.return_value = {"performance": "good"}
    mock_analytics_instance.evaluate_flags.return_value = [] # No flags detected

    mock_llm_instance = MagicMock()
    mock_llm.return_value = mock_llm_instance

    mock_planner_instance = MagicMock()
    mock_planner.return_value = mock_planner_instance

    # Run the flow
    flows.adapt_weekly_flow()

    # Assertions
    mock_storage.assert_called_once()
    mock_storage_instance.load_activities_for_week.assert_called_once()
    mock_storage_instance.load_hrv_for_week.assert_called_once()
    mock_analytics.assert_called_once()
    mock_analytics_instance.analyze_weekly_performance.assert_called_once_with([{"activityId": 3, "activityName": "Swimming"}], [{"hrvSummary": {"avgHrv": 60}}])
    mock_analytics_instance.evaluate_flags.assert_called_once()
    mock_llm.assert_not_called() # LLM should not be called
    mock_planner.assert_not_called() # Planner should not be called