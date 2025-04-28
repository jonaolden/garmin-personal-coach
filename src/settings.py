import os
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class RetrySettings(BaseModel):
    max_attempts: int = Field(default=5)
    base: int = Field(default=2)
    jitter: bool = Field(default=True)

class Settings(BaseSettings):
    overrides_allowed: bool = Field(default=True)
    # thresholds
    ramp_percentage_max: float = Field(default=0.10)
    ctl_atl_ratio_max: float = Field(default=1.3)
    hrv_drop_zscore: float = Field(default=-1.0)
    sleep_min_hours: int = Field(default=6)
    llm_volume_change_max: float = Field(default=0.20)
    # retries & back-off
    retry: RetrySettings = Field(default_factory=RetrySettings)
    # scheduling
    sync_daily_cron: str = Field(default="0 1 * * *")
    sync_catchup_cron: str = Field(default="0 10 * * *")
    adapt_weekly_cron: str = Field(default="0 17 * * SUN")
    # llm settings
    openai_api_key: Optional[str] = Field(default=None, description="API key for OpenAI")
    llm_model: str = Field(default="gpt-4o-mini", description="The LLM model to use for plan revisions")

    # User Goals and Constraints
    goal_date: Optional[str] = Field(default=None, description="Goal date in YYYY-MM-DD format")
    goal_type: Optional[str] = Field(default=None, description="Goal distance or type")
    available_weekdays: list[str] = Field(default_factory=list, description="Available training weekdays")
    blocked_dates: list[str] = Field(default_factory=list, description="Blocked dates in YYYY-MM-DD format")

    model_config = SettingsConfigDict(
        env_prefix='GARMIN_PIPELINE_',
        env_nested_delimiter='__',
        case_sensitive=False,
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore', # Allow extra env vars not in the model
    )

def load_settings(env: Optional[str] = None) -> Settings:
    """
    Loads settings from default.yaml, environment-specific yaml, user_goals.yaml, and environment variables.
    Environment variables take precedence.
    """
    settings_files = ["config/default.yaml", "config/user_goals.yaml"]
    if env:
        env_file = f"config/{env}.yaml"
        if os.path.exists(env_file):
            settings_files.append(env_file)
        else:
            print(f"Warning: Environment file {env_file} not found.")

    settings_dict = {}
    for file_path in settings_files:
        try:
            with open(file_path, 'r') as f:
                content = yaml.safe_load(f)
                if content:
                    settings_dict.update(content)
        except FileNotFoundError:
            # user_goals.yaml is optional, others are not
            if file_path != "config/user_goals.yaml":
                print(f"Warning: Settings file {file_path} not found.")
        except yaml.YAMLError as e:
            print(f"Error loading YAML file {file_path}: {e}")

    # Pydantic BaseSettings will automatically load from environment variables
    # and merge with the initial values (which come from YAML here).
    # Environment variables take precedence over the initial values.
    settings = Settings(**settings_dict)

    return settings

if __name__ == "__main__":
    # Example usage:
    # To load staging settings and environment variables:
    # settings = load_settings(env="staging")
    # print(settings)

    # To load default settings and environment variables:
    settings = load_settings()
    print(settings)