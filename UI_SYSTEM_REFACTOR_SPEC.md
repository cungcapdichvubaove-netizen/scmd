# UI_SYSTEM_REFACTOR_SPEC.md — SCMD Pro UI/System Refactor Specification

<<<<<<< HEAD
Version: 3.5.0-access-scope-docs-v4
Status: **Active implementation spec — included as UI governance dependency for Access Scope docs v4**
Updated: 2026-06-08

Tài liệu này map công việc refactor UI, brand language và frontend/runtime surface vào các file thực tế trong Django repository. Mục tiêu là đưa SCMD Pro về đúng định vị: phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp, không phải cyber dashboard hay war-room demo.


Patch note — access-scope-docs-v4:
- Included in the Access Scope documentation patch so AI/coder agents have the UI/brand governance file referenced by `DOCUMENTATION.md`, `WHITEPAPER.md` and `.cursorrules`.
- No runtime UI implementation is implied by this docs-only patch.

=======
Version: 3.5.0
Status: **Active implementation spec**
Updated: 2026-06-03

Tài liệu này map công việc refactor UI, brand language và frontend/runtime surface vào các file thực tế trong Django repository. Mục tiêu là đưa SCMD Pro về đúng định vị: phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp, không phải cyber dashboard hay war-room demo.

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
Patch note 3.5.0:
- Chuẩn hóa định vị thương hiệu mới: **SCMD** là công ty/thương hiệu mẹ; **SCMD Pro** là tên user-facing của sản phẩm; tagline là **Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp**.
- `SCMD ERP` và các tên cũ phải được đổi thành `SCMD Pro` trên UI sản phẩm; `SCMD` chỉ dùng cho công ty/thương hiệu mẹ, pháp lý, copyright, about/vendor.
- `main/templates/main/homepage.html` và `main/templates/main/login.html` phải dùng palette navy/blue, tiếng Việt chuẩn và local Tailwind build.

---

## 1. Product Positioning

### 1.1 SCMD / SCMD Pro là

- **SCMD**: công ty công nghệ phần mềm cho ngành dịch vụ bảo vệ.
- **SCMD Pro**: sản phẩm phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp.
- Security Commander Platform cho vận hành bảo vệ vật lý, điều phối hiện trường và quản trị nội bộ.
- Operations workspace cho điều phối, lãnh đạo, kế toán, nhân sự, kho, thanh tra.
- Data-first system: ca trực, chấm công, GPS, ảnh, sự cố, quân số, lương, kho.
- Hệ thống tiếng Việt chuẩn UTF-8, ưu tiên rõ ràng và đáng tin.

### 1.2 SCMD Pro không phải

- Tên rút gọn của “ERP” theo nghĩa phần mềm kế toán/hành chính chung chung.
- Cyber command center.
- Tactical/war-room UI.
- Landing page marketing với hiệu ứng neon.
- Multi-brand product surface.
- Generic ERP không có domain language bảo vệ.

---

## 2. Language Contract

Tên user-facing của sản phẩm: **SCMD Pro**. Tên công ty/thương hiệu mẹ: **SCMD**. Dòng mô tả chính thức: **Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp**.

| Cấm trong UI sản phẩm | Thay bằng |
|---|---|
| SCMD ERP | SCMD Pro |
| Security Command System | SCMD Pro |
| Sentinel Command System | SCMD Pro |
| SCMD như tên sản phẩm bán hàng chính | SCMD Pro |
| War Room | Bảng điều hành vận hành |
| Command Center nếu dùng kiểu war-room | Bảng điều hành vận hành / Trung tâm điều hành SCMD Pro |
| Tactical | Xóa hoặc thay bằng từ nghiệp vụ cụ thể |
| Enterprise Security Management | Phần mềm chỉ huy và quản trị dịch vụ bảo vệ hoặc xóa |
Ngoại lệ hợp lệ:

- `Mục tiêu bảo vệ`
- `Chốt bảo vệ`
- `Ca trực`
- `Tuần tra`
- `Sự cố`
- `Quân số`
- `Bảo vệ`

Đây là domain language, không phải theater language.

---

## 3. Django Surface Map

### 3.1 Shell & Navigation

```text
templates/base.html                          Authenticated shell wrapper
templates/base_public.html                   Public/unauthenticated wrapper
templates/partials/_sidebar.html             Sidebar layout
templates/partials/sidebar_menu_items.html   Sidebar nav items
templates/includes/scripts.html              Shared JS includes
```

Acceptance:

- Sidebar copy dùng tiếng Việt nghiệp vụ.
- Không còn “command center”, “war room”, “tactical”.
- Active state rõ, tương phản tốt, không neon/glow.

### 3.2 Dashboard

```text
dashboard/templates/dashboard/main.html
dashboard/templates/dashboard/index.html
dashboard/views.py
dashboard/application/executive_dashboard.py
static/js/war_room_alive_check.js
static/js/war_room_worker_monitor.js
static/js/war_room_payroll_listener.js
```

Target:

- Đổi `War Room` thành `Bảng điều hành vận hành` hoặc `Operations Cockpit` tùy vị trí.
- JS file có thể đổi tên dần nếu không gây vỡ import; nếu chưa đổi, ít nhất comment/copy user-facing phải sạch.
- KPI dùng màu trạng thái nghiệp vụ, không dùng cyber token.

Acceptance:

- Dashboard title/copy không còn brand cũ.
- KPI có label tiếng Việt chuẩn dấu.
- Empty/loading/error state rõ ràng.
- Không có số liệu demo hardcoded trong production path.

### 3.3 Admin Workspace

```text
config/jazzmin_conf.py
templates/admin/base_site.html
templates/admin/index.html
static/common/css/custom_admin.css
static/common/css/admin_tweaks.css
```

Target:

- `/admin/` = Technical Console.
- Admin title: `SCMD Admin` hoặc `SCMD Technical Console`.
- Không biến admin thành dashboard nghiệp vụ.
- Sửa dữ liệu nhạy cảm qua admin phải được audit theo backend policy.

Acceptance:

- Admin branding thống nhất SCMD.
- Không còn “Security Command”, “Sentinel”, “War Room”.
- Admin CSS dùng brand tokens, không neon.

### 3.4 Authentication / Public Pages

```text
main/templates/main/login.html
main/templates/main/homepage.html
templates/base_public.html
```

Target:

- Login là cổng vào SCMD — nền tảng chỉ huy và quản trị nội bộ.
- Homepage nếu còn tồn tại phải giới thiệu SCMD như nền tảng chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ, không dùng cyber marketing.
- Xóa `cdn.tailwindcss.com`.

Acceptance:

- `grep -R "cdn.tailwindcss.com" -n main templates` không còn hit trong file do team sở hữu.
- Login hiển thị SCMD Pro.
- Copy tiếng Việt rõ, không mojibake.

### 3.5 Print / Export

```text
templates/admin/users/nhanvien/print_profile.html
templates/admin/users/nhanvien/print_profile_bulk.html
reports/templates/
accounting/templates/
```

Target:

- Print/export phải mang brand SCMD.
- Không dùng Tailwind CDN production.
- Dữ liệu nhạy cảm phải có permission và audit backend.

Acceptance:

- Print template không phụ thuộc CDN nếu chạy production.
- Header/footer rõ tên công ty/hệ thống.
- Nội dung tiếng Việt chuẩn UTF-8.

### 3.6 Visual Tokens

```text
<<<<<<< HEAD
theme/tailwind.config.js
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
static/common/css/brand_system.css
tailwind.config.js
theme/static_src/src/styles.css
theme/static/css/dist/styles.css
```

Target:

- Brand token là SSOT cho màu.
- Tailwind build local.
- Không hardcode màu cyber trên surface nội bộ.

---

## 4. Brand Color System

### 4.1 Primary colors

| Token | Vai trò |
|---|---|
| Navy | Header, sidebar, primary shell |
| Blue | Primary action, link, focus state |
| Neutral | Background, card, border, text |

### 4.2 Business state colors

| State | Dùng cho |
|---|---|
| Success | Hoàn tất, đã check-in, đã xác nhận |
| Warning | Cần chú ý, thiếu dữ liệu, sắp quá hạn |
| Danger | Sự cố nghiêm trọng, trễ hạn, lỗi, thiếu quân số |
| Info | Thông tin phụ, trạng thái đang xử lý |
| Neutral | Draft, chưa phát sinh, không có cảnh báo |

### 4.3 Cấm trên internal ERP surface

- Neon cyan/orange/purple dùng kiểu cyber.
- Glow effect không có mục đích usability.
- Animated tactical grid/radar/war-room motifs.
- Mỗi module một màu rực không có meaning nghiệp vụ.

---

## 5. UX Contract

### 5.1 Nguyên tắc chung

- Tốc độ đọc và độ rõ ràng quan trọng hơn hiệu ứng.
- Người dùng nghiệp vụ phải hiểu trạng thái trong 3 giây.
- Màu chỉ dùng khi có meaning.
- Label tiếng Việt phải có dấu, không mojibake.
- Empty state phải nói rõ cần làm gì tiếp theo.
- Error state phải hướng dẫn hành động, không chỉ báo lỗi kỹ thuật.

### 5.2 Dashboard cards

Mỗi KPI card nên có:

- title ngắn,
- số chính,
- trạng thái hoặc trend nếu có,
- nguồn/ý nghĩa rõ,
- link drill-down nếu có.

Không dùng KPI nếu chưa có nguồn dữ liệu thật hoặc chưa document rõ.

### 5.3 Tables

- Cột quan trọng đặt trước.
- Trạng thái hiển thị bằng text + màu, không chỉ màu.
- Action nguy hiểm phải có confirm.
- Bảng dữ liệu nhạy cảm phải tôn trọng permission.

### 5.4 Forms

- Field label tiếng Việt rõ.
- Validation error gần field.
- Không dùng placeholder thay label.
- Field nhạy cảm như lương/GPS/khấu trừ phải có help text nếu dễ hiểu sai.

---

## 6. Implementation Phases

### Phase 0 — Baseline scan

Mục tiêu: lập baseline trước khi sửa.

Commands:

```bash
grep -R "cdn.tailwindcss.com" -n .
grep -R "Security Command\|Sentinel Command\|War Room\|Tactical\|SCMD Pro" -n templates static main dashboard users operations accounting clients
grep -R "cyber-\|neon\|glow" -n templates static
<<<<<<< HEAD
grep -RInP "[\\x{FFFD}]|Ã|Â" templates static main dashboard users operations accounting clients
=======
grep -R "�\|Ã\|Â" -n templates static main dashboard users operations accounting clients
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
find static/ -name "*.py"
find . -path "*/templates/*" -name "*.py"
```

Deliverable:

- danh sách file cần sửa,
- phân loại P0/P1/P2,
- xác định file vendor để loại khỏi backlog nếu không thuộc code team sở hữu.

### Phase 1 — P0/P1 debt clearance

Ưu tiên:

1. Xóa/chuyển file `.py` khỏi `static/`.
2. Xử lý `.py` trong `templates/`.
3. Xóa Tailwind CDN khỏi login/homepage nếu đang dùng production path.
4. Đảm bảo static build local hoạt động.

Definition of Done:

- `find static/ -name "*.py"` không còn file do team sở hữu.
- `find . -path "*/templates/*" -name "*.py"` không còn file do team sở hữu.
- `grep -R "cdn.tailwindcss.com" -n main templates` không còn hit trong file production.
- Login và homepage render được.

### Phase 2 — Brand rename & copy cleanup

Ưu tiên file:

1. `dashboard/templates/dashboard/*`
2. `main/templates/main/homepage.html`
3. `main/templates/main/login.html`
4. `templates/base*.html`
5. `templates/partials/*`
6. admin templates
7. print/export templates
8. JS/CSS comments/user-facing messages

Definition of Done:

- Không còn brand cũ trong user-facing copy.
- Dashboard title đổi khỏi `War Room`.
- Login/homepage dùng SCMD.
- Copy tiếng Việt chuẩn dấu.

### Phase 3 — Token enforcement

Ưu tiên:

1. Chuẩn hóa `brand_system.css`.
2. Đồng bộ `tailwind.config.js`.
3. Thay màu hardcode cyber/neon.
4. Kiểm tra contrast cho text/card/button/status.

Definition of Done:

- Không còn class/token cyber trên template chính.
- State colors dùng nhất quán.
- Primary action/link/focus state rõ.

### Phase 4 — ERP workspace hardening

Ưu tiên:

- Dashboard card labels.
- Empty/loading/error states.
- Table action clarity.
- Mobile/responsive layout cho dashboard và forms quan trọng.
- Permission-aware UI: không hiển thị action người dùng không có quyền thực hiện.

Definition of Done:

- Dashboard dùng được cho vận hành hằng ngày.
- Không có action nguy hiểm thiếu confirm.
- Empty/error state rõ.
- Responsive không vỡ trên tablet/mobile cơ bản.

### Phase 5 — Print/export long-tail

Ưu tiên:

- Employee profile print.
- Payroll export.
- Incident report export.
- Inventory issue/receipt print.

Definition of Done:

- Header/footer SCMD.
- Không CDN production.
- Tiếng Việt chuẩn UTF-8.
- Permission/audit backend đã có hoặc có issue blocker.

---

## 7. Backlog đã xác nhận từ code review

| Priority | Finding | Action |
|---|---|---|
| P0 | `.py` trong `static/js/` | Xóa khỏi static, chuyển logic về app/application |
| P1/P0 tùy deploy | `.py` trong `templates/` | Chuyển khỏi templates, xác định exposure risk |
| P1 | Wildcard application facade | Tạo use case class thật, xóa re-export |
| P1 | Duplicate manager scope | Gom về core SSOT |
| P2 | Tailwind CDN trong login/homepage/print | Build local hoặc CSS kiểm soát |
| P2 | War-room/cyber copy | Rename sang SCMD / Bảng điều hành vận hành |
| P2 | Mojibake trong file nội bộ | Chuẩn hóa UTF-8 |
| P2 | Cyber/neon colors | Chuyển về brand tokens |

---

## 8. UI QA Checklist

### Brand

- [ ] Tên user-facing của sản phẩm là SCMD Pro.
- [ ] Tagline hiển thị đúng: Nền tảng chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp.
- [ ] Không còn SCMD Pro trên UI chính, trừ tài liệu/tooltip giải thích năng lực ERP.
- [ ] Không còn Security Command/Sentinel/War Room/Tactical.
- [ ] `/dashboard/` là Bảng điều hành vận hành.
- [ ] `/admin/` là Technical Console/Admin.

### Frontend runtime

- [ ] Không còn `cdn.tailwindcss.com` trong template production.
- [ ] Tailwind local build chạy được.
- [ ] Compiled CSS được serve đúng.
- [ ] Không có file Python trong static/templates do team sở hữu.

### Visual

- [ ] Màu chính: navy/blue/neutral.
- [ ] Màu trạng thái có meaning nghiệp vụ.
- [ ] Không neon/glow/cyber motif trên internal ERP surfaces.
- [ ] Contrast đủ đọc.

### Content

- [ ] Tiếng Việt có dấu.
- [ ] Không mojibake.
- [ ] Empty state có hướng dẫn.
- [ ] Error state có hành động tiếp theo.

### Security/permission UI

- [ ] Action nhạy cảm chỉ hiện khi có quyền.
- [ ] Export nhạy cảm có warning/permission.
- [ ] Delete/void/lock/unlock có confirm.

---

## 9. Recommended PR split

Không nên sửa toàn bộ UI trong một PR lớn. Nên chia:

1. `ui/p0-static-template-cleanup`
2. `ui/remove-tailwind-cdn`
3. `ui/brand-copy-dashboard-login`
4. `ui/admin-technical-console-branding`
5. `ui/brand-token-enforcement`
6. `ui/print-export-branding`
7. `ui/mojibake-cleanup-owned-files`

Mỗi PR phải có screenshot trước/sau hoặc mô tả QA nếu không có screenshot.
<<<<<<< HEAD

---

## 12. V15 Responsive & State Contract

Patch note V15 — Compact Operations Admin hardening:

- Mobile shell must be SCMD Pro branded. Boilerplate strings such as `Django Tailwind`, `Django + Tailwind = ❤️`, and demo daisyUI toast content are prohibited on runtime templates.
- Module dashboards must use the shared `brand_system.css` tokens and shared dashboard components. Module-specific classes are allowed only as modifiers, not as independent mini design systems.
- Loading, empty and error states must use shared state classes so users can distinguish: data is loading, there is no open work, or a source failed.

### 12.1 Breakpoint contract

All SCMD Pro UI surfaces should use the same breakpoint language:

| Name | Width range | Intended use |
|---|---:|---|
| `xs` | `0–479px` | Small phones, one-handed field operation |
| `sm` | `480–639px` | Large phones |
| `md` | `640–767px` | Small tablets / large phone landscape |
| `lg` | `768–1023px` | Tablet landscape / compact desktop |
| `xl` | `1024–1279px` | Standard desktop |
| `2xl` | `>=1280px` | Wide desktop / control room display |

Do not introduce ad-hoc breakpoints such as `980px`, `1180px`, or `1280px` inside module-specific CSS unless the value is documented here and justified by a real viewport bug.

### 12.2 Shared dashboard component classes

Use shared component classes for dashboard UI:

```text
.scmd-dashboard
.scmd-dashboard-header
.scmd-dashboard-grid
.scmd-metric-card
.scmd-status-card
.scmd-panel
.scmd-data-table
.scmd-progress
.scmd-pipeline
.scmd-empty-state
.scmd-error-state
.scmd-skeleton
.scmd-skeleton-card
.scmd-skeleton-line
.scmd-skeleton-table-row
```

Allowed module modifiers:

```text
.scmd-dashboard--inventory
.scmd-dashboard--accounting
.scmd-dashboard--operations
.scmd-dashboard--inspection
.scmd-dashboard--crm
```

Do not create a full new visual vocabulary per module unless there is a product-level exception approved in this file.

### 12.3 Loading, empty and error states

Every async or computed dashboard region must distinguish these states:

| State | Required class | User meaning |
|---|---|---|
| Loading | `.scmd-state--loading` or `.scmd-skeleton-*` | Data is still loading |
| Empty | `.scmd-state--empty` | Data loaded successfully and no open work exists |
| Error | `.scmd-state--error` | Data source failed or is temporarily unavailable |

Skeleton animation must respect `prefers-reduced-motion`.
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
