"""Check the local-only notification boundary and approved alert contract."""

from json import loads
from pathlib import Path

from pytest import mark

ROOT = Path(__file__).resolve().parents[2] / "ops" / "monitoring"


def configuration(name: str) -> dict:
    """Read configuration written in the JSON subset of YAML."""
    return loads((ROOT / name).read_text(encoding="utf-8"))


def test_rule_requires_one_minute_of_failed_or_missing_scrapes():
    rule = configuration("prometheus/alerts.yaml")["groups"][0]["rules"][0]
    assert rule["for"] == "1m"
    assert rule["expr"] == (
        '(up{job="finsecure-pay",instance="application:8000"} == 0) or '
        'absent(up{job="finsecure-pay",instance="application:8000"})'
    )
    assert rule["labels"] == {"severity": "warning", "scope": "local-demo"}


def test_prometheus_evaluates_every_fifteen_seconds_and_routes_to_alertmanager():
    config = configuration("prometheus/alerts-prometheus.yaml")
    assert config["global"] == {
        "scrape_interval": "15s",
        "scrape_timeout": "5s",
        "evaluation_interval": "15s",
    }
    assert config["rule_files"] == ["/etc/prometheus/alerts.yaml"]
    assert config["alerting"]["alertmanagers"][0]["static_configs"][0]["targets"] == [
        "alertmanager:9093"
    ]


def test_email_stays_local_and_includes_recovery():
    config = configuration("alertmanager/alertmanager.yaml")
    assert config["global"]["smtp_smarthost"] == "mailpit:1025"
    assert config["global"]["smtp_from"] == "finsecure-alerts@example.test"
    assert config["receivers"] == [
        {
            "name": "local-mailpit",
            "email_configs": [{"to": "finsecure-operator@example.test", "send_resolved": True}],
        }
    ]
    assert config["route"] == {
        "receiver": "local-mailpit",
        "group_by": ["alertname", "job", "instance"],
        "group_wait": "30s",
        "group_interval": "5m",
        "repeat_interval": "4h",
    }


@mark.parametrize("service,port", [("alertmanager", 9093), ("mailpit", 8025)])
def test_new_services_have_bounded_unprivileged_loopback_access(service, port):
    config = configuration("alerts.compose.yaml")["services"][service]
    assert "@sha256:" in config["image"]
    assert config["user"] == "65534:65534"
    assert config["ports"] == [f"127.0.0.1:{port}:{port}"]
    assert config["read_only"]
    assert config["cap_drop"] == ["ALL"]
    assert config["security_opt"] == ["no-new-privileges:true"]
    assert config["mem_limit"] == config["memswap_limit"] == "256m"
    assert config["cpus"] == 0.5


def test_mailpit_has_no_external_relay_configuration_and_does_not_publish_smtp():
    config = configuration("alerts.compose.yaml")
    assert config["networks"] == {"notification": {}}
    mailpit = config["services"]["mailpit"]
    assert mailpit["networks"] == ["notification"]
    assert mailpit["ports"] == ["127.0.0.1:8025:8025"]
    assert not any("RELAY" in key or "FORWARD" in key for key in mailpit["environment"])
    assert mailpit["environment"]["MP_ALLOWED_HOSTS"] == "127.0.0.1,localhost,mailpit"
    assert mailpit["environment"]["MP_SMTP_ALLOWED_RECIPIENTS"] == (
        r"^finsecure-operator@example\.test$"
    )
