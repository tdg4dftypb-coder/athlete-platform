"""Isolated tests for the managed macOS user-cron fallback."""
from pathlib import Path
import os
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INSTALLER = PROJECT_ROOT / "ops/macos/install_daily_runtime_cron.sh"
STATUS = PROJECT_ROOT / "ops/macos/status_daily_runtime_cron.sh"
WRAPPER = PROJECT_ROOT / "ops/macos/run_production_daily_runtime_cron.sh"
BEGIN = "# BEGIN ATHLETE PLATFORM PRODUCTION DAILY RUNTIME"
END = "# END ATHLETE PLATFORM PRODUCTION DAILY RUNTIME"


@pytest.fixture
def cron_environment(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    state = tmp_path / "crontab"
    mutations = tmp_path / "mutations"
    crontab = tmp_path / "crontab-command"
    crontab.write_text(
        "#!/bin/bash\n"
        "if [[ \"${1:-}\" == -l ]]; then\n"
        "  if [[ \"${FAKE_CRONTAB_READ_ERROR:-0}\" == 1 ]]; then\n"
        "    echo 'crontab: permission denied' >&2\n"
        "    exit 1\n"
        "  fi\n"
        "  if [[ ! -f \"$FAKE_CRONTAB_STATE\" ]]; then\n"
        "    echo 'crontab: no crontab for test-user' >&2\n"
        "    exit 1\n"
        "  fi\n"
        "  /bin/cat \"$FAKE_CRONTAB_STATE\"\n"
        "else\n"
        "  /bin/cp \"$1\" \"$FAKE_CRONTAB_STATE\"\n"
        "  echo mutation >> \"$FAKE_CRONTAB_MUTATIONS\"\n"
        "fi\n"
    )
    crontab.chmod(0o755)
    launchctl = tmp_path / "launchctl-command"
    launchctl.write_text(
        "#!/bin/bash\n"
        "[[ \"${FAKE_LAUNCHCTL_LOADED:-0}\" == 1 ]]\n"
    )
    launchctl.chmod(0o755)
    env = os.environ | {
        "HOME": str(home),
        "FAKE_CRONTAB_STATE": str(state),
        "FAKE_CRONTAB_MUTATIONS": str(mutations),
        "ATHLETE_PLATFORM_CRONTAB_COMMAND": str(crontab),
        "ATHLETE_PLATFORM_LAUNCHCTL_COMMAND": str(launchctl),
        "ATHLETE_PLATFORM_LAUNCHAGENT_DIR": str(home / "Library/LaunchAgents"),
        "ATHLETE_PLATFORM_LOG_DIR": str(home / "Library/Logs/AthletePlatform"),
        "ATHLETE_PLATFORM_EXPECTED_TIMEZONE_SIGNATURE": "CEST +0200",
        "ATHLETE_PLATFORM_HOST_TIMEZONE_SIGNATURE": "CEST +0200",
    }
    return env, state, mutations, home


def run_installer(env, *arguments):
    return subprocess.run(
        [str(INSTALLER), *arguments], env=env, capture_output=True, text=True
    )


def test_wrapper_resolves_repo_and_executes_only_canonical_scheduled_command():
    content = WRAPPER.read_text()
    assert 'REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"' in content
    assert 'exec "$PYTHON_EXEC" -m scripts.run_production_daily_runtime --scheduled' in content
    assert "scripts.run_daily_decision_runtime" not in content
    assert "launchctl" not in content
    assert "crontab" not in content


def test_dry_run_is_read_only_and_reports_canonical_configuration(cron_environment):
    env, _, mutations, home = cron_environment
    result = run_installer(env, "--dry-run")
    assert result.returncode == 0
    assert "Schedule           : 0 7-23 * * *" in result.stdout
    assert str(WRAPPER) in result.stdout
    assert str(home / "Library/Logs/AthletePlatform/daily-runtime.log") in result.stdout
    assert str(home / "Library/Logs/AthletePlatform/daily-runtime-error.log") in result.stdout
    assert "Timezone aligned   : yes" in result.stdout
    assert "LaunchAgent loaded : no" in result.stdout
    assert not mutations.exists()


def test_clean_install_has_exact_managed_block_and_logs(cron_environment):
    env, state, mutations, home = cron_environment
    result = run_installer(env)
    assert result.returncode == 0, result.stderr
    content = state.read_text()
    assert content.count(BEGIN) == content.count(END) == 1
    line = next(line for line in content.splitlines() if line.startswith("0 "))
    assert line.startswith("0 7-23 * * * ")
    assert f"'{WRAPPER}'" in line
    assert "scripts.run_daily_decision_runtime" not in content
    assert "scripts.run_production_daily_runtime" not in content
    assert str(home / "Library/Logs/AthletePlatform/daily-runtime.log") in line
    assert str(home / "Library/Logs/AthletePlatform/daily-runtime-error.log") in line
    assert mutations.read_text().splitlines() == ["mutation"]


def test_install_preserves_unrelated_lines_and_is_idempotent(cron_environment):
    env, state, _, _ = cron_environment
    unrelated = "MAILTO=user@example.test\n15 4 * * 1 /usr/local/bin/other-job\n"
    state.write_text(unrelated)
    assert run_installer(env).returncode == 0
    first = state.read_text()
    assert first.startswith(unrelated)
    assert run_installer(env).returncode == 0
    second = state.read_text()
    assert second == first
    assert second.count(BEGIN) == second.count(END) == 1


def test_remove_deletes_only_managed_block_and_preserves_other_entries(cron_environment):
    env, state, _, _ = cron_environment
    unrelated = "MAILTO=user@example.test\n15 4 * * 1 /usr/local/bin/other-job\n"
    state.write_text(unrelated)
    assert run_installer(env).returncode == 0
    assert run_installer(env, "--remove").returncode == 0
    assert state.read_text() == unrelated


def test_unrelated_entries_around_valid_block_survive_install_and_remove(cron_environment):
    env, state, _, _ = cron_environment
    before = "15 4 * * * /usr/local/bin/before\n"
    after = "30 8 * * * /usr/local/bin/after\n"
    state.write_text(
        before
        + BEGIN
        + f"\n0 7-23 * * * '{WRAPPER}' >> '/tmp/out' 2>> '/tmp/err'\n"
        + END
        + "\n"
        + after
    )
    assert run_installer(env).returncode == 0
    assert state.read_text().startswith(before + after)
    assert run_installer(env, "--remove").returncode == 0
    assert state.read_text() == before + after


@pytest.mark.parametrize(
    "content",
    [
        f"unrelated-before\n{BEGIN}\nmanaged\nunrelated-after\n",
        f"unrelated-before\n{END}\nunrelated-after\n",
        f"{BEGIN}\n{BEGIN}\nmanaged\n{END}\n",
        f"{BEGIN}\nmanaged\n{END}\n{END}\n",
        f"{END}\nunrelated\n{BEGIN}\n",
    ],
)
def test_malformed_markers_fail_install_without_mutation(
    cron_environment, content
):
    env, state, mutations, _ = cron_environment
    state.write_text(content)
    result = run_installer(env)
    assert result.returncode == 1
    assert "markers are malformed" in result.stderr
    assert state.read_text() == content
    assert not mutations.exists()


def test_malformed_markers_fail_remove_and_status_reports_malformed(cron_environment):
    env, state, mutations, _ = cron_environment
    content = f"unrelated-before\n{BEGIN}\nmanaged\nunrelated-after\n"
    state.write_text(content)
    removed = run_installer(env, "--remove")
    status = subprocess.run([str(STATUS)], env=env, capture_output=True, text=True)
    assert removed.returncode == 1
    assert "markers are malformed" in removed.stderr
    assert "Managed cron block : malformed" in status.stdout
    assert "Managed schedule   : none" in status.stdout
    assert state.read_text() == content
    assert not mutations.exists()


@pytest.mark.parametrize("operation", [(), ("--remove",)])
def test_crontab_read_error_fails_without_mutation(cron_environment, operation):
    env, _, mutations, _ = cron_environment
    env["FAKE_CRONTAB_READ_ERROR"] = "1"
    result = run_installer(env, *operation)
    assert result.returncode == 1
    assert "unable to read user crontab" in result.stderr
    assert "permission denied" in result.stderr
    assert not mutations.exists()


def test_read_error_is_visible_in_dry_run_and_status(cron_environment):
    env, _, mutations, _ = cron_environment
    env["FAKE_CRONTAB_READ_ERROR"] = "1"
    dry_run = run_installer(env, "--dry-run")
    status = subprocess.run([str(STATUS)], env=env, capture_output=True, text=True)
    assert dry_run.returncode == status.returncode == 0
    assert "Crontab read       : error" in dry_run.stdout
    assert "Crontab read       : error" in status.stdout
    assert "Managed cron block : unknown" in dry_run.stdout
    assert "Managed cron block : unknown" in status.stdout
    assert "permission denied" in dry_run.stdout
    assert "permission denied" in status.stdout
    assert not mutations.exists()


def test_remove_absent_crontab_is_successful_noop(cron_environment):
    env, state, mutations, _ = cron_environment
    result = run_installer(env, "--remove")
    assert result.returncode == 0
    assert "nothing to remove" in result.stdout
    assert not state.exists()
    assert not mutations.exists()


@pytest.mark.parametrize(
    ("setup", "expected"),
    [
        ("loaded", "LaunchAgent is installed or loaded"),
        ("plist", "LaunchAgent is installed or loaded"),
        ("production", "unmanaged Athlete Platform runtime cron entry"),
        ("legacy", "unmanaged Athlete Platform runtime cron entry"),
        ("wrapper-name", "unmanaged Athlete Platform runtime cron entry"),
        ("wrapper-path", "unmanaged Athlete Platform runtime cron entry"),
    ],
)
def test_scheduler_conflicts_fail_closed(cron_environment, setup, expected):
    env, state, mutations, home = cron_environment
    if setup == "loaded":
        env["FAKE_LAUNCHCTL_LOADED"] = "1"
    elif setup == "plist":
        plist = home / "Library/LaunchAgents/com.athleteplatform.daily-decision-runtime.plist"
        plist.parent.mkdir(parents=True)
        plist.write_text("plist")
    elif setup == "production":
        state.write_text("0 7 * * * python -m scripts.run_production_daily_runtime --scheduled\n")
    elif setup == "legacy":
        state.write_text("0 7 * * * python -m scripts.run_daily_decision_runtime\n")
    elif setup == "wrapper-name":
        state.write_text("0 7 * * * run_production_daily_runtime_cron.sh\n")
    else:
        state.write_text(f"0 7 * * * {WRAPPER}\n")
    result = run_installer(env)
    assert result.returncode == 1
    assert expected in result.stderr
    assert not mutations.exists()


def test_timezone_mismatch_fails_closed_only_for_real_install(cron_environment):
    env, _, mutations, _ = cron_environment
    env["ATHLETE_PLATFORM_HOST_TIMEZONE_SIGNATURE"] = "UTC +0000"
    dry_run = run_installer(env, "--dry-run")
    assert dry_run.returncode == 0
    assert "Timezone aligned   : no" in dry_run.stdout
    installed = run_installer(env)
    assert installed.returncode == 1
    assert "not aligned with Europe/Warsaw" in installed.stderr
    assert not mutations.exists()


def test_invalid_option_is_bounded_and_nonzero(cron_environment):
    env, _, mutations, _ = cron_environment
    result = run_installer(env, "--unknown")
    assert result.returncode == 2
    assert "unknown argument" in result.stderr
    assert not mutations.exists()


def test_commented_wrapper_line_is_not_an_active_conflict(cron_environment):
    env, state, _, _ = cron_environment
    comment = f"# 0 7 * * * {WRAPPER}\n"
    state.write_text(comment)
    result = run_installer(env)
    assert result.returncode == 0, result.stderr
    assert state.read_text().startswith(comment)
    assert state.read_text().count(BEGIN) == 1


def test_remove_dry_run_reports_resulting_intent_without_install_block(cron_environment):
    env, _, mutations, _ = cron_environment
    result = run_installer(env, "--dry-run", "--remove")
    assert result.returncode == 0
    assert "Resulting intent   : managed block absent" in result.stdout
    assert "--- Proposed managed block ---" not in result.stdout
    assert not mutations.exists()


def test_status_is_read_only_and_reports_conflicts(cron_environment):
    env, state, mutations, home = cron_environment
    state.write_text(
        f"{BEGIN}\n0 7-23 * * * '{WRAPPER}' >> '/tmp/out' 2>> '/tmp/err'\n{END}\n"
        "0 8 * * * python -m scripts.run_daily_decision_runtime\n"
    )
    plist = home / "Library/LaunchAgents/com.athleteplatform.daily-decision-runtime.plist"
    plist.parent.mkdir(parents=True)
    plist.write_text("plist")
    result = subprocess.run([str(STATUS)], env=env, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Managed cron block : present" in result.stdout
    assert "0 7-23 * * *" in result.stdout
    assert "LaunchAgent plist  : conflict" in result.stdout
    assert "Unmanaged runtime  : conflict" in result.stdout
    assert not mutations.exists()
