"""
Analytics Module

Computes training load metrics (CTL/ATL), HRV z-scores, and generates flags
based on configured thresholds.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from src.settings import Settings # Import Settings class

# Constants for CTL/ATL calculation (days)
CTL_DAYS = 42
ATL_DAYS = 7

def compute_ctl_atl(activities_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes Chronic Training Load (CTL), Acute Training Load (ATL), and Training Stress Balance (TSB).
    Assumes activities_df has 'timestamp' (datetime) and 'tss' (numeric) columns.
    Args:
        activities_df (pd.DataFrame): DataFrame containing activity data.
    Returns: Dict[str, Any]: Dictionary containing computed metrics (e.g., {'ctl': 50, 'atl': 45, 'tsb': 5}).
    """
    if activities_df.empty or 'timestamp' not in activities_df.columns or 'tss' not in activities_df.columns:
        print("Analytics compute_ctl_atl: Input DataFrame is empty or missing required columns.")
        return {"ctl": 0, "atl": 0, "tsb": 0}

    # Ensure data is sorted by timestamp
    activities_df = activities_df.sort_values(by='timestamp').copy()

    # Calculate EMA for CTL and ATL
    # Pandas ewm uses alpha = 2/(span+1)
    activities_df['ctl'] = activities_df['tss'].ewm(span=CTL_DAYS, adjust=False).mean()
    activities_df['atl'] = activities_df['tss'].ewm(span=ATL_DAYS, adjust=False).mean()

    # TSB = CTL - ATL
    activities_df['tsb'] = activities_df['ctl'] - activities_df['atl']

    # Get the latest values
    latest_metrics = activities_df.iloc[-1][['ctl', 'atl', 'tsb']].to_dict()

    print(f"Analytics compute_ctl_atl: Computed CTL={latest_metrics['ctl']:.2f}, ATL={latest_metrics['atl']:.2f}, TSB={latest_metrics['tsb']:.2f}")
    return latest_metrics

def compute_hrv_zscore(hrv_data: List[Dict[str, Any]]) -> Optional[float]:
    """
    Computes the HRV z-score based on a rolling baseline.
    Assumes hrv_data is a list of dictionaries with a 'hrv' key (numeric).
    Args:
        hrv_data (List[Dict[str, Any]]): List of dictionaries containing HRV data.
    Returns: Optional[float]: The latest HRV z-score, or None if insufficient data.
    """
    if not hrv_data:
        print("Analytics compute_hrv_zscore: Input HRV data is empty.")
        return None

    # Convert list of dicts to DataFrame
    hrv_df = pd.DataFrame(hrv_data)

    if 'hrv' not in hrv_df.columns:
         print("Analytics compute_hrv_zscore: Input HRV data missing 'hrv' column.")
         return None

    # Calculate rolling mean and standard deviation (e.g., 30-day rolling window)
    window_size = 30 # TODO: Make window size configurable via settings
    if len(hrv_df) < window_size:
        print(f"Analytics compute_hrv_zscore: Insufficient data ({len(hrv_df)} points) for {window_size}-day rolling window.")
        return None

    hrv_df['hrv_mean'] = hrv_df['hrv'].rolling(window=window_size).mean()
    hrv_df['hrv_std'] = hrv_df['hrv'].rolling(window=window_size).std()

    # Calculate z-score
    hrv_df['hrv_zscore'] = (hrv_df['hrv'] - hrv_df['hrv_mean']) / hrv_df['hrv_std']

    # Get the latest z-score
    latest_zscore = hrv_df['hrv_zscore'].iloc[-1]

    print(f"Analytics compute_hrv_zscore: Latest HRV z-score: {latest_zscore:.2f}")
    return latest_zscore


def evaluate_flags(metrics: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Evaluates metrics against configured thresholds from settings and generates flags.
    Args:
        metrics (Dict[str, Any]): Dictionary of computed metrics (should include 'ctl', 'atl', 'hrv_zscore').
        settings (Settings): The application settings object.
    Returns: Dict[str, Any]: Dictionary of flags (e.g., {'high_ramp': True, 'low_hrv': False}).
    """
    flags = {}
    ctl = metrics.get('ctl', 0)
    atl = metrics.get('atl', 0)
    hrv_zscore = metrics.get('hrv_zscore')

    # Evaluate high training ramp
    # Ramp Rate = (ATL - Previous ATL) / Previous ATL (or similar, simplified here as ATL/CTL ratio)
    # A common flag is based on the ATL/CTL ratio or absolute ramp (ATL - CTL)
    # Using ATL/CTL ratio as per settings
    if ctl > 0 and atl / ctl > settings.ctl_atl_ratio_max:
         flags['high_atl_ctl_ratio'] = True
         print(f"Flagged: High ATL/CTL ratio ({atl/ctl:.2f}) > threshold ({settings.ctl_atl_ratio_max})")
    else:
         flags['high_atl_ctl_ratio'] = False


    # Evaluate low HRV
    if hrv_zscore is not None and hrv_zscore < settings.hrv_drop_zscore:
        flags['low_hrv'] = True
        print(f"Flagged: Low HRV z-score ({hrv_zscore:.2f}) < threshold ({settings.hrv_drop_zscore})")
    else:
        flags['low_hrv'] = False

    # TODO: Add more flags based on other metrics and settings (e.g., sleep, TSB)
    # Example: Low TSB flag
    tsb = metrics.get('tsb', 0)
    if tsb < -10: # Example threshold for low TSB
        flags['low_tsb'] = True
        print(f"Flagged: Low TSB ({tsb:.2f}) < threshold (-10)")
    else:
        flags['low_tsb'] = False


    print(f"Analytics evaluate_flags: Generated flags: {flags}")
    return flags

# CTL/ATL calculation, HRV z-score calculation, flag generation, and settings integration implemented.