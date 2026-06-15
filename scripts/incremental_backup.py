"""
Backup thu muc theo co che incremental, mo phong cach Git luu trang thai.

Cau truc thu muc backup:
    backup_root/
        current/                 -> ban mirror moi nhat cua du lieu nguon
        commits/
            YYYYMMDD_HHMMSS/
                files/           -> chi chua file moi/cap nhat cua lan backup do
                deleted_files.txt
        logs/
            backup_history.log
        .backup_meta/
            manifest.json        -> luu hash/trang thai lan backup gan nhat
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


MANIFEST_DIRNAME = ".backup_meta"
MANIFEST_FILENAME = "manifest.json"
CURRENT_DIRNAME = "current"
COMMITS_DIRNAME = "commits"
LOGS_DIRNAME = "logs"
LOG_FILENAME = "backup_history.log"


@dataclass
class FileSnapshot:
    """Thong tin trang thai cua mot file tai thoi diem scan."""

    relative_path: str
    sha256: str
    size: int
    mtime: float

    def to_dict(self) -> dict:
        return {
            "sha256": self.sha256,
            "size": self.size,
            "mtime": self.mtime,
        }


@dataclass
class IgnoreRule:
    """Mot dong rule trich ra tu .gitignore."""

    pattern: str
    only_directory: bool
    anchored: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backup incremental cho thu muc nguon."
    )
    parser.add_argument("--source", required=True, help="Thu muc nguon can backup")
    parser.add_argument("--backup", required=True, help="Thu muc repository backup")
    return parser.parse_args()


def resolve_path(raw_path: str) -> Path:
    return Path(raw_path).expanduser().resolve()


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def compute_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Tinh SHA256 theo tung khoi de xu ly file lon on dinh."""

    hasher = hashlib.sha256()
    with file_path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def load_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        return {"last_backup_at": None, "files": {}}

    with manifest_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_manifest(manifest_path: Path, payload: dict) -> None:
    ensure_directory(manifest_path.parent)
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def is_subpath(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def scan_source(source_dir: Path) -> dict[str, FileSnapshot]:
    """Quet toan bo file trong thu muc nguon va tinh hash tung file."""

    snapshots: dict[str, FileSnapshot] = {}
    ignore_rules = load_gitignore_rules(source_dir)

    for root, dirs, files in os.walk(source_dir):
        root_path = Path(root)

        # Cat bo som cac thu muc bi ignore de giam thoi gian quet.
        dirs[:] = [
            directory_name
            for directory_name in dirs
            if not should_ignore_path(
                relative_path=(root_path / directory_name).relative_to(source_dir).as_posix(),
                is_dir=True,
                rules=ignore_rules,
            )
        ]

        for file_name in files:
            file_path = root_path / file_name
            relative_path = file_path.relative_to(source_dir).as_posix()
            if should_ignore_path(relative_path=relative_path, is_dir=False, rules=ignore_rules):
                continue

            stat_info = file_path.stat()
            snapshots[relative_path] = FileSnapshot(
                relative_path=relative_path,
                sha256=compute_sha256(file_path),
                size=stat_info.st_size,
                mtime=stat_info.st_mtime,
            )

    return snapshots


def load_gitignore_rules(source_dir: Path) -> list[IgnoreRule]:
    """Doc cac rule ignore tu file .gitignore o root cua source."""

    gitignore_path = source_dir / ".gitignore"
    if not gitignore_path.exists():
        return []

    rules: list[IgnoreRule] = []
    with gitignore_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue

            only_directory = line.endswith("/")
            if only_directory:
                line = line[:-1]

            anchored = line.startswith("/")
            if anchored:
                line = line[1:]

            if line:
                rules.append(
                    IgnoreRule(
                        pattern=line,
                        only_directory=only_directory,
                        anchored=anchored,
                    )
                )

    return rules


def should_ignore_path(relative_path: str, is_dir: bool, rules: list[IgnoreRule]) -> bool:
    """Kiem tra 1 path co nam trong tap ignore cua .gitignore hay khong."""

    normalized_path = relative_path.replace("\\", "/").strip("/")
    if not normalized_path:
        return False

    base_name = Path(normalized_path).name

    for rule in rules:
        if matches_ignore_rule(normalized_path, base_name, rule):
            return True

    return False


def matches_ignore_rule(normalized_path: str, base_name: str, rule: IgnoreRule) -> bool:
    """So khop 1 path voi 1 rule ignore theo tap pattern pho bien cua .gitignore."""

    pattern = rule.pattern
    if not pattern:
        return False

    if rule.only_directory:
        if rule.anchored:
            return normalized_path == pattern or normalized_path.startswith(f"{pattern}/")

        if "/" in pattern:
            return (
                normalized_path == pattern
                or normalized_path.startswith(f"{pattern}/")
                or f"/{pattern}/" in f"/{normalized_path}/"
            )

        return (
            base_name == pattern
            or normalized_path.startswith(f"{pattern}/")
            or f"/{pattern}/" in f"/{normalized_path}/"
        )

    if rule.anchored:
        return fnmatch.fnmatch(normalized_path, pattern)

    if "/" in pattern:
        return fnmatch.fnmatch(normalized_path, pattern) or fnmatch.fnmatch(
            normalized_path, f"*/{pattern}"
        )

    return fnmatch.fnmatch(base_name, pattern)


def copy_file(source_root: Path, relative_path: str, destination_root: Path) -> None:
    source_file = source_root / relative_path
    destination_file = destination_root / relative_path
    ensure_directory(destination_file.parent)
    shutil.copy2(source_file, destination_file)


def remove_file_if_exists(destination_root: Path, relative_path: str) -> None:
    target_file = destination_root / relative_path
    if target_file.exists():
        target_file.unlink()

        current_parent = target_file.parent
        while current_parent != destination_root and current_parent.exists():
            try:
                current_parent.rmdir()
            except OSError:
                break
            current_parent = current_parent.parent


def append_log(log_file: Path, lines: list[str]) -> None:
    ensure_directory(log_file.parent)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n" + ("-" * 80) + "\n")


def write_deleted_report(commit_dir: Path, deleted_files: list[str]) -> None:
    if not deleted_files:
        return

    report_path = commit_dir / "deleted_files.txt"
    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("Danh sach file da bi xoa o nguon:\n")
        for relative_path in deleted_files:
            handle.write(f"- {relative_path}\n")


def build_commit_message(
    backup_time: str,
    source_dir: Path,
    backup_dir: Path,
    added_files: list[str],
    updated_files: list[str],
    deleted_files: list[str],
) -> list[str]:
    return [
        f"Thoi gian backup: {backup_time}",
        f"Thu muc nguon   : {source_dir}",
        f"Thu muc backup  : {backup_dir}",
        f"So file moi     : {len(added_files)}",
        f"So file cap nhat: {len(updated_files)}",
        f"So file da xoa  : {len(deleted_files)}",
        "File moi:",
        *([f"  + {path}" for path in added_files] or ["  (khong co)"]),
        "File cap nhat:",
        *([f"  * {path}" for path in updated_files] or ["  (khong co)"]),
        "File da xoa:",
        *([f"  - {path}" for path in deleted_files] or ["  (khong co)"]),
    ]


def main() -> int:
    args = parse_args()
    source_dir = resolve_path(args.source)
    backup_dir = resolve_path(args.backup)

    if not source_dir.exists() or not source_dir.is_dir():
        print("Loi: Thu muc nguon khong ton tai hoac khong hop le.", file=sys.stderr)
        return 1

    if is_subpath(backup_dir, source_dir):
        print(
            "Loi: Thu muc backup khong duoc nam ben trong thu muc nguon,"
            " vi se gay de quy khi quet file.",
            file=sys.stderr,
        )
        return 1

    ensure_directory(backup_dir)

    manifest_path = backup_dir / MANIFEST_DIRNAME / MANIFEST_FILENAME
    current_dir = backup_dir / CURRENT_DIRNAME
    commits_dir = backup_dir / COMMITS_DIRNAME
    log_file = backup_dir / LOGS_DIRNAME / LOG_FILENAME
    gitignore_path = source_dir / ".gitignore"

    previous_manifest = load_manifest(manifest_path)
    previous_files = previous_manifest.get("files", {})

    current_snapshots = scan_source(source_dir)
    current_files = {path: snapshot.to_dict() for path, snapshot in current_snapshots.items()}

    previous_paths = set(previous_files.keys())
    current_paths = set(current_files.keys())

    added_files = sorted(current_paths - previous_paths)
    deleted_files = sorted(previous_paths - current_paths)
    updated_files = sorted(
        path
        for path in (current_paths & previous_paths)
        if current_files[path]["sha256"] != previous_files[path]["sha256"]
    )

    backup_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    commit_dir = commits_dir / commit_stamp
    commit_files_dir = commit_dir / "files"

    files_to_copy = added_files + updated_files

    if not previous_files:
        print("Lan backup dau tien: sao chep toan bo du lieu...")
        files_to_copy = sorted(current_paths)
        added_files = files_to_copy[:]
        updated_files = []
    elif not files_to_copy and not deleted_files:
        message_lines = build_commit_message(
            backup_time=backup_time,
            source_dir=source_dir,
            backup_dir=backup_dir,
            added_files=[],
            updated_files=[],
            deleted_files=[],
        )
        append_log(log_file, message_lines)
        print("Khong co thay doi nao so voi lan backup truoc.")
        print(f"Log da duoc cap nhat tai: {log_file}")
        return 0

    ensure_directory(current_dir)
    ensure_directory(commit_files_dir)

    for relative_path in files_to_copy:
        copy_file(source_dir, relative_path, current_dir)
        copy_file(source_dir, relative_path, commit_files_dir)

    for relative_path in deleted_files:
        remove_file_if_exists(current_dir, relative_path)

    write_deleted_report(commit_dir, deleted_files)

    manifest_payload = {
        "last_backup_at": backup_time,
        "files": current_files,
    }
    save_manifest(manifest_path, manifest_payload)

    message_lines = build_commit_message(
        backup_time=backup_time,
        source_dir=source_dir,
        backup_dir=backup_dir,
        added_files=added_files,
        updated_files=updated_files,
        deleted_files=deleted_files,
    )
    append_log(log_file, message_lines)

    print("Backup hoan tat.")
    print(f"So file moi     : {len(added_files)}")
    print(f"So file cap nhat: {len(updated_files)}")
    print(f"So file da xoa  : {len(deleted_files)}")
    print(f"Ban mirror moi  : {current_dir}")
    print(f"Commit delta moi: {commit_dir}")
    print(f"Log lich su     : {log_file}")
    if gitignore_path.exists():
        print(f"Gitignore su dung: {gitignore_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
