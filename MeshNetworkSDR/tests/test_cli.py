"""Tests for CLI subcommands and scripts."""

import sys
from pathlib import Path
import pytest

from pluto_radio.cli import main


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Pluto+ SDR" in captured.out
    assert "status" in captured.out


def test_cli_no_args(capsys):
    ret = main([])
    assert ret == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out


def test_cli_status_simulation(capsys):
    ret = main(["status", "--simulation"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "PLUTO SDR" in captured.out
    assert "Status       : SIMULATION" in captured.out
    assert "URI          : sim:pluto0" in captured.out


def test_cli_stats(capsys):
    ret = main(["stats"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "PLUTO RADIO TELEMETRY" in captured.out
    assert "TX packets" in captured.out


def test_cli_future_stubs(capsys):
    for cmd in ["tx", "rx", "link", "ping"]:
        ret = main([cmd])
        assert ret == 0
        captured = capsys.readouterr()
        assert f"Command '{cmd}' is reserved for Stage" in captured.out
