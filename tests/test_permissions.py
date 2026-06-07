from __future__ import annotations

from pathlib import Path

from redclaw.agent.permissions import PermissionService


def test_allowed_path_is_safe(tmp_path):
    service = PermissionService([tmp_path])
    assert service.check_path(tmp_path / "note.txt").level == "safe"


def test_unknown_path_needs_confirmation(tmp_path):
    service = PermissionService([tmp_path / "allowed"])
    assert service.check_path(tmp_path / "other" / "note.txt").level == "needs_confirmation"


def test_install_command_needs_confirmation(tmp_path):
    service = PermissionService([Path(tmp_path)])
    assert service.check_command("apt install nginx").level == "needs_confirmation"


def test_system_destroying_command_blocked(tmp_path):
    service = PermissionService([Path(tmp_path)])
    assert service.check_command("mkfs /dev/sda").level == "blocked"
