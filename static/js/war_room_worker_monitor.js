/**
 * SCMD War Room - Worker Health Monitor
 * Lắng nghe trạng thái hạ tầng Celery Workers từ WebSocket.
 * Tuân thủ triết lý Operational Visibility.
 */

(function() {
    const socketUrl = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') 
                    + window.location.host 
                    + '/ws/notifications/';

    let socket;
    let currentActiveWorkers = [];

    function connect() {
        socket = new WebSocket(socketUrl);

        socket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            
            // Lắng nghe type 'worker_status' từ consumers.py
            if (data.type === 'worker_status') {
                updateWorkerUI(data.payload);
            }
        };

        socket.onclose = function(e) {
            console.warn('Worker Status Socket closed. Reconnecting in 5s...');
            setTimeout(connect, 5000);
        };

        socket.onerror = function(err) {
            console.error('Worker Status Socket error:', err);
            socket.close();
        };
    }

    /**
     * Cập nhật các thành phần UI dựa trên dữ liệu Heartbeat
     * Payload: { active_workers, active_count, total_count, timestamp }
     */
    function updateWorkerUI(payload) {
        const indicator = document.getElementById('worker-status-indicator');
        const statusText = document.getElementById('worker-status-text');
        const countInfo = document.getElementById('worker-count-info');
        const timeInfo = document.getElementById('worker-last-ping');

        // Cập nhật dữ liệu nội bộ
        currentActiveWorkers = payload.active_workers || [];

        if (indicator) {
            // Cập nhật đèn trạng thái
            if (payload.active_count > 0) {
                indicator.className = 'w-3 h-3 rounded-full bg-success animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.6)]';
            } else {
                indicator.className = 'w-3 h-3 rounded-full bg-error shadow-[0_0_8px_rgba(239,68,68,0.6)]';
                indicator.classList.remove('animate-pulse');
            }
        }

        if (statusText) {
            statusText.innerText = payload.active_count > 0 ? 'WORKERS ONLINE' : 'WORKERS OFFLINE';
            statusText.className = payload.active_count > 0 ? 'text-[10px] font-black text-success tracking-tighter' : 'text-[10px] font-black text-error tracking-tighter';
        }

        if (countInfo) {
            // Hiển thị số lượng worker đang hoạt động trên tổng số worker từng ghi nhận
            countInfo.innerText = `${payload.active_count}/${payload.total_count} nodes`;
        }

        if (timeInfo) {
            // Hiển thị thời điểm cập nhật cuối cùng (HH:MM:SS)
            timeInfo.innerText = payload.timestamp;
        }

        // Cập nhật danh sách trong Modal nếu Modal đang hiển thị
        updateModalContent(payload);

        // Log nhẹ để debug trong môi trường staging
        // console.debug(`[Worker-Health] Active nodes: ${payload.active_workers.join(', ')}`);
    }

    /**
     * Render danh sách Hostname vào Modal
     */
    function updateModalContent(payload) {
        const listContainer = document.getElementById('worker-list-container');
        const modalCount = document.getElementById('modal-worker-count');
        
        if (modalCount) modalCount.innerText = `${payload.active_count} nodes online`;
        if (!listContainer) return;

        listContainer.innerHTML = currentActiveWorkers.length > 0 
            ? currentActiveWorkers.map(hostname => `
                <li class="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200 group hover:border-indigo-300 transition-colors">
                    <div class="flex items-center gap-3">
                        <div class="w-2 h-2 rounded-full bg-success shadow-[0_0_5px_rgba(16,185,129,0.5)]"></div>
                        <span class="font-mono text-sm text-slate-700 font-medium">${hostname}</span>
                    </div>
                    <span class="text-[9px] font-black text-success uppercase tracking-tighter opacity-70 group-hover:opacity-100">Active</span>
                </li>
            `).join('')
            : '<li class="text-slate-400 italic py-8 text-center text-sm">Không có worker nào phản hồi...</li>';
    }

    // Khởi tạo kết nối khi load trang
    connect();
})();