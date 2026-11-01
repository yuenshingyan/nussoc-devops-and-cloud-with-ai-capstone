"""Exercise the real Uvicorn logging configuration, not only a formatter in isolation."""

from json import loads
from pathlib import Path
from signal import SIGTERM
from socket import AF_INET, SOCK_STREAM, socket
from subprocess import STDOUT, Popen, TimeoutExpired
from sys import executable
from time import monotonic, sleep

from httpx2 import Client

ROOT = Path(__file__).resolve().parents[2]


def test_real_server_emits_json_without_request_secrets(tmp_path):
    log_path = tmp_path / "server.jsonl"
    # Parent owns the reserved ephemeral port; child borrows its inherited descriptor.
    with socket(AF_INET, SOCK_STREAM) as listener, log_path.open("w", encoding="utf-8") as output:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        with Popen(
            [
                executable,
                "-m",
                "uvicorn",
                "finsecure_pay.main:create_app",
                "--factory",
                "--fd",
                str(listener.fileno()),
                "--no-access-log",
                "--log-config",
                "src/finsecure_pay/observability/logging.json",
            ],
            cwd=ROOT,
            pass_fds=(listener.fileno(),),
            stdout=output,
            stderr=STDOUT,
        ) as process:
            try:
                with Client(
                    base_url=f"http://127.0.0.1:{port}", timeout=1, trust_env=False
                ) as client:
                    deadline = monotonic() + 10
                    while monotonic() < deadline:
                        assert process.poll() is None, "Server failed startup"
                        if '"diagnostic_code":"APPLICATION_STARTED"' in log_path.read_text(
                            encoding="utf-8"
                        ):
                            break
                        sleep(0.05)
                    else:
                        raise AssertionError("Server startup exceeded ten seconds")
                    assert client.get("/health").status_code == 200
                    for amount, status in [("1.00", 200), ("-1.00", 200), (1, 422)]:
                        response = client.post(
                            "/validate?token=synthetic-private",
                            headers={"Authorization": "synthetic-private"},
                            json={
                                "transaction_id": "synthetic-private",
                                "sender_id": "synthetic-private-sender",
                                "recipient_id": "synthetic-private-recipient",
                                "amount": amount,
                                "currency": "SGD",
                            },
                        )
                        assert response.status_code == status
                    assert client.get("/synthetic-private").status_code == 404
                    assert client.get("/metrics").status_code == 200
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    # Uvicorn re-raises the requested signal after graceful shutdown outside PID 1.
    # Also require APPLICATION_STOPPED below; a forced kill is not a successful cleanup.
    assert process.returncode == -SIGTERM
    text = log_path.read_text(encoding="utf-8")
    assert "synthetic-private" not in text
    records = [loads(line) for line in text.splitlines()]
    assert [r["outcome"] for r in records if r["event"] == "validation_outcome"] == [
        "accepted",
        "rejected",
        "invalid",
    ]
    requests = [r for r in records if r["event"] == "http_request_completed"]
    assert len(requests) == 5
    assert {r["status_class"] for r in requests} == {"2xx", "4xx"}
    assert any(r.get("diagnostic_code") == "APPLICATION_STOPPED" for r in records)
