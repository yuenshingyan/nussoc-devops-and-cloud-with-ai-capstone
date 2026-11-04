"""Bound one trusted release command; allow client-internal retries, never relaunch it."""

from dataclasses import dataclass
from math import isfinite
from os import killpg, read
from selectors import EVENT_READ, DefaultSelector
from signal import SIGKILL
from subprocess import PIPE, Popen
from time import monotonic

OUTPUT_LIMIT = 1024 * 1024
MAX_RELEASE_SECONDS = 600


@dataclass(frozen=True)
class CommandResult:
    """Bounded stdout only; provider stderr is never returned or logged by this helper."""

    returncode: int
    stdout: bytes


def run_command(command: list[str], environment: dict[str, str], deadline: float) -> CommandResult:
    """Run once under a caller-owned monotonic deadline, draining both output pipes.

    This is for fixed administrator-owned commands, not upstream scripts. The deadline must
    fit inside the remaining ten-minute release budget. Internal tool retries share that
    budget. Failure/timeout is not proof that a remote write did not happen. No retry or
    rollback occurs here. Process-group cleanup does not establish Jenkins abort/restart
    behavior or cancel an operation already accepted by a remote server.
    """
    if type(deadline) not in {int, float}:
        raise ValueError("RELEASE_COMMAND_BUDGET_INVALID")
    try:
        remaining = deadline - monotonic()
    except OverflowError:
        raise ValueError("RELEASE_COMMAND_BUDGET_INVALID") from None
    if not isfinite(remaining) or not 0 < remaining <= MAX_RELEASE_SECONDS:
        raise ValueError("RELEASE_COMMAND_BUDGET_INVALID")
    if (
        type(command) is not list
        or not command
        or any(type(argument) is not str or "\x00" in argument for argument in command)
        or not command[0].startswith("/")
    ):
        raise ValueError("RELEASE_COMMAND_INVALID")
    if type(environment) is not dict or any(
        type(key) is not str
        or not key
        or "=" in key
        or "\x00" in key
        or type(value) is not str
        or "\x00" in value
        for key, value in environment.items()
    ):
        raise ValueError("RELEASE_COMMAND_ENVIRONMENT_INVALID")
    try:
        process = Popen(
            command,
            env=environment,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            start_new_session=True,
        )
    except OSError:
        raise RuntimeError("RELEASE_COMMAND_START_FAILED") from None
    output = bytearray()
    consumed = 0
    # No provider text is used in exceptions; callers must also avoid logging raw stdout.
    try:
        process.stdin.close()
        with DefaultSelector() as selector:
            selector.register(process.stdout, EVENT_READ, True)
            selector.register(process.stderr, EVENT_READ, False)
            while selector.get_map() or process.poll() is None:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError("RELEASE_COMMAND_TIMEOUT_OUTCOME_UNKNOWN")
                for key, _ in selector.select(min(remaining, 0.1)):
                    chunk = read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    consumed += len(chunk)
                    if consumed > OUTPUT_LIMIT:
                        raise RuntimeError("RELEASE_COMMAND_OUTPUT_LIMIT_OUTCOME_UNKNOWN")
                    if key.data:
                        output.extend(chunk)
        return CommandResult(process.returncode, bytes(output))
    finally:
        # We created this process group; never kill the agent's or another caller's group.
        try:
            killpg(process.pid, SIGKILL)
        except ProcessLookupError:
            pass
        finally:
            process.wait()
            process.stdout.close()
            process.stderr.close()
            process.stdin.close()
