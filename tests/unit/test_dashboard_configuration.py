"""Check the committed dashboard contract without Docker, Grafana, or extra parsers."""

from configparser import ConfigParser
from json import loads
from pathlib import Path
from re import fullmatch
from runpy import run_path

from pytest import mark

ROOT = Path(__file__).resolve().parents[2]
GRAFANA = ROOT / "ops/monitoring/grafana"
DASHBOARD = loads((GRAFANA / "dashboards/finsecure-pay.json").read_text(encoding="utf-8"))


def test_dashboard_is_provisioned_without_ui_persistence_or_dynamic_identifiers():
    provider = loads((GRAFANA / "provisioning/dashboards/finsecure.yaml").read_text())["providers"][
        0
    ]
    assert provider["allowUiUpdates"] is False
    assert provider["disableDeletion"] is True
    assert provider["options"]["path"] == "/etc/grafana/dashboards"
    assert provider["updateIntervalSeconds"] == 15
    assert DASHBOARD["editable"] is False
    assert DASHBOARD["uid"] == "finsecure-pay-local"
    assert DASHBOARD["time"] == {"from": "now-15m", "to": "now"}
    assert DASHBOARD["refresh"] == "15s" and DASHBOARD["timezone"] == "utc"
    assert DASHBOARD["templating"]["list"] == []
    assert {panel["id"] for panel in DASHBOARD["panels"]} == {1, 2, 3, 4, 5}
    assert len(DASHBOARD["panels"]) == 5


@mark.parametrize(
    "identifier,metric,unit",
    [
        (1, "finsecure_http_requests_total", "reqps"),
        (2, "finsecure_http_request_duration_seconds_sum", "s"),
        (3, "up", "none"),
        (4, "finsecure_process_resident_memory_bytes", "suffix:MiB"),
        (5, "finsecure_validation_outcomes_total", "reqps"),
    ],
)
def test_each_panel_uses_real_scoped_metrics_and_explicit_units(identifier, metric, unit):
    panel = next(panel for panel in DASHBOARD["panels"] if panel["id"] == identifier)
    assert panel["datasource"] == {"type": "prometheus", "uid": "finsecure-prometheus"}
    assert panel["fieldConfig"]["defaults"]["unit"] == unit
    assert panel["fieldConfig"]["defaults"]["noValue"]
    expression = panel["targets"][0]["expr"]
    assert metric + '{job="finsecure-pay"}' in expression
    assert "or vector(0)" not in expression and "clamp_min" not in expression
    assert "$" not in expression
    if identifier in (1, 2, 5):
        assert "rate(" in expression and "[2m]" in expression
    if identifier == 2:
        assert " / sum(rate(finsecure_http_request_duration_seconds_count" in expression
    if identifier == 4:
        assert expression.endswith(" / 1024 / 1024")
        assert "not pod/node" in panel["description"].lower()
    if panel["type"] == "stat":
        assert panel["targets"][0]["instant"] is True
        assert panel["options"]["reduceOptions"]["calcs"] == ["last"]


def test_datasource_is_read_only_server_side_and_has_bounded_query_timeout():
    config = loads((GRAFANA / "provisioning/datasources/prometheus.yaml").read_text())
    assert config["apiVersion"] == 1 and len(config["datasources"]) == 1
    source = config["datasources"][0]
    assert source["uid"] == "finsecure-prometheus"
    assert source["access"] == "proxy" and source["url"] == "http://prometheus:9090"
    assert source["editable"] is False and source["isDefault"] is True
    assert source["jsonData"]["timeInterval"] == "15s"
    assert source["jsonData"]["queryTimeout"] == "5s"
    assert "secureJsonData" not in source


def test_grafana_uses_file_authentication_without_external_features():
    config = ConfigParser(interpolation=None)
    config.read(GRAFANA / "grafana.ini", encoding="utf-8")
    assert config["security"]["admin_password"] == "$__file{/run/secrets/grafana-admin-password}"
    assert not config.getboolean("auth.anonymous", "enabled")
    assert not config.getboolean("users", "allow_sign_up")
    assert not config.getboolean("users", "allow_org_create")
    for key in ("reporting_enabled", "check_for_updates", "check_for_plugin_updates"):
        assert not config.getboolean("analytics", key)
    assert config.getboolean("plugins", "preinstall_disabled")
    assert not config.getboolean("plugins", "preinstall_auto_update")
    assert not config.getboolean("news", "news_feed_enabled")
    assert not config.getboolean("unified_alerting", "enabled")
    assert config["log"]["mode"] == "console" and config["log"]["level"] == "info"
    assert config.getint("dataproxy", "timeout") == 5


def test_overlay_keeps_the_metrics_only_stack_independent_and_limits_grafana():
    overlay = loads((ROOT / "ops/monitoring/grafana.compose.yaml").read_text())
    assert set(overlay["services"]) == {"grafana"}
    grafana = overlay["services"]["grafana"]
    helpers = run_path(str(ROOT / "scripts/monitoring_credentials.py"))
    assert grafana["image"] == helpers["GRAFANA_IMAGE"]
    assert fullmatch(r"grafana/grafana:13\.3\.0@sha256:[0-9a-f]{64}", grafana["image"])
    assert grafana["user"] == "472:472"
    assert grafana["read_only"] is True
    assert grafana["cap_drop"] == ["ALL"] and "cap_add" not in grafana
    assert grafana["security_opt"] == ["no-new-privileges:true"]
    assert grafana["ports"] == ["127.0.0.1:3000:3000"]
    assert grafana["cpus"] == 0.5 and grafana["mem_limit"] == grafana["memswap_limit"] == "512m"
    assert grafana["tmpfs"] == ["/tmp:rw,noexec,nosuid,size=16m,mode=1777"]
    assert "grafana-secrets:/run/secrets:ro" in grafana["volumes"]
    assert "secrets" not in grafana
    assert "environment" not in grafana
    assert all(mount.endswith(":ro") for mount in grafana["volumes"] if mount.startswith("./"))
    # Mount individual provisioning files so unused vendor directories remain present.
    assert {mount.split(":")[1] for mount in grafana["volumes"] if mount.startswith("./")} == {
        "/etc/grafana/grafana.ini",
        "/etc/grafana/provisioning/datasources/finsecure.yaml",
        "/etc/grafana/provisioning/dashboards/finsecure.yaml",
        "/etc/grafana/dashboards",
    }
    assert set(overlay["volumes"]) == {"grafana-data", "grafana-secrets"}
    assert overlay["volumes"]["grafana-secrets"] == {
        "external": True,
        "name": helpers["SECRET_VOLUME"],
    }
    assert "secrets" not in overlay
