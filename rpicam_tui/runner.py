"""Async subprocess execution for rpicam-still / rpicam-vid.

Runs the argv list built by command_builder.py using asyncio subprocess APIs
(never shell=True), streams output line-by-line to a callback, and supports
cancellation via SIGINT/terminate. Falls back to a "dry run" that only logs
the command when the target binary isn't on PATH (e.g. developing off-Pi).
"""
from __future__ import annotations

import asyncio
import shutil
import signal
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional, Union

OnLine = Callable[[str], Union[None, Awaitable[None]]]


@dataclass
class RunResult:
    command: list[str]
    returncode: Optional[int]
    started_at: float
    ended_at: float
    output: str
    dry_run: bool = False
    cancelled: bool = False

    @property
    def duration(self) -> float:
        return self.ended_at - self.started_at


class BinaryNotFoundError(RuntimeError):
    pass


class CaptureRunner:
    """Owns at most one in-flight rpicam-* process at a time."""

    def __init__(self) -> None:
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._cancelled = False

    @staticmethod
    def binary_available(binary: str) -> bool:
        return shutil.which(binary) is not None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def run(
        self,
        argv: list[str],
        on_line: Optional[OnLine] = None,
        dry_run: bool = False,
    ) -> RunResult:
        """Run argv[0] with argv[1:] as arguments, streaming output to on_line.

        If dry_run is True, or the binary can't be found on PATH, no process
        is spawned -- the command is just reported via on_line so the tool
        stays usable on a dev machine without a camera attached.
        """
        started = time.time()
        self._cancelled = False
        binary = argv[0]

        async def emit(line: str) -> None:
            if on_line is None:
                return
            result = on_line(line)
            if asyncio.iscoroutine(result):
                await result

        if dry_run or not self.binary_available(binary):
            reason = "dry-run mode" if dry_run else f"'{binary}' not found on PATH"
            await emit(f"[{reason}] would run: {' '.join(argv)}")
            ended = time.time()
            return RunResult(
                command=argv,
                returncode=0,
                started_at=started,
                ended_at=ended,
                output="",
                dry_run=True,
            )

        self._proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        lines: list[str] = []
        assert self._proc.stdout is not None
        try:
            while True:
                raw = await self._proc.stdout.readline()
                if not raw:
                    break
                text = raw.decode(errors="replace").rstrip("\n")
                lines.append(text)
                await emit(text)
            returncode = await self._proc.wait()
        finally:
            proc, self._proc = self._proc, None

        ended = time.time()
        return RunResult(
            command=argv,
            returncode=returncode,
            started_at=started,
            ended_at=ended,
            output="\n".join(lines),
            cancelled=self._cancelled,
        )

    def cancel(self) -> bool:
        """Ask the running process to stop, mirroring a Ctrl+C in a real shell.

        Returns True if a running process was signalled, False if nothing to cancel.
        """
        if not self.running:
            return False
        self._cancelled = True
        assert self._proc is not None
        try:
            self._proc.send_signal(signal.SIGINT)
        except (ProcessLookupError, ValueError):
            return False
        return True

    def kill(self) -> bool:
        """Force-terminate the running process (used if SIGINT is ignored)."""
        if not self.running:
            return False
        assert self._proc is not None
        try:
            self._proc.terminate()
        except ProcessLookupError:
            return False
        return True
