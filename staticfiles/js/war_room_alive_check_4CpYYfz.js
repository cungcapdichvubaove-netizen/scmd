// -*- coding: utf-8 -*-
/**
 * SCMD ERP - War Room Dashboard: Real-time Alive Check Violations
 * File: static/js/war_room_alive_check.js
 * Description: Lắng nghe WebSocket để cập nhật danh sách vi phạm Alive Check.
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("War Room Alive Check: DOM Content Loaded.");

    // Lấy URL WebSocket từ cấu hình Django (nếu có) hoặc mặc định
    // Đảm bảo biến `websocket_url` được định nghĩa trong template HTML
    const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsHost = window.location.host;
    const wsPath = '/ws/notifications/'; // SSOT từ operations/routing.py
    const websocketUrl = wsProtocol + wsHost + wsPath;

    let aliveCheckSocket = null;
    const violationsList = document.getElementById('alive-check-violations-list');
    const violationsCountBadge = document.getElementById('alive-check-violations-count');
    const alertSound = new Audio('/static/sounds/alert.mp3'); // Giả định có file âm thanh cảnh báo

    if (!violationsList || !violationsCountBadge) {
        console.error("War Room Alive Check: Không tìm thấy các phần tử HTML cần thiết (violations-list/count).");
        return;
    }

    function connectWebSocket() {
        aliveCheckSocket = new WebSocket(websocketUrl);

        aliveCheckSocket.onopen = function(e) {
            console.log("War Room Alive Check: WebSocket connection established.");
        };

        aliveCheckSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            console.log("War Room Alive Check: Received message:", data);

            if (data.type === 'ALIVE_CHECK_ALERT' || data.type === 'ALIVE_CHECK_EXPIRED') {
                handleAliveCheckAlert(data.payload);
            }
        };

        aliveCheckSocket.onclose = function(e) {
            console.warn('War Room Alive Check: WebSocket connection closed. Retrying in 5 seconds...', e.code, e.reason);
            setTimeout(connectWebSocket, 5000); // Tự động kết nối lại sau 5 giây
        };

        aliveCheckSocket.onerror = function(err) {
            console.error('War Room Alive Check: WebSocket error:', err);
            aliveCheckSocket.close(); // Đóng kết nối để kích hoạt onclose và retry
        };
    }

    function handleAliveCheckAlert(payload) {
        // Phát âm thanh cảnh báo (nếu có)
        if (alertSound) {
            alertSound.play().catch(e => console.warn("Could not play alert sound:", e));
        }

        // Tạo phần tử HTML mới cho cảnh báo
        const alertItem = document.createElement('div');
        alertItem.className = 'alert-item bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-2 shadow-md rounded-lg animate-fade-in';
        alertItem.innerHTML = `
            <div class="flex items-center">
                <svg class="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                <p class="font-bold text-sm">${payload.message}</p>
            </div>
            <p class="text-xs mt-1 ml-8">
                <span class="font-semibold">Nhân viên:</span> ${payload.nhan_vien || 'N/A'} - 
                <span class="font-semibold">Mục tiêu:</span> ${payload.muc_tieu || 'N/A'} - 
                <span class="font-semibold">Trạng thái:</span> <span class="font-bold">${payload.status || 'N/A'}</span> - 
                <span class="font-semibold">Thời gian:</span> ${payload.timestamp || 'N/A'}
            </p>
        `;

        // Thêm vào đầu danh sách
        if (violationsList.firstChild) {
            violationsList.insertBefore(alertItem, violationsList.firstChild);
        } else {
            violationsList.appendChild(alertItem);
        }

        // Cập nhật số lượng cảnh báo
        let currentCount = parseInt(violationsCountBadge.textContent) || 0;
        violationsCountBadge.textContent = currentCount + 1;
        violationsCountBadge.classList.add('animate-ping-once'); // Hiệu ứng nhỏ để thu hút sự chú ý
        setTimeout(() => {
            violationsCountBadge.classList.remove('animate-ping-once');
        }, 1000);

        // Giới hạn số lượng hiển thị để tránh quá tải DOM
        while (violationsList.children.length > 10) {
            violationsList.removeChild(violationsList.lastChild);
        }
    }

    // Bắt đầu kết nối WebSocket
    connectWebSocket();
});