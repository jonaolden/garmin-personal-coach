import os
import sys
from unittest.mock import patch

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src import garmin_client


def _success(payload: str):
    return {"stdout": payload, "stderr": "", "returncode": 0}


def _failure():
    return {"stdout": "", "stderr": "", "returncode": 1}


@patch("src.garmin_client._run_garmindb_cli")
def test_get_activities_success(mock_cli):
    mock_cli.return_value = _success('[{"id": 1}]')
    activities = garmin_client.get_activities()
    mock_cli.assert_called_once_with(["fetch", "activities"])
    assert activities == [{"id": 1}]


@patch("src.garmin_client._run_garmindb_cli")
def test_get_activities_delta_only(mock_cli):
    mock_cli.return_value = _success("[]")
    garmin_client.get_activities(delta_only=True)
    mock_cli.assert_called_once_with(["fetch", "activities", "--delta-only"])


@patch("src.garmin_client.time.sleep", return_value=None)
def test_get_activities_retry(mock_sleep):
    with patch(
        "src.garmin_client._run_garmindb_cli",
        side_effect=[_failure(), _failure(), _success('[{"id": 2}]')],
    ) as mock_cli:
        activities = garmin_client.get_activities()
        assert mock_cli.call_count == 3
        assert activities == [{"id": 2}]


@patch("src.garmin_client.time.sleep", return_value=None)
def test_get_hrv_retry(mock_sleep):
    with patch(
        "src.garmin_client._run_garmindb_cli",
        side_effect=[_failure(), _failure(), _success('[{"avg": 50}]')],
    ) as mock_cli:
        hrv = garmin_client.get_hrv()
        assert mock_cli.call_count == 3
        assert hrv == [{"avg": 50}]


@patch("src.garmin_client._run_garmindb_cli", return_value=_failure())
@patch("src.garmin_client.time.sleep", return_value=None)
def test_get_activities_failure(mock_sleep, mock_cli):
    result = garmin_client.get_activities()
    assert result is None
    assert mock_cli.call_count == 3


@patch("src.garmin_client._run_garmindb_cli", return_value=_failure())
@patch("src.garmin_client.time.sleep", return_value=None)
def test_get_hrv_failure(mock_sleep, mock_cli):
    result = garmin_client.get_hrv()
    assert result is None
    assert mock_cli.call_count == 3


def test_garmin_client_class_wraps_functions():
    with patch("src.garmin_client.login") as login_mock, \
        patch("src.garmin_client.refresh_access_token") as refresh_mock, \
        patch("src.garmin_client.get_activities", return_value=[]) as activities_mock, \
        patch("src.garmin_client.get_hrv", return_value={}) as hrv_mock:
        client = garmin_client.GarminClient()
        client.login()
        client.refresh_access_token()
        client.get_activities()
        client.get_hrv()
        login_mock.assert_called_once()
        refresh_mock.assert_called_once()
        activities_mock.assert_called_once_with(delta_only=False)
        hrv_mock.assert_called_once()

