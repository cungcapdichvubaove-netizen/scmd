(function () {
    function updateOnlineState() {
        var app = document.querySelector('[data-scmd-mobile-app]');
        var label = document.querySelector('[data-mobile-online-label]');
        if (!app || !label) return;
        var offline = navigator && navigator.onLine === false;
        app.classList.toggle('is-offline', offline);
        label.textContent = offline ? 'Ngoại tuyến' : 'Đang kết nối';
    }

    function setAccountPanelOpen(open) {
        var toggle = document.querySelector('[data-mobile-account-toggle]');
        var panel = document.getElementById('scmd-mobile-account-panel');
        if (!toggle || !panel) return;
        if (open) {
            panel.removeAttribute('hidden');
            toggle.setAttribute('aria-expanded', 'true');
        } else {
            panel.setAttribute('hidden', 'hidden');
            toggle.setAttribute('aria-expanded', 'false');
        }
    }

    function setupAccountPanel() {
        document.addEventListener('click', function (event) {
            var toggle = event.target.closest('[data-mobile-account-toggle]');
            var panel = document.getElementById('scmd-mobile-account-panel');
            if (!panel) return;
            if (toggle) {
                event.preventDefault();
                event.stopPropagation();
                setAccountPanelOpen(panel.hasAttribute('hidden'));
                return;
            }
            if (event.target.closest('#scmd-mobile-account-panel')) {
                return;
            }
            setAccountPanelOpen(false);
        });
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') setAccountPanelOpen(false);
        });
    }

    function setupHtmxProgress() {
        if (!window.htmx || !window.NProgress || !document.body) return;
        document.body.addEventListener('htmx:beforeRequest', function () { window.NProgress.start(); });
        document.body.addEventListener('htmx:afterRequest', function () { window.NProgress.done(); });
        document.body.addEventListener('htmx:responseError', function (event) {
            window.NProgress.done();
            var xhr = event.detail && event.detail.xhr;
            if (!xhr) return;
            if (xhr.status === 403 && xhr.responseURL) {
                window.location.href = xhr.responseURL;
            }
        });
        document.body.addEventListener('htmx:afterSwap', function () {
            window.scrollTo(0, 0);
            setAccountPanelOpen(false);
        });
    }

    function setupFloatingSos() {
        var root = document.querySelector('[data-mobile-sos]');
        if (!root) return;

        var shell = root.querySelector('[data-sos-shell]');
        var button = root.querySelector('[data-sos-button]');
        var help = root.querySelector('[data-sos-help]');
        var latInput = root.querySelector('[data-sos-lat]');
        var lngInput = root.querySelector('[data-sos-lng]');
        var form = root.querySelector('form');
        if (!shell || !button || !help || !latInput || !lngInput || !form) return;

        var storageKey = root.getAttribute('data-sos-storage-key') || 'scmd-mobile-sos-position-v1';
        var holdTimer = null;
        var pointerId = null;
        var dragging = false;
        var moved = false;
        var startX = 0;
        var startY = 0;
        var baseX = 0;
        var baseY = 0;
        var posX = 0;
        var posY = 0;

        function viewportWidth() {
            return window.innerWidth || document.documentElement.clientWidth || 0;
        }

        function viewportHeight() {
            return window.innerHeight || document.documentElement.clientHeight || 0;
        }

        function bottomNavOffset() {
            var nav = document.querySelector('.scmd-mobile-bottom-nav');
            return nav ? nav.offsetHeight + 12 : 88;
        }

        function clampPosition(x, y) {
            var margin = 10;
            var width = root.offsetWidth || 96;
            var height = root.offsetHeight || 112;
            var maxX = Math.max(margin, viewportWidth() - width - margin);
            var maxY = Math.max(margin, viewportHeight() - height - bottomNavOffset());
            return {
                x: Math.min(Math.max(x, margin), maxX),
                y: Math.min(Math.max(y, margin), maxY),
            };
        }

        function applyPosition(x, y, persist) {
            var clamped = clampPosition(x, y);
            posX = clamped.x;
            posY = clamped.y;
            root.style.transform = 'translate3d(' + posX + 'px, ' + posY + 'px, 0)';
            if (persist) {
                window.localStorage.setItem(storageKey, JSON.stringify({ x: posX, y: posY }));
            }
        }

        function placeDefault() {
            var width = root.offsetWidth || 96;
            var defaultX = viewportWidth() - width - 14;
            var defaultY = viewportHeight() - (root.offsetHeight || 112) - bottomNavOffset() - 22;
            applyPosition(defaultX, defaultY, false);
        }

        function restorePosition() {
            var raw = null;
            try {
                raw = window.localStorage.getItem(storageKey);
            } catch (error) {
                raw = null;
            }

            if (!raw) {
                placeDefault();
                return;
            }

            try {
                var parsed = JSON.parse(raw);
                if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
                    applyPosition(parsed.x, parsed.y, false);
                    return;
                }
            } catch (error) {
                // Ignore invalid stored data and fall back to default placement.
            }

            placeDefault();
        }

        function stopHold() {
            if (holdTimer) {
                window.clearTimeout(holdTimer);
                holdTimer = null;
            }
            root.classList.remove('is-holding');
        }

        function showHelp(message) {
            help.textContent = message;
        }

        function submitSos() {
            showHelp('Đang gửi SOS...');
            if (!navigator.geolocation) {
                showHelp('Thiết bị không hỗ trợ GPS.');
                window.alert('Thiết bị không hỗ trợ GPS. Không thể gửi SOS.');
                return;
            }

            navigator.geolocation.getCurrentPosition(
                function (position) {
                    latInput.value = position.coords.latitude;
                    lngInput.value = position.coords.longitude;
                    form.submit();
                },
                function () {
                    showHelp('Không lấy được GPS. Thử lại.');
                    window.alert('Không lấy được GPS. Bật định vị và thử lại.');
                },
                { timeout: 10000, enableHighAccuracy: true, maximumAge: 0 }
            );
        }

        function startHold() {
            stopHold();
            root.classList.add('is-holding');
            showHelp('Giữ đủ 2 giây...');
            if (navigator.vibrate) navigator.vibrate(35);
            holdTimer = window.setTimeout(function () {
                holdTimer = null;
                if (navigator.vibrate) navigator.vibrate([150, 80, 150]);
                submitSos();
            }, 2000);
        }

        button.addEventListener('pointerdown', function (event) {
            if (event.button !== undefined && event.button !== 0) return;
            pointerId = event.pointerId;
            dragging = false;
            moved = false;
            startX = event.clientX;
            startY = event.clientY;
            baseX = posX;
            baseY = posY;
            button.setPointerCapture(pointerId);
            startHold();
        });

        button.addEventListener('pointermove', function (event) {
            if (pointerId !== event.pointerId) return;
            var deltaX = event.clientX - startX;
            var deltaY = event.clientY - startY;

            if (!dragging && (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10)) {
                dragging = true;
                moved = true;
                stopHold();
                root.classList.add('is-dragging');
                showHelp('Thả ra để lưu vị trí.');
            }

            if (!dragging) return;
            event.preventDefault();
            applyPosition(baseX + deltaX, baseY + deltaY, false);
        });

        function endPointer(event) {
            if (pointerId !== event.pointerId) return;
            if (button.hasPointerCapture(pointerId)) {
                button.releasePointerCapture(pointerId);
            }
            stopHold();
            if (dragging) {
                applyPosition(posX, posY, true);
                root.classList.remove('is-dragging');
                showHelp('Đã lưu vị trí.');
            } else if (!moved) {
                showHelp('Giữ 2 giây. Kéo để đổi chỗ.');
            }
            pointerId = null;
            dragging = false;
        }

        button.addEventListener('pointerup', endPointer);
        button.addEventListener('pointercancel', endPointer);
        button.addEventListener('lostpointercapture', function () {
            stopHold();
            root.classList.remove('is-dragging');
            pointerId = null;
            dragging = false;
        });

        restorePosition();
        window.addEventListener('resize', function () {
            applyPosition(posX, posY, false);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        updateOnlineState();
        setupAccountPanel();
        setupHtmxProgress();
        setupFloatingSos();
    });
    window.addEventListener('online', updateOnlineState);
    window.addEventListener('offline', updateOnlineState);
})();
