"""Base scanner adapter with sandbox controls."""

import asyncio
import os
import re
import shlex
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings


@dataclass
class ScanResult:
    scanner: str
    success: bool
    findings: list[dict[str, Any]] = field(default_factory=list)
    raw_output: str | None = None
    error: str | None = None
    duration_seconds: float = 0.0


class BaseScannerAdapter(ABC):
    scanner_type: str = "base"
    allowed_chars = re.compile(r"^[a-zA-Z0-9\.\-:/_%?=&#]+$")

    def __init__(self) -> None:
        self.settings = get_settings()

    def sanitize_target(self, target: str) -> str:
        target = target.strip()
        if not self.allowed_chars.match(target.replace(" ", "")):
            raise ValueError("Target contains invalid characters")
        if any(c in target for c in (";", "|", "&", "$", "`", "(", ")", "{", "}", "\n", "\r")):
            raise ValueError("Target contains shell metacharacters")
        return target

    async def run_subprocess(
        self,
        cmd: list[str],
        timeout: int | None = None,
        cwd: str | None = None,
    ) -> tuple[int, str, str]:
        timeout = timeout or self.settings.scan_timeout_seconds
        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": tempfile.gettempdir(),
            "LANG": "C.UTF-8",
        }

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise TimeoutError(
                f"Scanner {self.scanner_type} timed out after {timeout}s"
            ) from exc

        return (
            process.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    def build_safe_command(self, binary: str, args: list[str]) -> list[str]:
        return [binary] + [shlex.quote(a) if " " in a else a for a in args]

    @abstractmethod
    async def scan(self, target: str, options: dict[str, Any] | None = None) -> ScanResult:
        pass
