"""Garmin client utilities using the ``garmindb`` CLI."""

import json
import subprocess
import time
from typing import Any, Dict, Optional

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
                log_event(
                    "garmin_client_retry_attempt",
                    {"function": func.__name__, "tries_left": _tries - 1, "delay": _delay},
                )
                time.sleep(_delay)
                _tries -= 1
                _delay *= 2
            return func(*args, **kwargs)

        return wrapper

    return decorator


# Authentication and token refresh are handled by ``garmindb_cli.py``.
def login() -> None:
    """Placeholder for login via ``garmindb_cli.py``."""

    log_event("garmin_client_login_placeholder")
    print("Garmin authentication handled by garmindb_cli.py.")


def refresh_access_token() -> None:
    """Placeholder for token refresh via ``garmindb_cli.py``."""

    log_event("garmin_client_refresh_placeholder")
    print("Garmin token refresh handled by garmindb_cli.py.")


def _run_garmindb_cli(command_args: list) -> Optional[Dict[str, Any]]:
    """Run the ``garmindb_cli.py`` script as a subprocess."""

    command = ["python", "garmindb_cli.py"] + command_args
    log_event("garmin_client_subprocess_command", {"command": " ".join(command)})
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        log_event(
            "garmin_client_subprocess_completed",
            {
                "command": " ".join(command),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    except FileNotFoundError:
        log_event(
            "garmin_client_garmindb_cli_not_found",
            {"message": "garmindb_cli.py command not found. Is it in the PATH or current directory?"},
        )
        return None
    except Exception as e:  # pragma: no cover - defensive programming
        log_event("garmin_client_subprocess_exception", {"command": " ".join(command), "error": str(e)})
        return None


@retry()
def _run_cli(command_args: list) -> Optional[Dict[str, Any]]:
    return _run_garmindb_cli(command_args)


def get_activities(delta_only: bool = False):
    """Fetch activity data using ``garmindb_cli.py``."""

    log_event("garmin_client_get_activities_start", {"delta_only": delta_only})
    command_args = ["fetch", "activities"]
    if delta_only:
        command_args.append("--delta-only")

    result = _run_cli(command_args)
    if result and result["returncode"] == 0:
        try:
            activities = json.loads(result["stdout"])
            log_event("garmin_client_get_activities_success", {"count": len(activities)})
            return activities
        except json.JSONDecodeError as e:
            log_event(
                "garmin_client_get_activities_json_decode_error",
                {"error": str(e), "stdout": result["stdout"]},
            )
            return None
    else:
        log_event("garmin_client_get_activities_failed", {"result": result})
        return None


def get_hrv():
    """Fetch HRV data using ``garmindb_cli.py``."""

    log_event("garmin_client_get_hrv_start")
    command_args = ["fetch", "hrv"]
    result = _run_cli(command_args)
    if result and result["returncode"] == 0:
        try:
            hrv_data = json.loads(result["stdout"])
            log_event("garmin_client_get_hrv_success", {"count": len(hrv_data)})
            return hrv_data
        except json.JSONDecodeError as e:
            log_event(
                "garmin_client_get_hrv_json_decode_error",
                {"error": str(e), "stdout": result["stdout"]},
            )
            return None
    else:
        log_event("garmin_client_get_hrv_failed", {"result": result})
        return None


def upload_data(data_type: str, data: Any) -> bool:
    """Upload data to Garmin using ``garmindb_cli.py`` if supported."""

    log_event("garmin_client_upload_data_stub", {"data_type": data_type})
    print(f"Garmin upload_data function stub for {data_type}.")
    # Example of how you might call garmindb_cli.py if it supported uploads:
    # command_args = ["upload", data_type, json.dumps(data)]
    # result = _run_garmindb_cli(command_args)
    # return result and result["returncode"] == 0
    return False  # Indicate that upload is not implemented via this method


class GarminClient:
    """Thin wrapper around module-level Garmin client functions."""

    def login(self) -> None:  # pragma: no cover - wrapper delegates to function
        login()

    def refresh_access_token(self) -> None:  # pragma: no cover - wrapper delegates to function
        refresh_access_token()

    def get_activities(self, delta_only: bool = False):
        return get_activities(delta_only=delta_only)

    def get_hrv(self):
        return get_hrv()


__all__ = [
    "login",
    "refresh_access_token",
    "get_activities",
    "get_hrv",
    "upload_data",
    "GarminClient",
]

