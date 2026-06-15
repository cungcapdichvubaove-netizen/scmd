(function () {
    const root = document.querySelector("[data-ops-dashboard]");
    if (!root) {
        return;
    }

    const apiUrl = root.dataset.apiUrl;
    const variant = root.dataset.variant || "desk";
    const tileUrl = root.dataset.tileUrl || "";
    const tileAttribution = root.dataset.tileAttribution || "";
    const incidentReportsUrl = root.dataset.incidentReportsUrl || "";
    const attendanceReportUrl = root.dataset.attendanceReportUrl || "";
    const incidentAdminBaseUrl = root.dataset.incidentAdminBaseUrl || "";
    const mapEl = root.querySelector("[data-ops-map]");
    if (!apiUrl || !mapEl) {
        return;
    }

    if (typeof L === "undefined") {
        setDashboardMessage(
            "danger",
            "Lỗi bản đồ",
            "Không tải được thư viện bản đồ. Dữ liệu vận hành vẫn có thể tải lại sau khi kiểm tra static hoặc kết nối mạng."
        );
        mapEl.setAttribute("data-map-error", "leaflet-missing");
        return;
    }

    const map = L.map(mapEl, {
        zoomControl: false,
        preferCanvas: true,
        zoomAnimation: false,
        fadeAnimation: false,
        markerZoomAnimation: false,
        inertia: false,
    }).setView([10.7769, 106.7009], 12);
    L.control.zoom({ position: variant === "display" ? "bottomleft" : "bottomright" }).addTo(map);

    if (tileUrl) {
        L.tileLayer(tileUrl, {
            attribution: tileAttribution,
        })
            .on("tileerror", function () {
                setDashboardMessage(
                    "warning",
                    "Lỗi nền bản đồ",
                    "Không tải được nền bản đồ. Dữ liệu vị trí vẫn được giữ nếu tọa độ hợp lệ."
                );
            })
            .addTo(map);
    } else {
        setDashboardMessage(
            "warning",
            "Thiếu cấu hình bản đồ",
            "Chưa cấu hình nguồn tile bản đồ. Hãy kiểm tra SCMD_MAP_TILE_URL trong settings/env."
        );
    }

    const guardLayer = L.layerGroup().addTo(map);
    const incidentLayer = L.layerGroup().addTo(map);
    const effectLayer = L.layerGroup().addTo(map);

    const knownGuardEvents = new Set();
    const knownIncidentIds = new Set();
    const filterState = {
        guards: true,
        incidents: true,
        critical: false,
    };
    const markerRegistry = {
        guards: new Map(),
        incidents: new Map(),
    };
    const normalizedVariant = variant === "display" ? "display" : "desk";
    const legacyWidgetStorageKey = "scmd-ops-display-layout-v1";
    const widgetStorageKey = `scmd-ops-layout-${normalizedVariant}-v1`;
    const widgets = new Map();

    let selectedState = null;
    let isFirstLoad = true;
    let isFetching = false;
    let pollingIntervalId = null;
    let refreshButton = null;
    let invalidateMapTimerId = null;

    function safeInvalidateMap(delay) {
        if (!map || typeof map.invalidateSize !== "function") {
            return;
        }

        if (invalidateMapTimerId) {
            window.clearTimeout(invalidateMapTimerId);
        }

        invalidateMapTimerId = window.setTimeout(function () {
            invalidateMapTimerId = null;
            map.invalidateSize(false);
        }, typeof delay === "number" ? delay : 0);
    }

    function el(id) {
        return document.getElementById(id);
    }

    function setDashboardMessage(tone, label, copy) {
        const toneEl = el("ops-status-tone");
        const copyEl = el("ops-status-copy");
        if (toneEl) {
            toneEl.className = toneClass(tone);
            toneEl.textContent = label;
        }
        if (copyEl) {
            copyEl.textContent = copy;
        }
    }

    function isValidLatLng(lat, lng) {
        const numericLat = Number(lat);
        const numericLng = Number(lng);
        return Number.isFinite(numericLat)
            && Number.isFinite(numericLng)
            && numericLat >= -90
            && numericLat <= 90
            && numericLng >= -180
            && numericLng <= 180;
    }

    function normalizeLatLng(item) {
        if (!item || !isValidLatLng(item.lat, item.lng)) {
            return null;
        }
        return [Number(item.lat), Number(item.lng)];
    }

    function apiErrorMessage(error) {
        if (error && error.status === 403) {
            return "Bạn không có quyền xem dữ liệu vận hành.";
        }
        if (error && error.status >= 500) {
            return "Không thể tải dữ liệu vận hành do lỗi hệ thống. Vui lòng kiểm tra log máy chủ.";
        }
        if (error && error.status) {
            return `Không thể tải dữ liệu vận hành. Mã lỗi HTTP ${error.status}.`;
        }
        return "Không thể tải dữ liệu vận hành. Vui lòng kiểm tra kết nối hoặc quyền truy cập API.";
    }

    function parseErrorPayload(response) {
        return response.json()
            .catch(() => ({}))
            .then((payload) => {
                const error = new Error(payload.message || payload.error || apiErrorMessage({ status: response.status }));
                error.status = response.status;
                error.payload = payload;
                throw error;
            });
    }

    function safeParseJson(value, fallback) {
        try {
            return JSON.parse(value);
        } catch (_) {
            return fallback;
        }
    }

    function readWidgetState(key) {
        try {
            const parsed = safeParseJson(window.localStorage.getItem(key), {});
            if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
                return {};
            }
            return parsed;
        } catch (_) {
            return {};
        }
    }

    function hasWidgetSnapshot(state) {
        return state && typeof state === "object" && Object.keys(state).length > 0;
    }

    function loadWidgetState() {
        const currentState = readWidgetState(widgetStorageKey);
        if (hasWidgetSnapshot(currentState)) {
            return currentState;
        }

        if (widgetStorageKey === legacyWidgetStorageKey) {
            return currentState;
        }

        const legacyState = readWidgetState(legacyWidgetStorageKey);
        if (hasWidgetSnapshot(legacyState)) {
            try {
                window.localStorage.setItem(widgetStorageKey, JSON.stringify(legacyState));
            } catch (_) {
                // Keep dashboard usable when storage is unavailable or full.
            }
            return legacyState;
        }

        return currentState;
    }

    function persistWidgetState() {
        const payload = {};
        widgets.forEach((widget, name) => {
            payload[name] = {
                x: widget.x || 0,
                y: widget.y || 0,
                hidden: Boolean(widget.hidden),
                collapsed: Boolean(widget.collapsed),
            };
        });
        try {
            window.localStorage.setItem(widgetStorageKey, JSON.stringify(payload));
        } catch (_) {
            return;
        }
    }

    function applyWidgetTransform(widget) {
        widget.node.style.transform = `translate3d(${widget.x || 0}px, ${widget.y || 0}px, 0)`;
    }

    function setWidgetHidden(name, hidden) {
        const widget = widgets.get(name);
        if (!widget) {
            return;
        }
        widget.hidden = hidden;
        widget.node.classList.toggle("is-hidden", hidden);
        const toggle = root.querySelector(`[data-widget-toggle="${name}"]`);
        if (toggle) {
            toggle.classList.toggle("is-on", !hidden);
        }
        persistWidgetState();
    }

    function setWidgetCollapsed(name, collapsed) {
        const widget = widgets.get(name);
        if (!widget) {
            return;
        }
        widget.collapsed = collapsed;
        widget.node.setAttribute("data-widget-collapsed", collapsed ? "true" : "false");
        const button = root.querySelector(`[data-widget-collapse="${name}"]`);
        if (button) {
            button.textContent = collapsed ? "+" : "−";
        }
        persistWidgetState();
    }

    function initializeWidgets() {
        const savedState = loadWidgetState();
        root.querySelectorAll("[data-widget]").forEach((node) => {
            const name = node.getAttribute("data-widget");
            const snapshot = savedState[name] || {};
            const widget = {
                node,
                name,
                x: Number(snapshot.x) || 0,
                y: Number(snapshot.y) || 0,
                hidden: Boolean(snapshot.hidden),
                collapsed: Boolean(snapshot.collapsed),
            };
            widgets.set(name, widget);
            applyWidgetTransform(widget);
            setWidgetHidden(name, widget.hidden);
            setWidgetCollapsed(name, widget.collapsed);

            const handle = node.querySelector("[data-widget-handle]");
            if (handle) {
                handle.addEventListener("mousedown", function (event) {
                    if (window.matchMedia("(max-width: 1320px)").matches) {
                        return;
                    }
                    event.preventDefault();
                    const startX = event.clientX;
                    const startY = event.clientY;
                    const originX = widget.x || 0;
                    const originY = widget.y || 0;
                    node.setAttribute("data-widget-dragging", "true");

                    function onMove(moveEvent) {
                        widget.x = originX + (moveEvent.clientX - startX);
                        widget.y = originY + (moveEvent.clientY - startY);
                        applyWidgetTransform(widget);
                    }

                    function onUp() {
                        node.setAttribute("data-widget-dragging", "false");
                        document.removeEventListener("mousemove", onMove);
                        document.removeEventListener("mouseup", onUp);
                        persistWidgetState();
                    }

                    document.addEventListener("mousemove", onMove);
                    document.addEventListener("mouseup", onUp);
                });
            }
        });

        root.querySelectorAll("[data-widget-toggle]").forEach((button) => {
            button.addEventListener("click", function () {
                const name = button.getAttribute("data-widget-toggle");
                const widget = widgets.get(name);
                if (!widget) {
                    return;
                }
                setWidgetHidden(name, !widget.hidden);
            });
        });

        root.querySelectorAll("[data-widget-collapse]").forEach((button) => {
            button.addEventListener("click", function () {
                const name = button.getAttribute("data-widget-collapse");
                const widget = widgets.get(name);
                if (!widget) {
                    return;
                }
                setWidgetCollapsed(name, !widget.collapsed);
            });
        });

        root.querySelectorAll("[data-widget-hide]").forEach((button) => {
            button.addEventListener("click", function () {
                const name = button.getAttribute("data-widget-hide");
                setWidgetHidden(name, true);
            });
        });
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function toneClass(tone) {
        const mapTone = {
            success: "scmd-tone scmd-tone--success",
            warning: "scmd-tone scmd-tone--warning",
            danger: "scmd-tone scmd-tone--danger",
            info: "scmd-tone scmd-tone--info",
            neutral: "scmd-tone scmd-tone--neutral",
        };
        return mapTone[tone] || mapTone.neutral;
    }

    function incidentTone(level) {
        if (level === "CAO" || level === "NGUY_HIEM") {
            return "danger";
        }
        if (level === "TB") {
            return "warning";
        }
        return "info";
    }

    function incidentLabel(level) {
        const labels = {
            THAP: "Thấp",
            TB: "Trung bình",
            CAO: "Cao",
            NGUY_HIEM: "Nguy hiểm",
        };
        return labels[level] || level || "Sự cố";
    }

    function computeStatus(stats, incidents) {
        if ((stats.su_co_nghiem_trong || 0) > 0) {
            return {
                tone: "danger",
                label: "Cảnh báo cao",
                copy: `${stats.su_co_nghiem_trong} sự cố nghiêm trọng đang mở. Ưu tiên khoanh vùng, điều phối và xử lý hiện trường.`,
            };
        }
        if ((incidents || []).length > 0 || (stats.vang_mat || 0) > 0) {
            return {
                tone: "warning",
                label: "Cần theo dõi",
                copy: `${incidents.length} sự cố mở và ${stats.vang_mat || 0} ca chưa check-in. Cần bám sát quân số và nhịp xử lý trong ngày.`,
            };
        }
        if ((stats.tong_ca || 0) > 0) {
            return {
                tone: "success",
                label: "Ổn định",
                copy: `Quân số đang phủ ${stats.ti_le_phu_ca || 0}% số ca phát sinh và chưa có hồ sơ sự cố mở cần escalations.`,
            };
        }
        return {
            tone: "neutral",
            label: "Chưa đủ dữ liệu",
            copy: "Chưa phát sinh đủ ca trực hoặc dữ liệu chấm công để tổng hợp toàn cảnh hiện trường.",
        };
    }

    function createPopupContent(item, kind) {
        if (kind === "guard") {
            return [
                `<div style="min-width:240px;">`,
                `<div style="font-size:15px;font-weight:800;color:#f8fafc;">${escapeHtml(item.name)}</div>`,
                `<div style="margin-top:6px;font-size:12px;color:#cbd5e1;">${escapeHtml(item.employee_code || "Nhân sự")}</div>`,
                `<div style="margin-top:8px;font-size:13px;color:#e2e8f0;">${escapeHtml(item.target || "Mục tiêu chưa xác định")}</div>`,
                `<div style="margin-top:4px;font-size:12px;color:#cbd5e1;">${escapeHtml(item.post_name || "Chốt chưa xác định")} • ${escapeHtml(item.shift_name || "Ca trực")}</div>`,
                `<div style="margin-top:4px;font-size:12px;color:#93c5fd;">Check-in: ${escapeHtml(item.check_in_time || "--:--")}</div>`,
                item.phone ? `<div style="margin-top:8px;font-size:12px;color:#e2e8f0;">Liên hệ: ${escapeHtml(item.phone)}</div>` : "",
                `</div>`,
            ].join("");
        }

        return [
            `<div style="min-width:260px;">`,
            `<div style="font-size:15px;font-weight:800;color:#f8fafc;">${escapeHtml(item.title)}</div>`,
            `<div style="margin-top:6px;font-size:12px;color:#fca5a5;">${escapeHtml(item.code || "Sự cố")} • ${escapeHtml(item.level_label || incidentLabel(item.level))}</div>`,
            `<div style="margin-top:8px;font-size:13px;color:#e2e8f0;">${escapeHtml(item.muc_tieu || "Mục tiêu")}</div>`,
            `<div style="margin-top:4px;font-size:12px;color:#cbd5e1;">${escapeHtml(item.thoi_gian || "--:--")} • ${escapeHtml(item.status_label || item.status || "Đang xử lý")}</div>`,
            item.mo_ta_ngan ? `<div style="margin-top:8px;font-size:12px;line-height:1.5;color:#cbd5e1;">${escapeHtml(item.mo_ta_ngan)}</div>` : "",
            `</div>`,
        ].join("");
    }

    function createGuardIcon(guard) {
        const initial = (guard.name || "?").trim().charAt(0).toUpperCase() || "?";
        return L.divIcon({
            className: "custom-icon",
            html: `<div class="ops-marker ops-marker--guard"><img src="${escapeHtml(guard.avatar || "")}" alt="${escapeHtml(guard.name || "")}" onerror="this.remove(); this.parentNode.textContent='${escapeHtml(initial)}';"></div>`,
            iconSize: [46, 46],
            iconAnchor: [23, 42],
            popupAnchor: [0, -30],
        });
    }

    function createIncidentIcon(incident) {
        const criticalClass = incident.level === "CAO" || incident.level === "NGUY_HIEM" ? " ops-marker--critical" : "";
        return L.divIcon({
            className: "custom-icon",
            html: `<div class="ops-marker ops-marker--incident${criticalClass}">!</div>`,
            iconSize: [46, 46],
            iconAnchor: [23, 23],
            popupAnchor: [0, -18],
        });
    }

    function flashEvent(kind) {
        const flash = el("ops-event-flash");
        if (!flash) {
            return;
        }
        flash.style.background = kind === "incident"
            ? "radial-gradient(circle at center, rgba(248, 113, 113, 0.20), transparent 42%)"
            : "radial-gradient(circle at center, rgba(96, 165, 250, 0.18), transparent 42%)";
        flash.classList.add("is-visible");
        window.setTimeout(() => flash.classList.remove("is-visible"), 720);
    }

    function showRipple(lat, lng, kind) {
        const ripple = L.marker([lat, lng], {
            interactive: false,
            icon: L.divIcon({
                className: "custom-icon",
                html: `<div class="ops-marker-ripple${kind === "incident" ? " ops-marker-ripple--incident" : ""}"></div>`,
                iconSize: [84, 84],
                iconAnchor: [42, 42],
            }),
        }).addTo(effectLayer);

        window.setTimeout(() => {
            effectLayer.removeLayer(ripple);
        }, 1700);
    }

    function updateStats(stats) {
        if (!stats) {
            return;
        }
        if (el("stat-total")) el("stat-total").textContent = stats.tong_ca || 0;
        if (el("stat-online")) el("stat-online").textContent = stats.da_checkin || 0;
        if (el("stat-missing")) el("stat-missing").textContent = stats.vang_mat || 0;
        if (el("stat-rate")) el("stat-rate").textContent = `${stats.ti_le_phu_ca || 0}%`;
        if (el("stat-incident")) el("stat-incident").textContent = stats.tong_su_co || 0;
        if (el("stat-target")) el("stat-target").textContent = stats.tong_muc_tieu || 0;
        if (el("stat-severe")) el("stat-severe").textContent = stats.su_co_nghiem_trong || 0;
    }

    function updateStatus(stats, incidents, lastActivity, recentActivity) {
        const state = computeStatus(stats, incidents);
        const latestActionableActivity = Array.isArray(recentActivity) && recentActivity.length > 0
            ? recentActivity[0]
            : lastActivity;
        if (el("ops-status-tone")) {
            el("ops-status-tone").className = `${toneClass(state.tone)} ops-mini-badge`;
            el("ops-status-tone").textContent = state.label;
        }
        if (el("ops-status-copy")) {
            el("ops-status-copy").textContent = state.copy;
        }
        if (el("incident-count")) {
            el("incident-count").textContent = `${(incidents || []).length} hồ sơ`;
        }
        if (el("last-activity")) {
            if (lastActivity) {
                el("last-activity").textContent = `${activityLabel(lastActivity)} • ${lastActivity.time || "--:--"} • ${lastActivity.user || "Chưa xác định"}`;
            } else {
                el("last-activity").textContent = "Chưa có cập nhật";
            }
        }
        if (el("last-activity-actions")) {
            el("last-activity-actions").innerHTML = latestActionableActivity
                ? buildActivityActions(latestActionableActivity)
                : "";
            bindActivityFocusActions(el("last-activity-actions"));
        }
        if (el("ops-event-summary")) {
            el("ops-event-summary").textContent = lastActivity
                ? lastActivity.summary || `${lastActivity.user} tại ${lastActivity.target || "hiện trường"}.`
                : "Hệ thống sẽ ưu tiên tiêu điểm vào sự cố hoặc check-in mới nhất.";
        }
    }

    function selectEntity(kind, item, options) {
        selectedState = {
            kind,
            id: item.id,
        };

        if (kind === "guard") {
            if (el("selected-title")) el("selected-title").textContent = item.name || "Nhân viên online";
            if (el("selected-copy")) {
                const shiftInfo = [item.shift_name, item.shift_window].filter(Boolean).join(" • ");
                el("selected-copy").textContent = shiftInfo
                    ? `${item.target || "Mục tiêu"} • ${item.post_name || "Chốt"} • ${shiftInfo}`
                    : `${item.target || "Mục tiêu"} • ${item.post_name || "Chốt"}`;
            }
            if (el("selected-kind")) el("selected-kind").textContent = "Nhân viên online";
            if (el("selected-status")) el("selected-status").textContent = `Check-in ${item.check_in_time || "--:--"}`;
            if (el("selected-target")) el("selected-target").textContent = item.target || "Chưa xác định";
            if (el("selected-contact")) {
                const contacts = [item.phone, item.target_contact_phone].filter(Boolean);
                el("selected-contact").textContent = contacts.length > 0 ? contacts.join(" • ") : "Chưa có số liên hệ";
            }
        } else {
            if (el("selected-title")) el("selected-title").textContent = item.title || "Sự cố hiện trường";
            if (el("selected-copy")) {
                const handler = item.nguoi_xu_ly ? `Người xử lý: ${item.nguoi_xu_ly}. ` : "";
                el("selected-copy").textContent = `${handler}${item.mo_ta_ngan || "Chưa có mô tả chi tiết."}`;
            }
            if (el("selected-kind")) el("selected-kind").textContent = item.level_label || incidentLabel(item.level);
            if (el("selected-status")) el("selected-status").textContent = item.status_label || item.status || "Đang xử lý";
            if (el("selected-target")) el("selected-target").textContent = item.muc_tieu || "Chưa xác định";
            if (el("selected-contact")) {
                const contacts = [item.nguoi_bao_cao, item.so_dien_thoai].filter(Boolean);
                el("selected-contact").textContent = contacts.length > 0 ? contacts.join(" • ") : "Chưa có người báo cáo";
            }
        }

        if (!options || options.focusMap !== false) {
            const coords = normalizeLatLng(item);
            if (coords) {
                map.flyTo(coords, kind === "incident" ? 17 : 16, { duration: 1.6 });
            }
        }

        const registry = kind === "guard" ? markerRegistry.guards : markerRegistry.incidents;
        const marker = registry.get(item.id);
        if (marker) {
            marker.openPopup();
        }

        root.querySelectorAll("[data-guard-id], [data-incident-id]").forEach((node) => {
            const nodeKind = node.hasAttribute("data-guard-id") ? "guard" : "incident";
            const nodeId = Number(node.getAttribute(nodeKind === "guard" ? "data-guard-id" : "data-incident-id"));
            node.classList.toggle("is-active", nodeKind === kind && nodeId === item.id);
        });
    }

    function buildIncidentReportUrl(incident) {
        if (!incidentReportsUrl) {
            return "";
        }
        const keyword = incident.code || incident.title || incident.id || "";
        if (!keyword) {
            return incidentReportsUrl;
        }
        try {
            const url = new URL(incidentReportsUrl, window.location.origin);
            url.searchParams.set("q", keyword);
            return `${url.pathname}${url.search}${url.hash}`;
        } catch (error) {
            const joiner = incidentReportsUrl.indexOf("?") === -1 ? "?" : "&";
            return `${incidentReportsUrl}${joiner}q=${encodeURIComponent(keyword)}`;
        }
    }

    function buildIncidentAdminChangeUrl(incident) {
        if (!incidentAdminBaseUrl || !incident || !incident.id) {
            return "";
        }
        const base = incidentAdminBaseUrl.endsWith("/") ? incidentAdminBaseUrl : `${incidentAdminBaseUrl}/`;
        return `${base}${encodeURIComponent(incident.id)}/change/`;
    }

    function buildActivityViewUrl(item) {
        if (!item) {
            return "";
        }
        if (item.kind === "incident") {
            return buildIncidentReportUrl({
                code: item.incident_code,
                title: item.summary,
                id: item.incident_id,
            });
        }
        return attendanceReportUrl || "";
    }

    function activityLabel(item) {
        if (!item) {
            return "Hoạt động";
        }
        return item.label || (item.kind === "incident" ? "Sự cố mới" : "Check-in mới");
    }

    function activitySummary(item) {
        if (!item) {
            return "Hiện trường";
        }
        return item.summary || item.target || "Hiện trường";
    }

    function focusCoordinates(lat, lng, kind, entityId) {
        if (!isValidLatLng(lat, lng)) {
            return;
        }
        const numericLat = Number(lat);
        const numericLng = Number(lng);
        map.flyTo([numericLat, numericLng], kind === "incident" ? 17 : 16, { duration: 1.5 });
        if (kind === "incident" && entityId) {
            const marker = markerRegistry.incidents.get(Number(entityId));
            if (marker) {
                marker.openPopup();
            }
        }
    }

    function buildActivityActions(item) {
        if (!item) {
            return "";
        }
        const viewUrl = buildActivityViewUrl(item);
        const viewAction = viewUrl
            ? `<a class="ops-incident-action" href="${escapeHtml(viewUrl)}" aria-label="Xem ${escapeHtml(activityLabel(item))}">Xem</a>`
            : "";
        const coords = normalizeLatLng(item);
        const focusAction = coords
            ? `<button type="button" class="ops-incident-action" data-focus-activity="true" data-activity-kind="${escapeHtml(item.kind || "activity")}" data-activity-entity-id="${escapeHtml(item.incident_id || item.id || "")}" data-activity-lat="${escapeHtml(coords[0])}" data-activity-lng="${escapeHtml(coords[1])}">Định vị</button>`
            : "";
        return `${viewAction}${focusAction}`;
    }

    function bindActivityFocusActions(scope) {
        const container = scope || document;
        container.querySelectorAll("[data-focus-activity='true']").forEach((node) => {
            node.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                focusCoordinates(
                    node.getAttribute("data-activity-lat"),
                    node.getAttribute("data-activity-lng"),
                    node.getAttribute("data-activity-kind"),
                    node.getAttribute("data-activity-entity-id")
                );
            });
        });
    }

    function incidentMetaLine(incident) {
        return [
            incident.code || "Sự cố",
            incident.muc_tieu || "Mục tiêu chưa xác định",
            incident.nguoi_bao_cao || incident.nguoi_xu_ly || "Chưa rõ phụ trách",
        ].filter(Boolean).join(" · ");
    }

    function incidentHandlerLine(incident) {
        const handler = incident.nguoi_xu_ly || incident.nguoi_bao_cao || "Chưa rõ";
        const status = incident.status_label || incident.status || "Đang xử lý";
        return `${handler} · ${status}`;
    }

    function updateIncidents(incidents) {
        const list = el("incident-list");
        if (!list) {
            return;
        }

        const renderedIncidents = (incidents || []).filter((incident) => {
            if (!filterState.incidents) {
                return false;
            }
            if (!filterState.critical) {
                return true;
            }
            return incident.level === "CAO" || incident.level === "NGUY_HIEM";
        });

        if (renderedIncidents.length === 0) {
            list.innerHTML = variant === "display"
                ? "<div class='wall-item' style='cursor:default;'>Không có sự cố phù hợp bộ lọc hiện tại.</div>"
                : "<div class='ops-incident-empty'>Không có sự cố phù hợp bộ lọc hiện tại.</div>";
            return;
        }

        list.innerHTML = renderedIncidents.map((incident) => {
            if (variant === "display") {
                return `
                    <button type="button" class="wall-item" data-incident-id="${incident.id}">
                        <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
                            <span class="${toneClass(incidentTone(incident.level))}">${escapeHtml(incident.level_label || incidentLabel(incident.level))}</span>
                            <span style="font-size:11px;font-weight:800;color:#94a3b8;">${escapeHtml(incident.thoi_gian || "--:--")}</span>
                        </div>
                        <div class="wall-item__title">${escapeHtml(incident.title)}</div>
                        <div class="wall-item__meta">${escapeHtml(incident.code || "Sự cố")} • ${escapeHtml(incident.muc_tieu || "Mục tiêu chưa xác định")}</div>
                        <div class="wall-item__sub">${escapeHtml(incident.nguoi_bao_cao || "Chưa rõ")} • ${escapeHtml(incident.status_label || incident.status || "Đang xử lý")}</div>
                    </button>
                `;
            }

            const reportUrl = buildIncidentReportUrl(incident);
            const adminChangeUrl = buildIncidentAdminChangeUrl(incident);
            const coords = normalizeLatLng(incident);
            const focusAction = coords
                ? `<button type="button" class="ops-incident-action" data-focus-map="incident" data-incident-focus-id="${incident.id}">Định vị</button>`
                : "";
            const viewAction = reportUrl
                ? `<a class="ops-incident-action" href="${escapeHtml(reportUrl)}" aria-label="Xem sự cố ${escapeHtml(incident.code || incident.title || incident.id)}">Xem</a>`
                : "";
            const resolveAction = adminChangeUrl
                ? `<a class="ops-incident-action ops-incident-action--primary" href="${escapeHtml(adminChangeUrl)}" aria-label="Xử lý sự cố ${escapeHtml(incident.code || incident.title || incident.id)}">Xử lý</a>`
                : "";

            return `
                <article class="ops-incident-card" data-incident-id="${incident.id}" aria-label="Sự cố ${escapeHtml(incident.title || incident.code || incident.id)}">
                    <div class="ops-incident-card__top">
                        <div class="ops-incident-card__main">
                            <span class="ops-incident-card__severity ${toneClass(incidentTone(incident.level))}">${escapeHtml(incident.level_label || incidentLabel(incident.level))}</span>
                            <div class="ops-incident-card__title">${escapeHtml(incident.title || "Sự cố hiện trường")}</div>
                        </div>
                        <span class="ops-incident-card__time">${escapeHtml(incident.thoi_gian || "--:--")}</span>
                    </div>
                    <div class="ops-incident-card__meta">${escapeHtml(incidentMetaLine(incident))}</div>
                    <div class="ops-incident-card__bottom">
                        <div class="ops-incident-card__sub">${escapeHtml(incidentHandlerLine(incident))}</div>
                        <div class="ops-incident-card__actions">${viewAction}${focusAction}${resolveAction}</div>
                    </div>
                </article>
            `;
        }).join("");

        list.querySelectorAll("[data-incident-id]").forEach((node) => {
            node.addEventListener("click", function (event) {
                if (event.target && event.target.closest("a, button")) {
                    return;
                }
                const incidentId = Number(node.getAttribute("data-incident-id"));
                const incident = renderedIncidents.find((item) => Number(item.id) === incidentId);
                if (incident) {
                    selectEntity("incident", incident);
                }
            });
        });

        list.querySelectorAll("[data-focus-map='incident']").forEach((node) => {
            node.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                const incidentId = Number(node.getAttribute("data-incident-focus-id"));
                const incident = renderedIncidents.find((item) => Number(item.id) === incidentId);
                if (incident && normalizeLatLng(incident)) {
                    selectEntity("incident", incident);
                }
            });
        });
    }

    function updateGuardList(markers) {
        const list = el("guard-list");
        if (!list) {
            return;
        }

        const renderedGuards = filterState.guards ? (markers || []) : [];
        if (el("guard-count")) {
            el("guard-count").textContent = `${renderedGuards.length} người`;
        }

        if (renderedGuards.length === 0) {
            list.innerHTML = "<div class='wall-item' style='cursor:default;'>Không có nhân viên online phù hợp bộ lọc hiện tại.</div>";
            return;
        }

        list.innerHTML = renderedGuards.map((guard) => `
            <button type="button" class="wall-item" data-guard-id="${guard.id}">
                <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
                    <span class="scmd-tone scmd-tone--info">${escapeHtml(guard.check_in_time || "--:--")}</span>
                    <span style="font-size:11px;font-weight:800;color:#93c5fd;">${escapeHtml(guard.employee_code || "")}</span>
                </div>
                <div class="wall-item__title">${escapeHtml(guard.name)}</div>
                <div class="wall-item__meta">${escapeHtml(guard.target || "Mục tiêu chưa xác định")}</div>
                <div class="wall-item__sub">${escapeHtml(guard.post_name || "Chốt")} • ${escapeHtml(guard.phone || "Chưa có số liên hệ")}</div>
            </button>
        `).join("");

        list.querySelectorAll("[data-guard-id]").forEach((node) => {
            node.addEventListener("click", function () {
                const guardId = Number(node.getAttribute("data-guard-id"));
                const guard = renderedGuards.find((item) => Number(item.id) === guardId);
                if (guard) {
                    selectEntity("guard", guard);
                }
            });
        });
    }

    function updateActivity(recentActivity) {
        const list = el("activity-log");
        if (!list) {
            return;
        }

        if (!recentActivity || recentActivity.length === 0) {
            list.innerHTML = variant === "display"
                ? "<div class='wall-item' style='cursor:default;'>Chưa có sự kiện mới trong ngày.</div>"
                : "<div class='ops-empty-row'>Chưa có sự kiện mới trong ngày.</div>";
            return;
        }

        list.innerHTML = recentActivity.map((item) => {
            const tone = item.kind === "incident" ? "danger" : "info";
            if (variant === "display") {
                return `
                    <button type="button" class="wall-item" data-activity-kind="${escapeHtml(item.kind || "activity")}" data-activity-lat="${escapeHtml(item.lat || "")}" data-activity-lng="${escapeHtml(item.lng || "")}">
                        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;">
                            <span class="${toneClass(tone)}">${escapeHtml(activityLabel(item))}</span>
                            <span style="font-size:11px;font-weight:800;color:#93c5fd;">${escapeHtml(item.time || "--:--")}</span>
                        </div>
                        <div class="wall-item__title">${escapeHtml(item.user || "Chưa xác định")}</div>
                        <div class="wall-item__sub">${escapeHtml(activitySummary(item))}</div>
                    </button>
                `;
            }
            const actions = buildActivityActions(item);
            return `
                <article class="ops-activity-item">
                    <div class="ops-activity-item__actor">${escapeHtml(item.user || "Chưa xác định")}</div>
                    <div class="ops-activity-item__summary"><span class="${toneClass(tone)} ops-mini-badge">${escapeHtml(activityLabel(item))}</span> ${escapeHtml(activitySummary(item))}</div>
                    <div class="ops-activity-item__time">${escapeHtml(item.time || "--:--")}</div>
                    <div class="ops-activity-item__actions">${actions}</div>
                </article>
            `;
        }).join("");

        if (variant === "display") {
            list.querySelectorAll("[data-activity-lat][data-activity-lng]").forEach((node) => {
                node.addEventListener("click", function () {
                    focusCoordinates(
                        node.getAttribute("data-activity-lat"),
                        node.getAttribute("data-activity-lng"),
                        node.getAttribute("data-activity-kind"),
                        node.getAttribute("data-activity-entity-id")
                    );
                });
            });
            return;
        }

        bindActivityFocusActions(list);
    }

    function updateTicker(incidents) {
        const ticker = el("incident-ticker");
        if (!ticker) {
            return;
        }

        const renderedIncidents = (incidents || []).filter((incident) => {
            if (!filterState.incidents) {
                return false;
            }
            if (!filterState.critical) {
                return true;
            }
            return incident.level === "CAO" || incident.level === "NGUY_HIEM";
        });

        if (renderedIncidents.length === 0) {
            ticker.textContent = "Chưa có cảnh báo mới.";
            return;
        }

        ticker.textContent = renderedIncidents
            .slice(0, 4)
            .map((item) => `${incidentLabel(item.level)} • ${item.title} • ${item.muc_tieu || "Hiện trường"}`)
            .join(" | ");
    }

    function updateMap(markers, incidents) {
        guardLayer.clearLayers();
        incidentLayer.clearLayers();
        effectLayer.clearLayers();
        markerRegistry.guards.clear();
        markerRegistry.incidents.clear();

        const bounds = [];
        let newestIncident = null;
        let newestCheckin = null;

        (markers || []).forEach((guard) => {
            const eventKey = `${guard.id}:${guard.check_in_time || ""}`;
            const isNewGuard = !knownGuardEvents.has(eventKey);
            knownGuardEvents.add(eventKey);
            if (isNewGuard && !isFirstLoad) {
                newestCheckin = guard;
            }

            if (!filterState.guards) {
                return;
            }

            const coords = normalizeLatLng(guard);
            if (!coords) {
                return;
            }

            const marker = L.marker(coords, { icon: createGuardIcon(guard) })
                .bindPopup(createPopupContent(guard, "guard"))
                .addTo(guardLayer);

            marker.on("click", function () {
                selectEntity("guard", guard, { focusMap: false });
            });

            markerRegistry.guards.set(guard.id, marker);
            bounds.push(coords);

            if (isNewGuard && !isFirstLoad) {
                showRipple(coords[0], coords[1], "checkin");
            }
        });

        (incidents || []).forEach((incident) => {
            const isNewIncident = !knownIncidentIds.has(incident.id);
            if (isNewIncident) {
                knownIncidentIds.add(incident.id);
                if (!isFirstLoad) {
                    newestIncident = incident;
                }
            }

            if (!filterState.incidents) {
                return;
            }
            if (filterState.critical && !(incident.level === "CAO" || incident.level === "NGUY_HIEM")) {
                return;
            }

            const coords = normalizeLatLng(incident);
            if (!coords) {
                return;
            }

            const marker = L.marker(coords, { icon: createIncidentIcon(incident) })
                .bindPopup(createPopupContent(incident, "incident"))
                .addTo(incidentLayer);

            marker.on("click", function () {
                selectEntity("incident", incident, { focusMap: false });
            });

            markerRegistry.incidents.set(incident.id, marker);
            bounds.push(coords);

            if (isNewIncident && !isFirstLoad) {
                showRipple(coords[0], coords[1], "incident");
            }
        });

        if (isFirstLoad && bounds.length > 0) {
            map.fitBounds(bounds, { padding: [48, 48] });
        }

        if (!isFirstLoad && newestIncident) {
            flashEvent("incident");
            const coords = normalizeLatLng(newestIncident);
            if (coords) {
                map.flyTo(coords, 17, { duration: 1.8 });
            }
            const marker = markerRegistry.incidents.get(newestIncident.id);
            if (marker) {
                marker.openPopup();
            }
            selectEntity("incident", newestIncident, { focusMap: false });
            return;
        }

        if (!isFirstLoad && newestCheckin) {
            flashEvent("checkin");
            if (variant === "display") {
                const coords = normalizeLatLng(newestCheckin);
                if (coords) {
                    map.flyTo(coords, 16, { duration: 1.5 });
                }
            }
            const marker = markerRegistry.guards.get(newestCheckin.id);
            if (marker) {
                marker.openPopup();
            }
            selectEntity("guard", newestCheckin, { focusMap: false });
            return;
        }

        if (selectedState) {
            const registry = selectedState.kind === "guard" ? markerRegistry.guards : markerRegistry.incidents;
            const marker = registry.get(selectedState.id);
            if (marker) {
                marker.openPopup();
            }
        }
    }

    function updateClock() {
        const clock = el("ops-clock");
        if (!clock) {
            return;
        }
        const now = new Date();
        clock.textContent = now.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
    }

    function bindFilterButtons() {
        root.querySelectorAll("[data-filter-kind]").forEach((button) => {
            button.addEventListener("click", function () {
                const key = button.getAttribute("data-filter-kind");
                if (!Object.prototype.hasOwnProperty.call(filterState, key)) {
                    return;
                }
                filterState[key] = !filterState[key];
                button.classList.toggle("is-active", filterState[key]);
                refreshData();
            });
        });
    }

    function setRefreshButtonLoading(isLoading) {
        if (!refreshButton) {
            return;
        }

        if (!refreshButton.dataset.originalLabel) {
            refreshButton.dataset.originalLabel = refreshButton.textContent.trim() || "Làm mới dữ liệu";
        }

        refreshButton.disabled = isLoading;
        refreshButton.setAttribute("aria-busy", isLoading ? "true" : "false");
        refreshButton.classList.toggle("opacity-60", isLoading);
        refreshButton.classList.toggle("cursor-wait", isLoading);
        refreshButton.textContent = isLoading ? "Đang làm mới..." : refreshButton.dataset.originalLabel;
    }

    function refreshData() {
        if (isFetching) {
            return Promise.resolve(false);
        }

        isFetching = true;
        setRefreshButtonLoading(true);

        return fetch(apiUrl, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
            credentials: "same-origin",
            cache: "no-store",
        })
            .then((response) => {
                if (!response.ok) {
                    return parseErrorPayload(response);
                }
                return response.json();
            })
            .then((data) => {
                const stats = data.stats || {};
                const incidents = data.incidents || [];
                const markers = data.markers || [];

                updateStats(stats);
                const recentActivity = data.recent_activity || [];
                updateStatus(stats, incidents, data.last_activity || null, recentActivity);
                updateIncidents(incidents);
                updateGuardList(markers);
                updateActivity(recentActivity);
                updateTicker(incidents);
                updateMap(markers, incidents);
                safeInvalidateMap(80);
                isFirstLoad = false;
                return true;
            })
            .catch((error) => {
                setDashboardMessage("danger", "Lỗi tải dữ liệu", apiErrorMessage(error));
                return false;
            })
            .finally(() => {
                isFetching = false;
                setRefreshButtonLoading(false);
            });
    }

    function stopPolling() {
        if (!pollingIntervalId) {
            return;
        }
        window.clearInterval(pollingIntervalId);
        pollingIntervalId = null;
    }

    function startPolling() {
        if (pollingIntervalId || document.hidden) {
            return;
        }
        pollingIntervalId = window.setInterval(refreshData, normalizedVariant === "display" ? 8000 : 15000);
    }

    refreshButton = root.querySelector("[data-refresh-dashboard]");
    if (refreshButton) {
        refreshButton.addEventListener("click", refreshData);
    }

    document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
            stopPolling();
            return;
        }
        refreshData();
        startPolling();
    });

    initializeWidgets();
    bindFilterButtons();
    updateClock();
    safeInvalidateMap(0);
    safeInvalidateMap(180);
    safeInvalidateMap(520);
    window.addEventListener("resize", function () {
        safeInvalidateMap(120);
    });
    window.setInterval(updateClock, 30000);
    refreshData();
    startPolling();
})();
