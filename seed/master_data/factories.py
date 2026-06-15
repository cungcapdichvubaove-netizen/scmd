"""Master-data factories for SCMD Pro Digital Twin."""

from django.contrib.auth.models import Group

from main.models import CompanyInfo
from users.models import ChucDanh, PhongBan, CauHinhMaNhanVien
from seed.orchestrator.utils import get_group, save_validated

DEPARTMENTS = [
    "Điều hành",
    "Nhân sự",
    "Tuyển dụng",
    "Đào tạo",
    "Tài chính",
    "Kế toán",
    "Kinh doanh",
    "CSKH",
    "SOC",
    "IT",
    "Camera AI",
    "Kho vận",
    "Mua sắm",
]

ROLES = [
    ("CEO", "ban_giam_doc"),
    ("COO", "ban_giam_doc"),
    ("Regional Director", "quan_ly_vung"),
    ("Area Manager", "quan_ly_vung"),
    ("Site Commander", "doi_truong"),
    ("Team Leader", "doi_truong"),
    ("Guard", "bao_ve"),
    ("Kế toán", "ke_toan"),
    ("Điều phối SOC", "nhan_vien"),
    ("Thủ kho", "nhan_vien"),
]

BRANCHES = [
    {"code": "HN", "name": "Chi nhánh Hà Nội", "address": "Tòa nhà SCMD, Hoàn Kiếm, Hà Nội"},
    {"code": "DN", "name": "Chi nhánh Đà Nẵng", "address": "Hải Châu, Đà Nẵng"},
    {"code": "HCM", "name": "Chi nhánh TP.HCM", "address": "Quận 1, TP.HCM"},
]


def seed_master_data(ctx):
    CompanyInfo.objects.update_or_create(
        tenant_id=ctx.tenant_id,
        defaults={
            "ten_cong_ty": "SCMD Pro Digital Twin Security Group",
            "ten_phap_ly": "Công ty Cổ phần Dịch vụ Bảo vệ SCMD Digital Twin",
            "ma_so_thue": "0109999999",
            "dia_chi": "Tòa nhà SCMD, Hoàn Kiếm, Hà Nội",
            "dien_thoai": "02439999999",
            "hotline": "19009999",
            "email": "contact@scmdpro.local",
            "website": "https://scmdpro.local",
            "nguoi_dai_dien": "Nguyễn Minh An",
            "chuc_vu_nguoi_dai_dien": "Tổng Giám đốc",
            "ghi_chu": "Digital Twin synthetic dataset. Không chứa dữ liệu cá nhân thật.",
        },
    )
    ctx.count("company")

    CauHinhMaNhanVien.objects.get_or_create(defaults={"tien_to": "DTNV", "do_dai_so": 6, "so_hien_tai": 0})

    departments = {}
    for name in DEPARTMENTS:
        group = get_group(name)
        obj, _ = PhongBan.objects.get_or_create(
            ten_phong_ban=name,
            defaults={"tenant_id": ctx.tenant_id, "mo_ta": "Digital Twin department", "nhom_quyen": group},
        )
        departments[name] = obj
    ctx.count("departments", len(departments))

    titles = {}
    for title, group_name in ROLES:
        group = get_group(group_name)
        obj, _ = ChucDanh.objects.get_or_create(
            ten_chuc_danh=title,
            defaults={"mo_ta": f"Digital Twin role: {title}", "nhom_quyen": group},
        )
        titles[title] = obj
    ctx.count("job_titles", len(titles))
    ctx.write_jsonl("master-data/branches.jsonl", BRANCHES)
    ctx.count("branches", len(BRANCHES))
    return {"departments": departments, "titles": titles, "branches": BRANCHES}
