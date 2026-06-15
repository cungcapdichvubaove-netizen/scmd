# -*- coding: utf-8 -*-
"""
SCMD Pro - Release Contract Validator (Implementation)
------------------------------------------------------
Tự động kiểm tra tuân thủ WHITEPAPER.md v3.5.0 và DOCUMENTATION.md.
Chặn release nếu phát hiện vi phạm ranh giới kiến trúc và bảo mật.
"""

import os
import re
import sys
import glob
import argparse
import ast
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True


SKIP_DIR_PARTS = {
    ".git", "__pycache__", "node_modules", "staticfiles", "media", ".pytest_cache", "htmlcov",
    "tmp-edge-profile", "tmpedge2", "venv", ".venv", "env",
}


def should_skip_path(path):
    parts = set(Path(path).parts)
    return bool(parts & SKIP_DIR_PARTS)


def iter_source_files(root='.', suffixes=None):
    """Yield files while pruning non-source/runtime directories early.

    This prevents release checks from walking huge virtualenv/node_modules/media
    trees after a P0 artifact has already been detected elsewhere.
    """
    for current_root, dirs, files in os.walk(root, topdown=True):
        dirs[:] = [dirname for dirname in dirs if dirname not in SKIP_DIR_PARTS]
        if should_skip_path(current_root):
            continue
        for filename in files:
            if suffixes and not any(filename.endswith(ext) for ext in suffixes):
                continue
            yield os.path.join(current_root, filename)


def _safe_console_text(text):
    """Return console-safe text for Windows shells with limited encodings."""
    encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
    return text.encode(encoding, errors='replace').decode(encoding, errors='replace')

def setup_django():
    """Khởi tạo Django nếu dependency/runtime sẵn sàng.

    Release validator phải chạy được static checks ngay cả trong môi trường
    audit ZIP chưa cài Django. Vì vậy không import django ở top-level.
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        import django
        django.setup()
        return True
    except Exception as e:
        print(_safe_console_text(f"WARNING: Khong the khoi tao Django. Mot so kiem tra can settings se bi bo qua. Loi: {e}"))
        return False


def check_static_python():
    """Rule 13 & 3.3.1 (P0): Tuyệt đối không để file .py trong thư mục tĩnh công khai."""
    violations = []
    if os.path.exists('static'):
        for root, _, files in os.walk('static'):
            for file in files:
                if file.endswith('.py'):
                    violations.append(os.path.join(root, file))
    return violations


def check_template_python():
    """Rule 3.3.1 (P0): Không nạp logic Python vào thư mục chứa giao diện."""
    violations = []
    search_patterns = ['templates', '*/templates']
    for pattern in search_patterns:
        for t_dir in glob.glob(pattern):
            for root, _, files in os.walk(t_dir):
                for file in files:
                    if file.endswith('.py'):
                        violations.append(os.path.join(root, file))
    return violations


def check_wildcard_imports():
    """Rule 3.2 (P1): Cấm 'import *' trong tầng Application để bảo vệ tính deterministic."""
    violations = []
    for app_path in glob.glob('*/application'):
        for root, _, files in os.walk(app_path):
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            for line_no, line in enumerate(f, 1):
                                if 'import *' in line and 'noqa' not in line:
                                    violations.append(f"{full_path}:{line_no}: {line.strip()}")
                    except Exception: continue
    return violations


def check_tailwind_cdn():
    """Rule 10.2 (P2): Cấm Tailwind CDN trong production templates."""
    violations = []
    search_dirs = ['templates', '*/templates']
    for pattern in search_dirs:
        for path in glob.glob(os.path.join(pattern, '**/*.html'), recursive=True):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    if ('cdn.tailwindcss' + '.com') in f.read():
                        violations.append(path)
            except Exception: continue
    return violations


def check_external_font_cdn():
    """P0: Admin/public/internal runtime must not fetch fonts from external CDNs."""
    violations = []
    pattern = re.compile(r"fonts\.googleapis\.com|fonts\.gstatic\.com", re.IGNORECASE)
    for path in iter_source_files('.', suffixes=('.html', '.css', '.js', '.svg')):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                if pattern.search(f.read()):
                    violations.append(path)
        except Exception:
            continue
    return violations


def check_vendor_stub_assets():
    """P0: Reject placeholder vendor assets on runtime paths."""
    suspicious = {
        "static/vendor/chartjs/chart.umd.min.js": 5000,
        "static/vendor/html5-qrcode/html5-qrcode.min.js": 20000,
        "static/vendor/alpine/alpine.min.js": 5000,
        "static/vendor/jquery/jquery-3.7.0.min.js": 10000,
        "static/vendor/select2/select2.min.js": 10000,
        "static/vendor/select2/select2.min.css": 2000,
        "static/vendor/fontawesome/css/all.min.css": 10000,
        "static/vendor/dexie/dexie.min.js": 5000,
        "static/vendor/htmx/htmx.min.js": 5000,
        "static/vendor/nprogress/nprogress.min.js": 1000,
        "static/vendor/bootstrap/bootstrap.bundle.min.js": 10000,
    }
    violations = []
    for relative_path, minimum_size in suspicious.items():
        path = Path(relative_path)
        if not path.exists():
            violations.append(f"{relative_path}: missing runtime vendor asset.")
            continue
        if path.stat().st_size < minimum_size:
            violations.append(f"{relative_path}: suspiciously small ({path.stat().st_size} bytes), likely placeholder/stub.")
            continue
        try:
            content = path.read_text(encoding='utf-8', errors='ignore').lower()
        except Exception:
            content = ""
        if "minimal local" in content or "compatibility fallback" in content:
            violations.append(f"{relative_path}: contains placeholder/stub marker text.")
    return violations


def check_legacy_brand_language():
    """Rule 2 & 10.1 (P2): Cấm sử dụng thuật ngữ cũ (legacy UI terminology) trên UI sở hữu."""
    violations = []
    # Pattern từ UI_SYSTEM_REFACTOR_SPEC.md
    legacy_pattern = re.compile("|".join(["War " + "Room", "War" + "Room", "Senti" + "nel", "Tact" + "ical", "Cy" + "ber", "SCMD ERP", r"\bESP\b"]), re.IGNORECASE)
    search_dirs = ['templates', 'main', 'dashboard', 'users', 'operations', 'accounting', 'clients', 'inventory']
    extensions = ['.html', '.js', '.txt']

    for d in search_dirs:
        if not os.path.exists(d): continue
        for root, _, files in os.walk(d):
            if should_skip_path(root):
                continue
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_no, line in enumerate(f, 1):
                                if legacy_pattern.search(line):
                                    violations.append(f"{path}:{line_no}: {line.strip()}")
                    except Exception: continue
    return violations


def check_manager_ssot():
    """Rule 4.4 & 9 (P1): Cưỡng chế SSOT cho Organization Scope Manager."""
    violations = []
    # 1. Kiểm tra core/managers.py có định nghĩa không
    core_mgr_path = os.path.join('core', 'managers.py')
    if not os.path.exists(core_mgr_path):
        violations.append("Thiếu tệp core/managers.py (SSOT cho TenantAwareManager).")
    else:
        with open(core_mgr_path, 'r', encoding='utf-8', errors='ignore') as f:
            if 'class TenantAwareManager' not in f.read():
                violations.append("core/managers.py không định nghĩa TenantAwareManager.")

    # 2. Chặn việc định nghĩa đè Manager ở các app khác
    manager_pattern = re.compile(r"^\s*class\s+(TenantAwareManager|OrganizationScopedManager)\b")
    forbidden_apps = ['main', 'users', 'clients', 'operations', 'accounting', 'inventory', 'inspection']
    for app in forbidden_apps:
        for path in glob.glob(os.path.join(app, 'models*.py')):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_no, line in enumerate(f, 1):
                    if manager_pattern.search(line):
                        violations.append(f"Vi phạm SSOT tại {path}:{line_no}: Định nghĩa Manager tại App thay vì dùng core.managers.")
    return violations


def check_migration_graph():
    """Rule 11 (Hardening): Kiểm tra đồ thị migration có bị phân nhánh (conflict) không."""
    violations = []
    app_dirs = [d for d in os.listdir('.') if os.path.isdir(os.path.join(d, 'migrations'))]
    
    for app in app_dirs:
        migration_dir = os.path.join(app, 'migrations')
        by_prefix = defaultdict(list)
        merge_prefixes = set()
        
        for f in os.listdir(migration_dir):
            if f.endswith('.py') and f != '__init__.py':
                prefix = f.split('_')[0]
                if prefix.isdigit():
                    by_prefix[prefix].append(f)
                    if 'merge' in f.lower(): merge_prefixes.add(prefix)
        
        # Nếu một số thứ tự có > 1 file và không có file merge
        for prefix, files in by_prefix.items():
            if len(files) > 1:
                # Kiểm tra xem có bất kỳ file merge nào có prefix >= prefix hiện tại không
                if not any(int(m_pre) >= int(prefix) for m_pre in merge_prefixes):
                    violations.append(f"App '{app}': Phân nhánh migration tại {prefix} chưa được hội tụ -> {files}")
    return violations


def check_conflict_markers():
    """P0: Chặn release tệp còn dấu vết merge conflict."""
    violations = []
    marker_pattern = re.compile(r"^(<<<<<<<|=======|>>>>>>>)")
    for path in iter_source_files('.', suffixes=('.py', '.html', '.css', '.js', '.md', '.yml')):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_no, line in enumerate(f, 1):
                    if marker_pattern.search(line):
                        violations.append(f"{path}:{line_no}")
        except Exception:
            continue
    return violations


def check_runtime_residue():
    """Rule 11 (Hardening): Chặn đóng gói các tệp tin rác phát sinh lúc runtime."""
    violations = []
    residue_dirs = {"__pycache__", ".pytest_cache", "htmlcov", "tmp-edge-profile", "tmpedge2"}
    residue_names = {"dump.rdb", ".coverage", ".DS_Store", "deploy-scmdpro.log"}

    for root, dirs, files in os.walk('.', topdown=True):
        kept_dirs = []
        for dirname in dirs:
            if dirname in {".git", "venv", ".venv", "env", "node_modules", "staticfiles", "media"}:
                continue
            if dirname in residue_dirs or dirname.startswith("tmpedge"):
                violations.append(os.path.join(root, dirname))
                continue
            kept_dirs.append(dirname)
        dirs[:] = kept_dirs

        if should_skip_path(root):
            continue
        for filename in files:
            path = os.path.join(root, filename)
            if (
                filename in residue_names
                or filename.startswith("celerybeat-schedule")
                or filename.endswith(".pyc")
                or filename.endswith(".log")
            ):
                violations.append(path)
    return violations

def check_destructive_dev_scripts():
    """P0/P1: Chặn destructive reset script lọt vào release root/source package.

    Check này là static-only, không phụ thuộc Django/settings. Mục tiêu là
    không cho các entrypoint có khả năng xóa DB/migrations nằm ở root hoặc
    source package production. Dev-only helper chỉ được phép nằm dưới
    tools/dev_only/ và phải có guard xác nhận rõ ràng.
    """
    violations = []
    root_reset = Path("reset_project.py")
    if root_reset.exists():
        violations.append("reset_project.py tồn tại ở project root; destructive reset script bị cấm trong release package.")

    dev_reset = Path("tools/dev_only/reset_project.py")
    if dev_reset.exists():
        text = dev_reset.read_text(encoding="utf-8", errors="ignore")
        if "SCMD_ALLOW_DESTRUCTIVE_RESET" not in text or "RESET LOCAL DEV DATABASE" not in text:
            violations.append("tools/dev_only/reset_project.py thiếu confirm phrase SCMD_ALLOW_DESTRUCTIVE_RESET.")
        if "ENVIRONMENT" not in text or "production" not in text.lower():
            violations.append("tools/dev_only/reset_project.py thiếu guard chặn production.")
    return violations


def _module_target_exists(module_name):
    """Return True when an internal module maps to an existing .py file/package."""
    module_path = Path(*module_name.split('.'))
    return (module_path.with_suffix('.py').exists() or (module_path / '__init__.py').exists())


def _relative_import_module(file_path, level, module):
    """Resolve a relative import target for static internal import validation."""
    path = Path(file_path)
    package_parts = list(path.parent.parts)
    if path.name == '__init__.py':
        package_parts = list(path.parent.parts)

    # from .x import y inside package a/b.py -> a.x
    keep = len(package_parts) - level + 1
    if keep < 0:
        return None
    parts = package_parts[:keep]
    if module:
        parts.extend(module.split('.'))
    return '.'.join(part for part in parts if part and part != '.')


def check_internal_import_targets():
    """P1: Bắt các import nội bộ trỏ tới module/file không tồn tại.

    Release packaging có thể vô tình loại thiếu file Python mà compileall không bắt
    được vì compileall chỉ kiểm tra cú pháp, không resolve import runtime. Check này
    tập trung vào import tầng application của các Django app sở hữu, ví dụ:
    - from .application.patrol_use_cases import ...
    - from inspection.application.patrol_use_cases import ...
    """
    violations = []
    for file_path in iter_source_files('.', suffixes=('.py',)):
        path = Path(file_path)
        if path.parts and path.parts[0] in {'.git', 'staticfiles', 'media'}:
            continue
        try:
            tree = ast.parse(path.read_text(encoding='utf-8', errors='ignore'))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            module_name = None
            if node.level:
                module_name = _relative_import_module(path, node.level, node.module)
            elif node.module:
                module_name = node.module
            if not module_name:
                continue
            if '.application.' not in module_name and not module_name.endswith('.application'):
                continue
            if not _module_target_exists(module_name):
                violations.append(f"{path}:{node.lineno}: thiếu module import nội bộ '{module_name}'")
    return violations



def check_forbidden_release_artifacts():
    """P0: Chặn dữ liệu nhạy cảm và artifact local lọt vào release package.

    Khác với check_runtime_residue, check này cố ý kiểm tra cache/bytecode,
    media thực, credential local, dependency folder và virtualenv. Các thư mục
    lớn như virtualenv/node_modules được ghi nhận là P0 rồi prune ngay để tránh
    timeout khi audit ZIP đã extract.
    """
    violations = []
    forbidden_exact = {
        ".env": "Credential/runtime secret thật không được nằm trong source ZIP.",
        "reset_project.py": "Destructive reset helper không được nằm ở project root/release package.",
    }
    forbidden_prefixes = {
        "media": "Dữ liệu upload/PII không được nằm trong source ZIP.",
        "node_modules": "Dependency build local không được nằm trong source ZIP/release package.",
        "staticfiles": "Collected static output không được nằm trong source ZIP; chỉ generate bằng collectstatic khi deploy.",
        "tmp-edge-profile": "Browser/runtime profile không được nằm trong source ZIP.",
        "tmpedge2": "Browser/runtime profile không được nằm trong source ZIP.",
        "venv": "P0: Virtualenv detected in source ZIP/release package; clean source không được chứa môi trường Python local.",
        ".venv": "P0: Virtualenv detected in source ZIP/release package; clean source không được chứa môi trường Python local.",
        "env": "P0: Virtualenv detected in source ZIP/release package; clean source không được chứa môi trường Python local.",
    }
    forbidden_names = {
        "dump.rdb": "Redis dump không được nằm trong source ZIP.",
        "celerybeat-schedule": "Celery beat state không được nằm trong source ZIP.",
        "celerybeat-schedule-shm": "Celery beat state không được nằm trong source ZIP.",
        "celerybeat-schedule-wal": "Celery beat state không được nằm trong source ZIP.",
    }

    for root, dirs, files in os.walk('.', topdown=True):
        root_path = Path(root)
        if '.git' in root_path.parts:
            dirs[:] = []
            continue

        kept_dirs = []
        for dirname in dirs:
            dir_path = root_path / dirname
            normalized_dir = dir_path.as_posix().lstrip('./')
            matched_reason = None
            for prefix, reason in forbidden_prefixes.items():
                if normalized_dir == prefix or normalized_dir.startswith(prefix + '/'):
                    matched_reason = reason
                    break
            if matched_reason:
                violations.append(f"{normalized_dir}: {matched_reason}")
                continue
            kept_dirs.append(dirname)
        dirs[:] = kept_dirs

        for filename in files:
            path = root_path / filename
            normalized = path.as_posix().lstrip('./')
            if normalized in forbidden_exact:
                violations.append(f"{normalized}: {forbidden_exact[normalized]}")
                continue
            if normalized == "deploy-scmdpro.log":
                violations.append(f"{normalized}: Deployment/runtime log khong duoc nam trong source ZIP.")
                continue
            if path.name in forbidden_names:
                violations.append(f"{normalized}: {forbidden_names[path.name]}")
                continue
            if "__pycache__" in path.parts or path.name == "__pycache__" or path.suffix == ".pyc":
                violations.append(f"{normalized}: Python bytecode/cache không được nằm trong source ZIP.")
                continue
            for prefix, reason in forbidden_prefixes.items():
                if normalized == prefix or normalized.startswith(prefix + '/'):
                    violations.append(f"{normalized}: {reason}")
                    break
    return violations

def check_backup_security_config():
    """Rule 11: Đảm bảo mật khẩu xuất dữ liệu/sao lưu không dùng mặc định."""
    violations = []
    try:
        from django.conf import settings
    except Exception:
        return ["Lỗi: Không thể import Django settings."]

    # P0: Chặn sử dụng mật khẩu mặc định trong code
    if getattr(settings, 'EXCEL_EXPORT_PASSWORD', '') == 'SCMD_PROTECT_2026':
        violations.append("EXCEL_EXPORT_PASSWORD đang sử dụng giá trị mặc định không an toàn.")
    
    # P0: Kiểm tra ranh giới bảo mật Production
    env = os.environ.get('ENVIRONMENT', 'development').lower()
    if env == 'production':
        if settings.DEBUG:
            violations.append("SECURITY ALERT: DEBUG=True đang bật trong môi trường PRODUCTION.")
        
        # Rule 11: Chặn reset script trong production
        if os.path.exists('reset_project.py'):
            violations.append("SECURITY ALERT: Phát hiện file 'reset_project.py' trong production root!")

    # P1: Kiểm tra quyền thư mục backup cục bộ (nếu có)
    if os.path.exists('backups') and (os.stat('backups').st_mode & 0o777) > 0o700:
        violations.append("Thư mục 'backups/' đang sai quyền (Kỳ vọng: 700).")

    # P1: Kiểm tra cấu hình Organization ID (WHITEPAPER Rule 4.1)
    if not getattr(settings, 'SCMD_ORGANIZATION_ID', None):
        violations.append("Thiếu cấu hình SCMD_ORGANIZATION_ID trong settings.")

    return violations


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="SCMD Pro release contract validator."
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("SCMD_RELEASE_ROOT"),
        help="Project root to audit. Supports extracted ZIP directories without .git.",
    )
    parser.add_argument(
        "--audit-zip",
        action="store_true",
        help="Run in ZIP/audit mode: do not require VCS metadata and ignore collected artifacts.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    # Đảm bảo làm việc tại root để các đường dẫn tương đối hoạt động chính xác.
    # Audit ZIP mode không phụ thuộc .git; chỉ cần thư mục có manage.py hoặc cấu trúc Django.
    project_root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    if not project_root.exists():
        print(f"❌ RELEASE REJECTED: root không tồn tại: {project_root}")
        sys.exit(1)
    os.chdir(project_root)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    django_ready = setup_django()
    
    print("--- SCMD Pro Release Contract Check v3.5.0 ---")
    if args.audit_zip:
        print("Audit ZIP mode: enabled; VCS metadata is not required.")
    checks = [
        ("P0: Merge conflict markers", check_conflict_markers()),
        ("P0: Python in static/", check_static_python()),
        ("P0: Python in templates/", check_template_python()),
        ("P0: External font CDN usage", check_external_font_cdn()),
        ("P0: Runtime vendor stubs", check_vendor_stub_assets()),
        ("P1: Wildcard imports (application/)", check_wildcard_imports()),
        ("P1: Manager SSOT (core.managers)", check_manager_ssot()),
        ("P1: Migration graph (no branches)", check_migration_graph()),
        ("P1: Internal import targets", check_internal_import_targets()),
        ("P2: Tailwind CDN in templates", check_tailwind_cdn()),
        ("P2: Legacy brand language (UI cleanup)", check_legacy_brand_language()),
        ("P2: Runtime residue (cache/bytecode/logs)", check_runtime_residue()),
        ("P0: Forbidden release artifacts", check_forbidden_release_artifacts()),
        ("P0: Destructive reset scripts", check_destructive_dev_scripts()),
    ]
    
    if django_ready:
        checks.append(("P1: Backup & Export Security Configuration", check_backup_security_config()))
    
    failed = False
    for desc, violations in checks:
        if violations:
            print(f"❌ [FAIL] {desc}")
            for v in violations: print(f"   - {v}")
            failed = True
        else: print(f"✅ [PASS] {desc}")
            
    if failed:
        print("\n❌ RELEASE REJECTED: Vi phạm hợp đồng kiến trúc. Xem WHITEPAPER.md.")
        sys.exit(1)
    print("\n✅ All contract checks passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()


