/* File: static/admin/js/scmd_admin_scroll.js */

document.addEventListener("DOMContentLoaded", function() {
    'use strict';

    const sidebar = document.getElementById('nav-sidebar');
    if (!sidebar) {
        console.warn("SCMD: Không tìm thấy #nav-sidebar. Kiểm tra lại theme Admin.");
        return;
    }

    const currentPath = window.location.pathname;
    const modules = sidebar.querySelectorAll('.module');
    
    let activeModule = null;

    // --- LOGIC ACCORDION ---
    modules.forEach(module => {
        const caption = module.querySelector('caption');
        const links = module.querySelectorAll('a:not(.section)'); // Link con
        let isModuleActive = false;

        // 1. Kiểm tra xem Module này có chứa link đang xem không?
        links.forEach(link => {
            const href = link.getAttribute('href');
            if (href && currentPath.startsWith(href) && href !== '#') {
                isModuleActive = true;
                link.classList.add('scmd-active-link'); // Highlight link con
                // Highlight dòng tr
                const row = link.closest('tr');
                if (row) row.classList.add('scmd-active-row');
            }
        });

        // 2. Xử lý trạng thái Ban đầu (Init)
        if (isModuleActive) {
            module.classList.remove('collapsed'); // MỞ RA
            activeModule = module;
        } else {
            // Nếu không phải module Search, thì ĐÓNG LẠI
            if (!module.classList.contains('search')) {
                module.classList.add('collapsed');
            }
        }

        // 3. Gắn sự kiện Click để Đóng/Mở thủ công
        if (caption) {
            caption.addEventListener('click', function(e) {
                // Nếu click vào chính chữ Link (App Label) thì để nó chuyển trang
                // Nếu click vào khoảng trống hoặc mũi tên -> Toggle
                if (e.target.tagName !== 'A') {
                    e.preventDefault();
                    module.classList.toggle('collapsed');
                }
            });
        }
    });

    // --- LOGIC AUTO-SCROLL (Cuộn module active lên đầu) ---
    if (activeModule) {
        setTimeout(() => {
            // Tính toán vị trí để cuộn Module lên ngay dưới Header
            // Trừ 60px cho Header
            const topPos = activeModule.offsetTop - 60;
            sidebar.scrollTo({
                top: topPos,
                behavior: 'smooth'
            });
        }, 300); // Đợi 300ms để trình duyệt render xong việc đóng mở
    }
});