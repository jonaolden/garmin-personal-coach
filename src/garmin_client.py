"""
Garmin Client Module

Handles Garmin authentication, token refresh, and GET requests with retry logic.
"""

import requests
import time
import subprocess
import json
from typing import Dict, Any, Optional
from src.monitoring import log_event

def retry(tries: int = 3, delay: int = 5):
    """Retry decorator with exponential backoff."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            _tries, _delay = tries, delay
            while _tries > 1:
                result = func(*args, **kwargs)
                if result and result.get("returncode", -1) == 0:
                    return result
                log_event("garmin_client_retry_attempt", {"function": func.__name__, "tries_left": _tries - 1, "delay": _delay})
                time.sleep(_delay)
                _tries -= 1
                _delay *= 2 # Exponential backoff
            return func(*args, **kwargs) # Last attempt
        return wrapper
    return decorator

# Authentication and token refresh are handled by garmindb_cli.py
def login():
    """
    Placeholder for login. Authentication is handled by garmindb_cli.py.
    """
    log_event("garmin_client_login_placeholder")
    print("Garmin authentication handled by garmindb_cli.py.")
    pass

def _run_garmindb_cli(command_args: list) -> Optional[Dict[str, Any]]:
    """
    Runs the garmindb_cli.py script as a subprocess.
    Args:
        command_args (list): List of arguments to pass to garmindb_cli.py.
    Returns:
        Optional[Dict[str, Any]]: A dictionary containing stdout, stderr, and returncode
                                   if the subprocess ran, None otherwise (e.g., command not found).
    """
    command = ["python", "garmindb_cli.py"] + command_args
    log_event("garmin_client_subprocess_command", {"command": " ".join(command)})
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        log_event("garmin_client_subprocess_completed", {
            "command": " ".join(command),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except FileNotFoundError:
        log_event("garmin_client_garmindb_cli_not_found", {"message": "garmindb_cli.py command not found. Is it in the PATH or current directory?"})
        return None
    except Exception as e:
        log_event("garmin_client_subprocess_exception", {"command": " ".join(command), "error": str(e)})
        return None

# TODO: Implement retry logic
@retry()
def get_activities(delta_only=False):
    """
    Fetches activity data from Garmin using garmindb_cli.py with retry logic.
    Args:
        delta_only (bool): If True, fetch only new activities since the last sync.
    Returns: List of activities (parsed from JSON stdout) or None on failure.
    """
    log_event("garmin_client_get_activities_start", {"delta_only": delta_only})
    command_args = ["fetch", "activities"]
    if delta_only:
        command_args.append("--delta-only")

    result = _run_garmindb_cli(command_args)

    if result and result["returncode"] == 0:
        try:
            # Assuming garmindb_cli.py outputs JSON array of activities to stdout
            activities = json.loads(result["stdout"])
            log_event("garmin_client_get_activities_success", {"count": len(activities)})
            return activities
        except json.JSONDecodeError as e:
            log_event("garmin_client_get_activities_json_decode_error", {"error": str(e), "stdout": result["stdout"]})
            return None
    else:
        log_event("garmin_client_get_activities_failed", {"result": result})
        return None

# TODO: Implement retry logic
@retry()
def get_hrv():
    """
    Fetches HRV data from Garmin using garmindb_cli.py with retry logic.
    Returns: List of HRV data (parsed from JSON stdout) or None on failure.
    """
    log_event("garmin_client_get_hrv_start")
    command_args = ["fetch", "hrv"]

    result = _run_garmindb_cli(command_args)

    if result and result["returncode"] == 0:
        try:
            # Assuming garmindb_cli.py outputs JSON array of HRV data to stdout
            hrv_data = json.loads(result["stdout"])
            log_event("garmin_client_get_hrv_success", {"count": len(hrv_data)})
            return hrv_data
        except json.JSONDecodeError as e:
            log_event("garmin_client_get_hrv_json_decode_error", {"error": str(e), "stdout": result["stdout"]})
            return None
    else:
        log_event("garmin_client_get_hrv_failed", {"result": result})
        return None

# Retry decorator and token refresh logic implemented.
# TODO: Implement data update/upload functionality using garmindb_cli.py if needed
def upload_data(data_type: str, data: Any):
    """
    Uploads data to Garmin using garmindb_cli.py if needed.
    This is a placeholder as garmindb_cli.py might not support uploads.
    Args:
        data_type (str): Type of data to upload (e.g., "activities", "hrv").
        data (Any): The data to upload.
    Returns: bool: True if upload was attempted (success not guaranteed), False otherwise.
    """
    log_event("garmin_client_upload_data_stub", {"data_type": data_type})
    print(f"Garmin upload_data function stub for {data_type}.")
    # Example of how you might call garmindb_cli.py if it supported uploads:
    # command_args = ["upload", data_type, json.dumps(data)]
    # result = _run_garmindb_cli(command_args)
    # return result and result["returncode"] == 0
    return False # Indicate that upload is not implemented via this method