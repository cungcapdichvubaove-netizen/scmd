/*
 * Security Command (SCMD) System
 * File: static/js/scmd_socket.js
 * Description: WebSocket Manager (Updated Phase 7.1).
 * - Hiển thị Toast Notification.
 * - Dispatch Event 'SCMD_REALTIME_EVENT' để Map cập nhật Marker.
 */

class SCMDWebSocket {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        this.connect();
    }

    connect() {
        const url = this.protocol + window.location.host + '/ws/notifications/';
        console.log(`[Socket] Connecting to ${url}...`);

        try {
            this.socket = new WebSocket(url);

            this.socket.onopen = () => {
                console.log("[Socket] Connected ✅");
                this.reconnectAttempts = 0;
                this.showToast("Hệ thống Online", "Kết nối máy chủ thành công.", "success");
            };

            this.socket.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    this.handleMessage(data);
                } catch (err) { 
                    console.error("[Socket] Parse Error:", err); 
                }
            };

            this.socket.onclose = (e) => {
                console.warn("[Socket] Connection closed. Code:", e.code);
                this.scheduleReconnect();
            };

            this.socket.onerror = (err) => {
                console.error("[Socket] WebSocket Error:", err);
            };

        } catch (error) {
            console.error("[Socket] Connection failed:", error);
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            const delay = 1000 * Math.pow(2, this.reconnectAttempts);
            console.log(`[Socket] Reconnecting in ${delay/1000}s...`);
            setTimeout(() => {
                this.reconnectAttempts++;
                this.connect();
            }, delay);
        } else {
            console.error("[Socket] Max reconnect attempts reached.");
        }
    }

    handleMessage(packet) {
        if (packet.type === 'notification') {
            const payload = packet.payload;
            
            // 1. Hiển thị Popup (Toast)
            this.showToast(payload.title, payload.message, payload.status || 'info');
            
            // 2. Bắn sự kiện để Map (Leaflet) bắt được
            const event = new CustomEvent('SCMD_REALTIME_EVENT', { detail: payload });
            document.dispatchEvent(event);
        }
    }

    showToast(title, message, type = 'info') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }

        const bgClass = (type === 'danger' || type === 'NGUY_HIEM' || type === 'CAO') ? 'bg-danger text-white' : 
                        (type === 'success') ? 'bg-success text-white' : 
                        (type === 'warning') ? 'bg-warning text-dark' : 'bg-white text-dark';

        const toastId = 'toast_' + Date.now();
        const html = `
            <div id="${toastId}" class="toast show align-items-center ${bgClass} border-0 mb-2" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <strong>${title}</strong><br>${message}
                    </div>
                    <button type="button" class="btn-close ${bgClass.includes('white') ? '' : 'btn-close-white'} me-2 m-auto" data-bs-dismiss="toast" onclick="this.parentElement.parentElement.remove()"></button>
                </div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', html);
        
        // Tự động ẩn sau 5s
        setTimeout(() => {
            const toastElement = document.getElementById(toastId);
            if (toastElement) {
                toastElement.classList.remove('show');
                setTimeout(() => toastElement.remove(), 500);
            }
        }, 5000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.scmdSocket = new SCMDWebSocket();
});