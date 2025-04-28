"""
Unit and Integration Tests for the Garmin Client Module.
"""

import pytest
from unittest.mock import patch, MagicMock

# Import garmin_client module
from src import garmin_client

# TODO: Add unit tests for authentication, token refresh, and retry logic
@patch('src.garmin_client.requests.post')
def test_garmin_login(mock_post):
    """
    Test Garmin login and token refresh.
    """
    # Mock successful initial login
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"access_token": "new_access_token", "refresh_token": "new_refresh_token"}

    client = garmin_client.GarminClient("test_email", "test_password")
    client.login()

    mock_post.assert_called_once()
    assert client.access_token == "new_access_token"
    assert client.refresh_token == "new_refresh_token"

@patch('src.garmin_client.requests.post')
def test_garmin_login_failure(mock_post):
    """
    Test Garmin login failure.
    """
    # Mock failed login
    mock_post.return_value.status_code = 401

    client = garmin_client.GarminClient("test_email", "test_password")
    with pytest.raises(Exception): # Assuming login raises an exception on failure
        client.login()

    mock_post.assert_called_once()

@patch('src.garmin_client.requests.post')
def test_garmin_refresh_token(mock_post):
    """
    Test Garmin token refresh.
    """
    # Mock successful token refresh
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"access_token": "refreshed_access_token", "refresh_token": "new_refresh_token"}

    client = garmin_client.GarminClient("test_email", "test_password")
    client.refresh_token = "old_refresh_token" # Set an old refresh token
    client.refresh_access_token()

    mock_post.assert_called_once()
    assert client.access_token == "refreshed_access_token"
    assert client.refresh_token == "new_refresh_token"

@patch('src.garmin_client.requests.post')
def test_garmin_refresh_token_failure(mock_post):
    """
    Test Garmin token refresh failure.
    """
    # Mock failed token refresh
    mock_post.return_value.status_code = 401

    client = garmin_client.GarminClient("test_email", "test_password")
    client.refresh_token = "old_refresh_token" # Set an old refresh token
    with pytest.raises(Exception): # Assuming refresh_access_token raises an exception on failure
        client.refresh_access_token()

    mock_post.assert_called_once()

@patch('src.garmin_client.requests.get')
def test_get_activities_integration(mock_get):
    """
    Integration test for get_activities using mocks.
    """
    # Mock successful API call
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{"activityId": 123, "activityName": "Running"}]

    client = garmin_client.GarminClient("test_email", "test_password")
    client.access_token = "fake_access_token" # Set a fake access token
    activities = client.get_activities("2023-01-01", "2023-01-07")

    mock_get.assert_called_once()
    assert len(activities) == 1
    assert activities[0]["activityName"] == "Running"

@patch('src.garmin_client.requests.get')
def test_get_hrv_integration(mock_get):
    """
    Integration test for get_hrv using mocks.
    """
    # Mock successful API call
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"hrvSummary": {"avgHrv": 50}}

    client = garmin_client.GarminClient("test_email", "test_password")
    client.access_token = "fake_access_token" # Set a fake access token
    hrv_data = client.get_hrv("2023-01-01")

    mock_get.assert_called_once()
    assert hrv_data["hrvSummary"]["avgHrv"] == 50

@patch('src.garmin_client.requests.get')
def test_get_activities_retry(mock_get):
    """
    Test get_activities with retry logic.
    """
    # Configure the mock to fail twice then succeed
    mock_get.side_effect = [
        MagicMock(status_code=500),
        MagicMock(status_code=500),
        MagicMock(status_code=200, json=lambda: [{"activityId": 456, "activityName": "Cycling"}])
    ]

    client = garmin_client.GarminClient("test_email", "test_password")
    client.access_token = "fake_access_token" # Set a fake access token
    # Assuming the client has a retry mechanism built-in
    activities = client.get_activities("2023-01-01", "2023-01-07")

    # Check that the mock was called three times (2 retries + 1 success)
    assert mock_get.call_count == 3
    assert len(activities) == 1
    assert activities[0]["activityName"] == "Cycling"

@patch('src.garmin_client.requests.get')
def test_get_hrv_retry(mock_get):
    """
    Test get_hrv with retry logic.
    """
    # Configure the mock to fail twice then succeed
    mock_get.side_effect = [
        MagicMock(status_code=500),
        MagicMock(status_code=500),
        MagicMock(status_code=200, json=lambda: {"hrvSummary": {"avgHrv": 60}})
    ]

    client = garmin_client.GarminClient("test_email", "test_password")
    client.access_token = "fake_access_token" # Set a fake access token
    # Assuming the client has a retry mechanism built-in
    hrv_data = client.get_hrv("2023-01-01")

    # Check that the mock was called three times (2 retries + 1 success)
    assert mock_get.call_count == 3
    assert hrv_data["hrvSummary"]["avgHrv"] == 60

@patch('src.garmin_client.requests.get')
def test_get_activities_failure(mock_get):
    """
    Test get_activities failure path.
    """
    # Mock failed API call
    mock_get.return_value.status_code = 400

    client = garmin_client.GarminClient("test_email", "test_password")
    client.access_token = "fake_access_token" # Set a fake access token
    with pytest.raises(Exception): # Assuming get_activities raises an exception on failure
        client.get_activities("2023-01-01", "2023-01-07")

    mock_get.assert_called_once()

@patch('src.garmin_client.requests.get')
def test_get_hrv_failure(mock_get):
    """
    Test get_hrv failure path.
    """
    # Mock failed API call
    mock_get.return_value.status_code = 400

    client = garmin_client.GarminClient("test_email", "test_password")
    client.access_token = "fake_access_token" # Set a fake access token
    with pytest.raises(Exception): # Assuming get_hrv raises an exception on failure
        client.get_hrv("2023-01-01")

    mock_get.assert_called_once()