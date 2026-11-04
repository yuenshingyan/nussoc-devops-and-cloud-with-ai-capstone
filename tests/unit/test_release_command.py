from os import environ
from pathlib import Path
from sys import executable
from time import monotonic

from pytest import mark, raises

from scripts.release_command import OUTPUT_LIMIT, CommandResult, run_command


def invoke(source: str, seconds: float = 5) -> CommandResult:
    return run_command([executable, "-I", "-c", source], dict(environ), monotonic() + seconds)


def test_success_returns_stdout_but_not_provider_stderr():
    result = invoke("import sys; print('digest'); print('private-provider-text',file=sys.stderr)")
    assert result.returncode == 0
    assert result.stdout == b"digest\n"
    assert not hasattr(result, "stderr")


def test_failure_is_returned_without_relaunching_command(tmp_path):
    marker = tmp_path / "attempts"
    source = (
        f"from pathlib import Path; p=Path({str(marker)!r}); "
        "p.write_text((p.read_text() if p.exists() else '') + 'one'); exit(7)"
    )
    result = invoke(source)
    assert result.returncode == 7
    assert marker.read_text() == "one"


def test_deadline_stops_command_with_ambiguous_outcome():
    with raises(TimeoutError, match="TIMEOUT_OUTCOME_UNKNOWN"):
        invoke("import time; time.sleep(60)", seconds=0.3)


@mark.parametrize("stream", ["stdout", "stderr"])
def test_output_limit_stops_command_without_exposing_output(stream):
    source = f"import sys; sys.{stream}.buffer.write(b'x'*{OUTPUT_LIMIT + 1}); sys.{stream}.flush()"
    with raises(RuntimeError, match="OUTPUT_LIMIT_OUTCOME_UNKNOWN"):
        invoke(source)


def test_both_pipes_are_drained_without_deadlock():
    result = invoke(
        "import sys; "
        "sys.stderr.buffer.write(b'e'*200000); sys.stderr.flush(); "
        "sys.stdout.buffer.write(b'o'*200000); sys.stdout.flush()"
    )
    assert result.returncode == 0
    assert result.stdout == b"o" * 200000


def test_exact_output_limit_is_accepted():
    result = invoke(f"import sys; sys.stdout.buffer.write(b'x'*{OUTPUT_LIMIT})")
    assert result.stdout == b"x" * OUTPUT_LIMIT


@mark.parametrize("deadline", [True, "later", float("nan"), float("inf"), 0, 10**1000])
def test_invalid_deadline_is_rejected_before_execution(deadline):
    with raises(ValueError, match="BUDGET_INVALID"):
        run_command([executable], {}, deadline)


def test_budget_cannot_exceed_overall_release_limit():
    with raises(ValueError, match="BUDGET_INVALID"):
        run_command([executable], {}, monotonic() + 601)


@mark.parametrize("command", [[], ["python"], [executable, None], [executable, "bad\x00arg"]])
def test_invalid_command_is_rejected(command):
    with raises(ValueError, match="COMMAND_INVALID"):
        run_command(command, {}, monotonic() + 5)


@mark.parametrize("environment", [None, {"BAD=KEY": "value"}, {"X": None}, {"X": "bad\x00value"}])
def test_invalid_environment_is_rejected_without_exposing_values(environment):
    with raises(ValueError, match="^RELEASE_COMMAND_ENVIRONMENT_INVALID$"):
        run_command([executable], environment, monotonic() + 5)


def test_start_failure_has_no_provider_path_in_error(tmp_path):
    with raises(RuntimeError, match="^RELEASE_COMMAND_START_FAILED$"):
        run_command([str(tmp_path / "missing-private-name")], {}, monotonic() + 5)


def test_timeout_also_stops_descendant_holding_pipes(tmp_path):
    marker = tmp_path / "descendant-finished"
    started = tmp_path / "descendant-started"
    child = (
        f"import time; from pathlib import Path; Path({str(started)!r}).touch(); "
        f"time.sleep(3); Path({str(marker)!r}).touch()"
    )
    source = (
        f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); "
        "time.sleep(60)"
    )
    with raises(TimeoutError, match="TIMEOUT_OUTCOME_UNKNOWN"):
        invoke(source, seconds=1)
    assert started.exists()
    # A second bounded process supplies the observation window, not a retry of the first.
    invoke("import time; time.sleep(3.2)")
    assert not Path(marker).exists()
