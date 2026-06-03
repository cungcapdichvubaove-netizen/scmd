/**
 * SCMD War Room - Payroll Alert Listener
 * Lắng nghe sự kiện từ WebSocket và hiển thị Toast notification.
 */

(function() {
    const socketUrl = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') 
                    + window.location.host 
                    + '/ws/notifications/';

    const socket = new WebSocket(socketUrl);

    socket.onmessage = function(e) {
        const data = JSON.parse(e.data);

        if (data.type === 'payroll_alert') {
            showPayrollToast(data.payload);
        }
    };

    socket.onclose = function(e) {
        console.warn('SCMD Notification Socket closed unexpectedly. Reconnecting in 5s...');
        setTimeout(() => window.location.reload(), 5000);
    };

    function showPayrollToast(payload) {
        // 1. Tạo hoặc lấy container cho Toast (DaisyUI)
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast toast-top toast-end z-[9999]';
            document.body.appendChild(toastContainer);
        }

        // 2. Xác định màu sắc dựa trên Severity
        const alertClass = payload.severity === 'CRITICAL' ? 'alert-error' : 'alert-warning';
        const icon = payload.severity === 'CRITICAL' ? '🚫' : '⚠️';

        // 3. Xây dựng cấu trúc HTML cho Toast
        const toastItem = document.createElement('div');
        toastItem.className = `alert ${alertClass} shadow-lg mb-2 flex-col items-start min-w-[350px] animate-bounce`;
        
        toastItem.innerHTML = `
            <div class="flex items-center gap-2 w-full">
                <span class="text-xl">${icon}</span>
                <div class="flex-1">
                    <h3 class="font-bold text-sm">CẢNH BÁO QUYẾT TOÁN</h3>
                    <p class="text-xs">${payload.message}</p>
                </div>
                <button class="btn btn-ghost btn-xs" onclick="this.parentElement.parentElement.remove()">✕</button>
            </div>
            <div class="mt-2 text-[10px] opacity-70 w-full flex justify-between border-t border-black/10 pt-1">
                <span>Bảng lương: ${payload.ten_bang_luong}</span>
                <span class="font-bold">Tỷ lệ: ${payload.anomaly_rate}%</span>
            </div>
            <a href="/accounting/dashboard/" class="btn btn-xs btn-block mt-2 btn-outline border-black/20">
                Kiểm tra ngay
            </a>
        `;

        toastContainer.appendChild(toastItem);

        // 4. Tự động xóa sau 10 giây nếu là Warning, 30 giây nếu là Critical
        const duration = payload.severity === 'CRITICAL' ? 30000 : 10000;
        setTimeout(() => {
            if (toastItem.parentNode) toastItem.remove();
        }, duration);
    }
})();