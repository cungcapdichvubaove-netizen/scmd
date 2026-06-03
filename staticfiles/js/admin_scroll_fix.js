/*
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: static/js/admin_scroll_fix.js
Author: Mr. Anh
Created Date: 2025-12-05
Description: Script cải thiện UX cho trang Admin (Jazzmin).
             - Tự động tìm menu item đang active và cuộn nó ra giữa màn hình.
*/

document.addEventListener("DOMContentLoaded", function() {
    // Jazzmin/AdminLTE thường gán class 'active' cho thẻ a hoặc li
    const activeLink = document.querySelector('.nav-sidebar .nav-link.active');

    if (activeLink) {
        // Cuộn mượt mà vào giữa
        activeLink.scrollIntoView({
            behavior: 'smooth',
            block: 'center',
            inline: 'nearest'
        });

        // Hiệu ứng highlight để báo hiệu vị trí
        const originalTransition = activeLink.style.transition;
        activeLink.style.transition = "background-color 0.5s ease";
        
        // Nháy nhẹ màu nền (nếu theme hỗ trợ)
        activeLink.style.filter = "brightness(1.2)";
        
        setTimeout(() => {
            activeLink.style.filter = "brightness(1)";
            activeLink.style.transition = originalTransition;
        }, 800);
    }
});