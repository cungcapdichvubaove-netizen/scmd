# SCMD Brand Migration Guide — 3.5.0

## Quyết định thương hiệu

Kiến trúc thương hiệu chính thức:

> **SCMD**  
> Công ty công nghệ phần mềm cho ngành dịch vụ bảo vệ

> **SCMD Pro**  
> Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp

SCMD là viết tắt của **Security Commander**. SCMD Pro là sản phẩm thương mại chính được bán cho các doanh nghiệp dịch vụ bảo vệ.

## Nguyên tắc đổi tên

- `SCMD ERP` → `SCMD Pro` trên UI sản phẩm, login, dashboard, admin title, PWA manifest, print/export, tài liệu bán hàng và tài liệu hướng dẫn người dùng.
- `SCMD` dùng cho công ty/thương hiệu mẹ, copyright, pháp lý, chủ sở hữu, about/vendor và kiến trúc thương hiệu.
- `ERP` không dùng làm tên sản phẩm. ERP chỉ là nhóm năng lực bên trong SCMD Pro: nhân sự, khách hàng, hợp đồng, mục tiêu, ca trực, kho, lương, tài chính, báo cáo.
- Không dùng `ESP` làm tên sản phẩm chính. Có thể dùng `Enterprise Security Platform` như mô tả phân loại nếu thật sự cần tiếng Anh.

## Dòng định vị chuẩn

### Công ty

**SCMD — Công ty công nghệ phần mềm cho ngành dịch vụ bảo vệ.**

### Sản phẩm

**SCMD Pro — Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp.**

### Mô tả ngắn

SCMD Pro giúp doanh nghiệp dịch vụ bảo vệ quản lý tập trung khách hàng, hợp đồng, mục tiêu, ca trực, chấm công, tuần tra, sự cố, quân số, kho, lương và báo cáo vận hành trên một nền tảng thống nhất.

## Checklist thay thế trong code/tài liệu

```bash
<<<<<<< HEAD
grep -RInE "War Room|WarRoom|Sentinel|Tactical|Cyber|SCMD ERP|ESP" -n templates static main dashboard users operations accounting clients *.md
=======
grep -R "SCMD ERP\|Security Command System\|Sentinel Command System\|War Room\|Tactical\|ESP" -n templates static main dashboard users operations accounting clients *.md
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
grep -R "SCMD Pro" -n templates static main dashboard users operations accounting clients *.md
```

## Quy tắc UI

- Login/public pages: hiển thị **SCMD Pro**.
- Dashboard: **Bảng điều hành vận hành SCMD Pro** hoặc **Bảng điều hành vận hành** tùy không gian UI.
- Admin: **SCMD Pro Admin** hoặc **SCMD Pro Technical Console**.
- PWA/mobile app: **SCMD Pro**.
- Print/export: header dùng **SCMD Pro**; footer/copyright có thể ghi **© SCMD**.

## Quy tắc không được làm

- Không quay lại tên `SCMD ERP` làm brand chính.
- Không dùng logo/hình ảnh tạo cảm giác công ty bảo vệ trực tiếp thay vì công ty phần mềm.
- Không dùng war-room/cyber/neon/tactical language trên UI nghiệp vụ.
- Không dùng `SCMD` lẫn `SCMD Pro` tùy tiện; luôn phân biệt công ty và sản phẩm.
<<<<<<< HEAD
Status note:
- This is a migration/support guide for brand-normalization work.
- Current source of truth remains `README.md`, `WHITEPAPER.md`, `DOCUMENTATION.md`, and `UI_SYSTEM_REFACTOR_SPEC.md`.
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
