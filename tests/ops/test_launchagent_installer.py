"""Tests for macOS LaunchAgent template, rendering, and installer script mechanics."""
import os
from pathlib import Path
import plistlib
import subprocess
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = PROJECT_ROOT / "ops" / "macos" / "com.athleteplatform.daily-decision-runtime.plist.template"
INSTALL_SCRIPT = PROJECT_ROOT / "ops" / "macos" / "install_daily_runtime_launchagent.sh"
UNINSTALL_SCRIPT = PROJECT_ROOT / "ops" / "macos" / "uninstall_daily_runtime_launchagent.sh"
STATUS_SCRIPT = PROJECT_ROOT / "ops" / "macos" / "status_daily_runtime_launchagent.sh"


def test_launchagent_template_file_exists():
    assert TEMPLATE_PATH.exists()
    assert INSTALL_SCRIPT.exists()
    assert UNINSTALL_SCRIPT.exists()
    assert STATUS_SCRIPT.exists()


def test_dry_run_installer_renders_valid_plist():
    result = subprocess.run(
        [str(INSTALL_SCRIPT), "--dry-run", "--hour", "8", "--minute", "30"],
        capture_output=True,
        text=True,
        check=True,
    )

    out = result.stdout
    assert "=== DRY RUN: LaunchAgent Configuration ===" in out
    assert "plutil lint check : OK" in out

    # Extract plist content from dry-run stdout
    lines = out.splitlines()
    start_idx = lines.index("--- Rendered Content ---") + 1
    end_idx = lines.index("------------------------")
    plist_xml = "\n".join(lines[start_idx:end_idx])

    # Validate plist XML via plistlib
    data = plistlib.loads(plist_xml.encode("utf-8"))
    assert data["Label"] == "com.athleteplatform.daily-decision-runtime"
    assert data["ProgramArguments"][0].endswith(".venv/bin/python")
    assert data["ProgramArguments"][1:3] == ["-m", "scripts.run_daily_decision_runtime"]
    assert data["StartCalendarInterval"]["Hour"] == 8
    assert data["StartCalendarInterval"]["Minute"] == 30
    assert data["RunAtLoad"] is True
    assert "KeepAlive" not in data


def test_installer_invalid_arguments_error_handling():
    res_hour = subprocess.run([str(INSTALL_SCRIPT), "--hour", "25"], capture_output=True, text=True)
    assert res_hour.returncode == 2
    assert "Hour must be between 0 and 23" in res_hour.stderr

    res_min = subprocess.run([str(INSTALL_SCRIPT), "--minute", "60"], capture_output=True, text=True)
    assert res_min.returncode == 2
    assert "Minute must be between 0 and 59" in res_min.stderr


def test_installer_target_dir_override_dry_run(tmp_path):
    target_dir = tmp_path / "LaunchAgents"
    log_dir = tmp_path / "Logs"

    result = subprocess.run(
        [
            str(INSTALL_SCRIPT),
            "--dry-run",
            "--target-dir",
            str(target_dir),
            "--log-dir",
            str(log_dir),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    out = result.stdout
    assert f"Target Plist Path : {target_dir}/com.athleteplatform.daily-decision-runtime.plist" in out
    assert f"Log Stdout        : {log_dir}/daily-runtime.log" in out


def test_installer_fails_gracefully_on_unwritable_target_dir(tmp_path):
    unwritable_dir = tmp_path / "unwritable"
    unwritable_dir.mkdir()
    unwritable_dir.chmod(0o555)

    result = subprocess.run(
        [str(INSTALL_SCRIPT), "--target-dir", str(unwritable_dir)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "is not writable. Permission denied." in result.stderr
