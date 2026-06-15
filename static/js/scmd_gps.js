/*
 * SCMD Pro - GPS & Live Map Module
 * File: static/js/scmd_gps.js
 * Updated: 2025-12-11 (Live Map Integrated)
 */

// --- MODULE 1: XỬ LÝ GPS (GIỮ NGUYÊN ĐỂ KHÔNG ERROR CODE CŨ) ---
const SCMD_GPS = {
    getCurrentPosition: function() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error("Trình duyệt không hỗ trợ định vị GPS."));
                return;
            }
            const options = {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            };
            const success = (pos) => {
                const crd = pos.coords;
                console.log(`[SCMD-GPS] Locked: ${crd.latitude}, ${crd.longitude}`);
                resolve({
                    lat: crd.latitude,
                    lng: crd.longitude,
                    accuracy: crd.accuracy
                });
            };
            const error = (err) => {
                let msg = "Lỗi định vị.";
                switch(err.code) {
                    case err.PERMISSION_DENIED: msg = "Bạn đã từ chối cấp quyền vị trí."; break;
                    case err.POSITION_UNAVAILABLE: msg = "Không thể xác định vị trí."; break;
                    case err.TIMEOUT: msg = "Hết thời gian chờ GPS."; break;
                }
                console.error(`[SCMD-GPS] Error: ${msg}`);
                reject(new Error(msg));
            };
            navigator.geolocation.getCurrentPosition(success, error, options);
        });
    },

    calculateDistance: function(lat1, lon1, lat2, lon2) {
        const R = 6371e3; // mét
        const φ1 = lat1 * Math.PI/180;
        const φ2 = lat2 * Math.PI/180;
        const Δφ = (lat2-lat1) * Math.PI/180;
        const Δλ = (lon2-lon1) * Math.PI/180;
        const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
                  Math.cos(φ1) * Math.cos(φ2) *
                  Math.sin(Δλ/2) * Math.sin(Δλ/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }
};

// --- MODULE 2: XỬ LÝ SOCKET & LIVE MAP (MỚI) ---
const SCMD_Socket = {
    socket: null,
    mapInstance: null, // Lưu instance của Leaflet map
    markers: {},       // Lưu danh sách marker để update thay vì vẽ đè

    /**
     * Khởi tạo kết nối Socket cho Dashboard
     * @param {Object} map - Leaflet Map Instance (L.map('id'))
     */
    init: function(map) {
        this.mapInstance = map;
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const wsUrl = protocol + window.location.host + '/ws/notifications/';
        
        console.log(`[SCMD-Socket] Connecting to ${wsUrl}...`);
        
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = function(e) {
            console.log("[SCMD-Socket] Connected! Ready for Live Updates.");
        };

        this.socket.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.handleMessage(data);
        };

        this.socket.onclose = function(e) {
            console.warn("[SCMD-Socket] Disconnected. Reconnecting in 5s...");
            setTimeout(() => SCMD_Socket.init(map), 5000); // Tự động kết nối lại
        };
    },

    handleMessage: function(data) {
        console.log("[SCMD-Live] Received:", data);

        // 1. Xử lý tin Check-in (Chấm công)
        if (data.type === 'CHECKIN') {
            this.updateWorkerMarker(data);
            this.showToast(data.message, 'success');
        } 
        // 2. Xử lý tin Incident (Sự cố)
        else if (data.type === 'INCIDENT') {
            this.addIncidentMarker(data);
            this.showToast(data.message, 'danger');
            this.playAlertSound();
        }
    },

    updateWorkerMarker: function(data) {
        if (!this.mapInstance || typeof L === 'undefined') return;

        // Nếu marker của nhân viên này đã có -> Update vị trí
        if (this.markers[data.user_name]) {
            const marker = this.markers[data.user_name];
            marker.setLatLng([data.lat, data.lng]);
            marker.bindPopup(this.getPopupContent(data)).openPopup();
        } else {
            // Chưa có -> Tạo mới
            const icon = L.icon({
                iconUrl: data.avatar || '/static/img/default-avatar.png',
                iconSize: [40, 40],
                className: 'rounded-circle border border-primary shadow-sm'
            });

            const newMarker = L.marker([data.lat, data.lng], {icon: icon})
                .addTo(this.mapInstance)
                .bindPopup(this.getPopupContent(data));
            
            this.markers[data.user_name] = newMarker;
        }
        
        // Hiệu ứng bay tới vị trí mới
        this.mapInstance.flyTo([data.lat, data.lng], 15);
    },

    addIncidentMarker: function(data) {
        if (!this.mapInstance || typeof L === 'undefined') return;

        const color = (data.level === 'NGUY_HIEM' || data.level === 'CAO') ? 'red' : 'orange';
        
        // Vẽ vòng tròn cảnh báo lan tỏa (nếu dùng CSS animation) hoặc CircleMarker
        L.circleMarker([data.lat, data.lng], {
            radius: 20,
            color: color,
            fillColor: color,
            fillOpacity: 0.6
        }).addTo(this.mapInstance)
          .bindPopup(`<b>⚠️ SỰ CỐ: ${data.title}</b><br>${data.timestamp}`)
          .openPopup();
          
        this.mapInstance.setView([data.lat, data.lng], 16);
    },

    getPopupContent: function(data) {
        return `
            <div class="text-center">
                <img src="${data.avatar}" class="rounded-circle mb-1" width="30">
                <br><b>${data.user_name}</b>
                <br><small class="text-muted">${data.timestamp}</small>
                <br><span class="badge bg-primary">${data.action}</span>
            </div>
        `;
    },

    showToast: function(msg, type) {
        // Tích hợp Toastify hoặc Alert đơn giản nếu chưa có lib
        if (typeof Toastify !== 'undefined') {
            Toastify({
                text: msg,
                duration: 5000,
                backgroundColor: type === 'danger' ? "#dc3545" : "#28a745",
            }).showToast();
        } else {
            console.log(`TOAST [${type}]: ${msg}`);
        }
    },

    playAlertSound: function() {
        // Tạo âm thanh cảnh báo ngắn
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioCtx.createOscillator();
            oscillator.type = 'square';
            oscillator.frequency.setValueAtTime(440, audioCtx.currentTime); // A4
            oscillator.connect(audioCtx.destination);
            oscillator.start();
            oscilla