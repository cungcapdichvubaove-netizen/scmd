/**
 * SCMD Pro - Operations Alive Check Listener
 * Lắng nghe WebSocket để cập nhật danh sách vi phạm Alive Check.
 */

document.addEventListener("DOMContentLoaded", function () {
    console.log("Operations Alive Check: DOM Content Loaded.");

    const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const wsHost = window.location.host;
    const wsPath = "/ws/notifications/";
    const websocketUrl = wsProtocol + wsHost + wsPath;

    let aliveCheckSocket = null;
    const violationsList = document.getElementById("alive-check-violations-list");
    const violationsCountBadge = document.getElementById("alive-check-violations-count");
    const alertSound = new Audio("/static/sounds/alert.mp3");

    if (!violationsList || !violationsCountBadge) {
        console.error("Operations Alive Check: Không tìm thấy phần tử HTML cần thiết.");
        return;
    }

    function connectWebSocket() {
        aliveCheckSocket = new WebSocket(websocketUrl);

        aliveCheckSocket.onopen = function () {
            console.log("Operations Alive Check: WebSocket connection established.");
        };

        aliveCheckSocket.onmessage = function (e) {
            const data = JSON.parse(e.data);
            console.log("Operations Alive Check: Received message:", data);

            if (data.type === "ALIVE_CHECK_ALERT" || data.type === "ALIVE_CHECK_EXPIRED") {
                handleAliveCheckAlert(data.payload);
            }
        };

        aliveCheckSocket.onclose = function (e) {
            console.warn("Operations Alive Check: WebSocket closed. Retrying in 5 seconds...", e.code, e.reason);
            setTimeout(connectWebSocket, 5000);
        };

        aliveCheckSocket.onerror = function (err) {
            console.error("Operations Alive Check: WebSocket error:", err);
            aliveCheckSocket.close();
        };
    }

    function handleAliveCheckAlert(payload) {
        alertSound.play().catch((e) => console.warn("Could not play alert sound:", e));

        const alertItem = document.createElement("div");
        alertItem.className = "alert-item mb-2 rounded-lg border-l-4 border-red-500 bg-red-100 p-4 text-red-700 shadow-md animate-fade-in";
        alertItem.innerHTML = `
            <div class="flex items-center">
                <svg class="mr-2 h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                <p class="text-sm font-bold">${payload.message}</p>
            </div>
            <p class="ml-8 mt-1 text-xs">
                <span class="font-semibold">Nhân viên:</span> ${payload.nhan_vien || "N/A"} -
                <span class="font-semibold">Mục tiêu:</span> ${payload.muc_tieu || "N/A"} -
                <span class="font-semibold">Trạng thái:</span> <span class="font-bold">${payload.status || "N/A"}</span> -
                <span class="font-semibold">Thời gian:</span> ${payload.timestamp || "N/A"}
            </p>
        `;

        if (violationsList.firstChild) {
            violationsList.insertBefore(alertItem, violationsList.firstChild);
        } else {
            violationsList.appendChild(alertItem);
        }

        const currentCount = parseInt(violationsCountBadge.textContent, 10) || 0;
        violationsCountBadge.textContent = currentCount + 1;
        violationsCountBadge.classList.add("animate-ping-once");
        setTimeout(() => {
            violationsCountBadge.classList.remove("animate-ping-once");
        }, 1000);

        while (violationsList.children.length > 10) {
            violationsList.removeChild(violationsList.lastChild);
        }
    }

    connectWebSocket();
});
