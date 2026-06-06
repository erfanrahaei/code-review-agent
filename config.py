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
    
    # LLM Settings
    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    api_base: str = Field(default_factory=lambda: os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"))
    model_name: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

config = AppConfig()