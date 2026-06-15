/**
 * SCMD Pro - Operations Worker Health Monitor
 * Lang nghe trang thai ha tang Celery Workers tu WebSocket.
 */

(function () {
    const socketUrl = (window.location.protocol === "https:" ? "wss://" : "ws://")
        + window.location.host
        + "/ws/notifications/";

    let socket;
    let currentActiveWorkers = [];

    function connect() {
        socket = new WebSocket(socketUrl);

        socket.onmessage = function (e) {
            const data = JSON.parse(e.data);
            if (data.type === "worker_status") {
                updateWorkerUI(data.payload);
            }
        };

        socket.onclose = function () {
            console.warn("Worker status socket closed. Reconnecting in 5s...");
            setTimeout(connect, 5000);
        };

        socket.onerror = function (err) {
            console.error("Worker status socket error:", err);
            socket.close();
        };
    }

    function updateWorkerUI(payload) {
        const indicator = document.getElementById("worker-status-indicator");
        const statusText = document.getElementById("worker-status-text");
        const countInfo = document.getElementById("worker-count-info");
        const timeInfo = document.getElementById("worker-last-ping");

        currentActiveWorkers = payload.active_workers || [];

        if (indicator) {
            if (payload.active_count > 0) {
                indicator.className = "h-3 w-3 rounded-full bg-success animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.6)]";
            } else {
                indicator.className = "h-3 w-3 rounded-full bg-error shadow-[0_0_8px_rgba(239,68,68,0.6)]";
                indicator.classList.remove("animate-pulse");
            }
        }

        if (statusText) {
            statusText.innerText = payload.active_count > 0 ? "Worker đang online" : "Worker đang offline";
            statusText.className = payload.active_count > 0
                ? "text-[10px] font-black text-success tracking-tighter"
                : "text-[10px] font-black text-error tracking-tighter";
        }

        if (countInfo) {
            countInfo.innerText = `${payload.active_count}/${payload.total_count} worker`;
        }

        if (timeInfo) {
            timeInfo.innerText = payload.timestamp;
        }

        updateModalContent(payload);
    }

    function updateModalContent(payload) {
        const listContainer = document.getElementById("worker-list-container");
        const modalCount = document.getElementById("modal-worker-count");

        if (modalCount) {
            modalCount.innerText = `${payload.active_count} worker đang phản hồi`;
        }

        if (!listContainer) {
            return;
        }

        listContainer.innerHTML = currentActiveWorkers.length > 0
            ? currentActiveWorkers.map((hostname) => `
                <li class="group flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3 transition-colors hover:border-blue-300">
                    <div class="flex items-center gap-3">
                        <div class="h-2 w-2 rounded-full bg-success shadow-[0_0_5px_rgba(16,185,129,0.5)]"></div>
                        <span class="font-mono text-sm font-medium text-slate-700">${hostname}</span>
                    </div>
                    <span class="text-[9px] font-black tracking-tighter text-success opacity-70 group-hover:opacity-100">Đang hoạt động</span>
                </li>
            `).join("")
            : '<li class="py-8 text-center text-sm italic text-slate-400">Khong co worker nao phan hoi...</li>';
    }

    connect();
})();
