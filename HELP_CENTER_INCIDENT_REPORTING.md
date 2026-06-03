# Hướng dẫn sử dụng tính năng Báo cáo sự cố (Incident Reporting)

## 1. Giới thiệu

Tính năng Báo cáo sự cố trong hệ thống SCMD cho phép nhân viên bảo vệ và quản lý nhanh chóng ghi nhận, theo dõi và xử lý các sự cố phát sinh tại mục tiêu. Hệ thống hỗ trợ báo cáo từ ứng dụng di động và hiển thị cảnh báo theo thời gian thực trên Dashboard War Room.

## 2. Các loại sự cố có thể báo cáo

Hệ thống hỗ trợ phân loại sự cố theo mức độ nghiêm trọng:

*   **Thấp (Nhắc nhở)**: Các vi phạm nhỏ, cần nhắc nhở hoặc ghi nhận nội bộ.
*   **Trung bình (Lập biên bản)**: Các sự việc cần lập biên bản, có thể liên quan đến quy trình hoặc tài sản nhỏ.
*   **Cao (Thiệt hại tài sản)**: Các sự cố gây thiệt hại đáng kể về tài sản.
*   **Nguy hiểm (Đe dọa tính mạng/An ninh)**: Các tình huống khẩn cấp, đe dọa an toàn tính mạng, an ninh mục tiêu hoặc các sự cố nghiêm trọng khác.

## 3. Cách báo cáo sự cố từ ứng dụng di động

1.  **Đăng nhập vào ứng dụng SCMD Mobile**: Đảm bảo bạn đã đăng nhập bằng tài khoản nhân viên của mình.
2.  **Truy cập mục "Báo cáo sự cố"**: Thường nằm trên Dashboard chính hoặc trong menu điều hướng.
3.  **Điền thông tin báo cáo**:
    *   **Tiêu đề sự cố**: Tóm tắt ngắn gọn về sự việc (ví dụ: "Mất tài sản tại Kho A", "Xô xát tại cổng chính").
    *   **Mục tiêu**: Hệ thống sẽ tự động đề xuất mục tiêu bạn đang trực. Nếu không, hãy chọn mục tiêu phù hợp.
    *   **Mức độ nghiêm trọng**: Chọn mức độ phù hợp nhất với sự cố (Thấp, Trung bình, Cao, Nguy hiểm).
    *   **Mô tả chi tiết**: Cung cấp thông tin đầy đủ về diễn biến sự cố, thời gian, địa điểm cụ thể, các bên liên quan và hành động đã thực hiện. Bạn có thể sử dụng tính năng ghi âm (nếu có) để tường trình.
    *   **Ảnh hiện trường**: Đính kèm tối đa 2 ảnh chụp hiện trường để làm bằng chứng.
    *   **File ghi âm**: Đính kèm file ghi âm (nếu có) để cung cấp thêm thông tin.
4.  **Gửi báo cáo**: Sau khi điền đầy đủ thông tin, nhấn nút "Gửi báo cáo".

## 4. Xử lý sự cố và thông báo Real-time

Ngay sau khi báo cáo được gửi:

*   **Mã vụ việc tự động**: Hệ thống sẽ tự động gán một mã vụ việc duy nhất (ví dụ: `SC-YYYYMMDD-HEX`) cho báo cáo của bạn.
*   **Nén ảnh tự động**: Các ảnh đính kèm sẽ được tự động nén ở chế độ nền để tối ưu hóa dung lượng lưu trữ.
*   **Cảnh báo tức thời**:
    *   Một cảnh báo sẽ được gửi ngay lập tức đến Dashboard War Room của quản lý và các bên liên quan thông qua WebSocket.
    *   Tùy thuộc vào mức độ nghiêm trọng, hệ thống có thể kích hoạt các hành động bổ sung như gửi email hoặc SMS đến các cấp quản lý cao hơn.
*   **Theo dõi trạng thái**: Quản lý có thể theo dõi trạng thái xử lý của sự cố (Chờ xử lý, Đang xử lý, Đã xử lý, Chờ đền bù, Hoàn tất, Đã hủy) trên Dashboard.

## 5. Chức năng SOS khẩn cấp

Trong trường hợp khẩn cấp đe dọa tính mạng hoặc an ninh nghiêm trọng, bạn có thể sử dụng tính năng SOS:

1.  **Trên Dashboard Mobile**: Tìm nút "SOS" hoặc "Cấp cứu".
2.  **Nhấn và giữ (hoặc xác nhận)**: Hệ thống sẽ gửi ngay lập tức một tín hiệu khẩn cấp với vị trí GPS hiện tại của bạn đến Dashboard War Room.
3.  **Thông báo**: Một báo cáo sự cố với mức độ "Nguy hiểm" sẽ được tạo tự động, kèm theo tiêu đề "CẤP CỨU: [Tên nhân viên]".

## 6. Lưu ý quan trọng

*   **Thông tin chính xác**: Luôn cung cấp thông tin chính xác và đầy đủ nhất có thể để hỗ trợ quá trình xử lý.
*   **Bằng chứng**: Ảnh và ghi âm là bằng chứng quan trọng, hãy đảm bảo chúng rõ ràng và liên quan đến sự cố.
*   **Không lạm dụng SOS**: Chỉ sử dụng tính năng SOS trong các tình huống khẩn cấp thực sự.

Nếu có bất kỳ thắc mắc nào về việc sử dụng tính năng này, vui lòng liên hệ với quản lý trực tiếp hoặc bộ phận hỗ trợ kỹ thuật.