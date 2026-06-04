import os
from pydantic import BaseModel, Field

class AppConfig(BaseModel):
    # Files or extensions we generally want to ignore during review
    ignored_extensions: list[str] = Field(
        default=[".png", ".jpg", ".jpeg", ".gif", ".pdf", ".lock", "-lock.json"]
    )
    ignored_files: list[str] = Field(
        default=["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"]
    )
    # Default fallback branch if the remote branch is not set
    default_comparison_branch: str = "main"

config = AppConfig()