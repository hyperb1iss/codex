from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from .cancellation import CancelToken

ApprovalMode = Literal["never", "on-request", "on-failure", "untrusted"]
SandboxMode = Literal["read-only", "workspace-write", "danger-full-access"]
ModelReasoningEffort = Literal["minimal", "low", "medium", "high", "xhigh"]


@dataclass(frozen=True)
class CodexOptions:
    codex_path_override: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    env: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class ThreadOptions:
    model: Optional[str] = None
    sandbox_mode: Optional[SandboxMode] = None
    working_directory: Optional[str] = None
    skip_git_repo_check: bool = False
    model_reasoning_effort: Optional[ModelReasoningEffort] = None
    network_access_enabled: Optional[bool] = None
    web_search_enabled: Optional[bool] = None
    approval_policy: Optional[ApprovalMode] = None
    additional_directories: Optional[List[str]] = None


@dataclass(frozen=True)
class TurnOptions:
    output_schema: Optional[Dict[str, Any]] = None
    timeout_s: Optional[float] = None
    cancel_token: Optional[CancelToken] = None
