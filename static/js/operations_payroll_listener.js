/**
 * SCMD Pro - Payroll Alert Listener
 * Lắng nghe sự kiện từ WebSocket và hiển thị toast notification.
 */

(function () {
    const socketUrl = (window.location.protocol === "https:" ? "wss://" : "ws://")
        + window.location.host
        + "/ws/notifications/";

    const socket = new WebSocket(socketUrl);

    socket.onmessage = function (e) {
        const data = JSON.parse(e.data);
        if (data.type === "payroll_alert") {
            showPayrollToast(data.payload);
        }
    };

    socket.onclose = function () {
        console.warn("SCMD notification socket closed unexpectedly. Reconnecting in 5s...");
        setTimeout(() => window.location.reload(), 5000);
    };

    function getAccountingDashboardUrl() {
        const routeNode = document.querySelector("[data-scmd-accounting-dashboard-url]");
        return routeNode ? routeNode.getAttribute("data-scmd-accounting-dashboard-url") : "";
    }

    function showPayrollToast(payload) {
        const accountingDashboardUrl = getAccountingDashboardUrl();
        let toastContainer = document.querySelector(".toast-container");
        if (!toastContainer) {
            toastContainer = document.createElement("div");
            toastContainer.className = "toast toast-top toast-end z-[9999]";
            document.body.appendChild(toastContainer);
        }

        const alertClass = payload.severity === "CRITICAL" ? "alert-error" : "alert-warning";
        const icon = payload.severity === "CRITICAL" ? "🚫" : "⚠️";

        const toastItem = document.createElement("div");
        toastItem.className = `alert ${alertClass} mb-2 min-w-[350px] animate-bounce flex-col items-start shadow-lg`;

        toastItem.innerHTML = `
            <div class="flex w-full items-center gap-2">
                <span class="text-xl">${icon}</span>
                <div class="flex-1">
                    <h3 class="text-sm font-bold">Cảnh báo quyết toán</h3>
                    <p class="text-xs">${payload.message}</p>
                </div>
                <button class="btn btn-ghost btn-xs" onclick="this.parentElement.parentElement.remove()">✕</button>
            </div>
            <div class="mt-2 flex w-full justify-between border-t border-black/10 pt-1 text-[10px] opacity-70">
                <span>Bảng lương: ${payload.ten_bang_luong}</span>
                <span class="font-bold">Tỷ lệ: ${payload.anomaly_rate}%</span>
            </div>
            ${accountingDashboardUrl ? `
            <a href="${accountingDashboardUrl}" class="btn btn-outline btn-xs btn-block mt-2 border-black/20">
                Kiểm tra ngay
            </a>` : ""}
        `;

        toastContainer.appendChild(toastItem);

        const duration = payload.severity === "CRITICAL" ? 30000 : 10000;
        setTimeout(() => {
            if (toastItem.parentNode) toastItem.remove();
        }, duration);
    }
})();
