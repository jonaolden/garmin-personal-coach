"""
Planner Interface Module

Applies RFC6902 JSON Patch and interacts with the garmin_planner CLI tool.
Adheres to the fail-open principle.
"""

import subprocess
import json
import yaml
import jsonpatch
import os
import shutil
from src.monitoring import log_event

# TODO: Implement logic to apply JSON Patch locally before pushing (optional but good practice)
# TODO: Implement interaction with garmin_planner CLI

def patch_and_push(diff: str):
    """
    Applies the RFC6902 JSON Patch and pushes the updated plan using garmin_planner.
    Args:
        diff (str): The RFC6902 JSON Patch string.
    """
    log_event("planner_patch_and_push_start", {"diff": diff})

    plan_dir = "plans"
    current_plan_path = os.path.join(plan_dir, "current_plan.yaml")
    patched_plan_path = os.path.join(plan_dir, "patched_plan.yaml")

    # Ensure plans directory exists
    os.makedirs(plan_dir, exist_ok=True)

    current_plan = {}
    # Load the current plan from plans/ (gitignored)
    try:
        with open(current_plan_path, 'r') as f:
            current_plan = yaml.safe_load(f) or {}
        log_event("planner_current_plan_loaded", {"path": current_plan_path})
    except FileNotFoundError:
        log_event("planner_current_plan_not_found", {"path": current_plan_path, "message": "Creating a new empty plan."})
        current_plan = {} # Start with an empty plan if file not found
    except Exception as e:
        log_event("planner_current_plan_load_error", {"path": current_plan_path, "error": str(e)})
        # Adhere to fail-open: log error but continue with empty plan

    # Apply the diff to the current plan
    try:
        patch = json.loads(diff)
        patched_plan = jsonpatch.apply_patch(current_plan, patch)
        log_event("planner_patch_applied")
    except jsonpatch.JsonPatchException as e:
        log_event("planner_patch_application_failed", {"error": str(e), "diff": diff})
        # Adhere to fail-open: log failure and stop here
        log_event("planner_patch_and_push_end", {"status": "failed_patch_application"})
        return
    except json.JSONDecodeError as e:
        log_event("planner_diff_json_decode_error", {"error": str(e), "diff": diff})
        # Adhere to fail-open: log failure and stop here
        log_event("planner_patch_and_push_end", {"status": "failed_diff_decode"})
        return
    except Exception as e:
        log_event("planner_patch_application_exception", {"error": str(e), "diff": diff})
        # Adhere to fail-open: log failure and stop here
        log_event("planner_patch_and_push_end", {"status": "failed_patch_exception"})
        return

    # Save the patched plan temporarily
    try:
        with open(patched_plan_path, 'w') as f:
            yaml.dump(patched_plan, f)
        log_event("planner_patched_plan_saved", {"path": patched_plan_path})
    except Exception as e:
        log_event("planner_patched_plan_save_error", {"path": patched_plan_path, "error": str(e)})
        # Adhere to fail-open: log failure and stop here
        log_event("planner_patch_and_push_end", {"status": "failed_save_patched_plan"})
        return

    # Invoke garmin_planner as a subprocess
    command = ["garmin_planner", "push", "--plan", patched_plan_path]
    log_event("planner_subprocess_command", {"command": " ".join(command)})
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            log_event("planner_subprocess_failed", {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            })
            # Adhere to fail-open: log failure but do not raise exception
            log_event("planner_patch_and_push_end", {"status": "failed_subprocess"})
        else:
            log_event("planner_subprocess_succeeded", {
                "stdout": result.stdout,
                "stderr": result.stderr # stderr might contain warnings even on success
            })
            # Update the local cache in plans/ on success
            try:
                shutil.copyfile(patched_plan_path, current_plan_path)
                log_event("planner_local_cache_updated", {"path": current_plan_path})
            except Exception as e:
                log_event("planner_local_cache_update_error", {"path": current_plan_path, "error": str(e)})
                # Adhere to fail-open: log failure but do not stop the process

            log_event("planner_patch_and_push_end", {"status": "succeeded"})

    except FileNotFoundError:
        log_event("planner_garmin_planner_not_found", {"message": "garmin_planner command not found. Is it in the PATH?"})
        # Adhere to fail-open
        log_event("planner_patch_and_push_end", {"status": "failed_command_not_found"})
    except Exception as e:
        log_event("planner_subprocess_exception", {"error": str(e)})
        # Adhere to fail-open
        log_event("planner_patch_and_push_end", {"status": "failed_subprocess_exception"})

# TODO: Add error handling and logging for subprocess calls (Done in patch_and_push)
# TODO: Manage the local plans/ cache (Basic implementation added in patch_and_push)

# TODO: Add error handling and logging for subprocess calls
# TODO: Manage the local plans/ cache