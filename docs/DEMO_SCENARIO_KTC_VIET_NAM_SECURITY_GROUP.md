# Demo Scenario — KTC Việt Nam Security Group

## Mục tiêu buổi demo

Tạo một bộ dữ liệu đủ thật để khách hàng thấy SCMD Pro có thể vận hành theo mô hình doanh nghiệp dịch vụ bảo vệ chuyên nghiệp:

- Trụ sở Hà Nội quản trị toàn quốc.
- Chi nhánh Đà Nẵng và Sài Gòn vận hành độc lập theo vùng.
- Dữ liệu hiện trường có chấm công GPS, tuần tra, sự cố, kiểm tra quân số.
- Kho quân tư trang và bảng lương có đủ dữ liệu để đối chiếu.

## Quy mô mặc định V4 Light

```text
60 nhân viên bảo vệ
24 mục tiêu
21 ngày phân công ca
7 ngày dữ liệu chấm công quá khứ
36 sự cố
72 kiểm tra quân số
16 phiếu xuất/cấp phát công cụ
1 kỳ lương demo
```

Quy mô này được tối ưu cho VM demo 1GB RAM + swap, vẫn đủ dữ liệu để demo đa vai trò mà không làm dashboard quá nặng.

## Luồng demo đề xuất

1. Tổng giám đốc đăng nhập để xem bức tranh toàn quốc.
2. Trưởng vận hành xem mục tiêu, ca trực, chấm công, sự cố.
3. Giám đốc chi nhánh xem dữ liệu vùng Đà Nẵng/Sài Gòn.
4. Kinh doanh xem khách hàng, hợp đồng, mục tiêu.
5. Thủ kho xem vật tư, phiếu nhập/xuất, cấp phát.
6. Kế toán xem lương, tạm ứng, khấu trừ.
7. Bảo vệ đăng nhập để xem luồng hiện trường.

## Nguyên tắc an toàn dữ liệu

Mọi dữ liệu demo đều có marker:

```text
[DEMO-KTCVN]
DEMO-KTCVN-*
KTCVN-*
```

Reset demo chỉ được xóa dữ liệu có marker KTCVN. Không hard-delete dữ liệu thật.

## CompanyInfo

Company profile KTC chỉ tự cập nhật hồ sơ trống/default/demo. Nếu muốn cập nhật hồ sơ công ty hiện có trong DB demo cô lập, dùng flag:

```bash
--update-company-info
```

Thông tin demo:

```text
CÔNG TY CỔ PHẦN DỊCH VỤ BẢO VỆ CHUYÊN NGHIỆP KTC VIỆT NAM
MST: 0106004565
Trụ sở: Số 67 đường Phan Đăng Lưu, Xã Phù Đổng, Thành phố Hà Nội, Việt Nam
Người đại diện: NGUYỄN NGỌC THÀNH
Điện thoại: 02436983798
```
