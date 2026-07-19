from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Java Migration Assistant"
    debug: bool = False

    # Base directory is backend/
    base_dir: Path = Path(__file__).resolve().parent.parent
    upload_dir: Path = base_dir / "uploads"
    workspace_dir: Path = base_dir / "workspace"
    reports_dir: Path   = base_dir / "workspace" / "reports"    # HTML reports
    backups_dir: Path   = base_dir / "workspace" / "backups"    # pre-migration backups
    build_logs_dir: Path = base_dir / "workspace" / "build-logs" # per-attempt Maven logs
    output_dir: Path    = base_dir / "workspace" / "output"      # generated JARs/WARs

    openai_api_key: str = ""          # set in .env — empty disables AI fix
    openai_model: str   = "gpt-4o-mini"
    build_max_retries: int = 5

    max_upload_size_mb: int = 100

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure runtime directories exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.workspace_dir.mkdir(parents=True, exist_ok=True)
settings.reports_dir.mkdir(parents=True, exist_ok=True)
settings.backups_dir.mkdir(parents=True, exist_ok=True)
settings.build_logs_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
