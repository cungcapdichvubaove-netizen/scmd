/* File: static/admin/js/scmd_jazzmin_scroll.js
Description: Sidebar Engine cho Jazzmin/AdminLTE.
             Tính năng: Auto-Expand, Auto-Collapse, Snap-Scroll.
             Updated: 2026-03-22 - Optimized performance & precision.
*/

document.addEventListener("DOMContentLoaded", function() {
    'use strict';

    // 1. Xác định Container Sidebar của Jazzmin
    const sidebarContainer = document.querySelector('.sidebar');
    if (!sidebarContainer) return;

    // 2. Tìm link đang Active
    let activeLink = sidebarContainer.querySelector('.nav-treeview .nav-link.active');
    
    if (!activeLink) {
        activeLink = sidebarContainer.querySelector('.nav-link.active');
    }

    if (activeLink) {
        // --- A. AUTO-EXPAND (Mở rộng menu nhánh đang active) ---
        let parentItem = activeLink.closest('.nav-item.has-treeview');
        
        while (parentItem) {
            parentItem.classList.add('menu-open');
            const subMenu = parentItem.querySelector('.nav-treeview');
            if (subMenu) {
                subMenu.style.display = 'block'; 
            }
            parentItem = parentItem.parentElement.closest('.nav-item.has-treeview');
        }

        // --- B. AUTO-COLLAPSE (Đóng các menu không liên quan) ---
        const allOpenMenus = sidebarContainer.querySelectorAll('.nav-item.has-treeview.menu-open');
        allOpenMenus.forEach(menu => {
            if (!menu.contains(activeLink)) {
                menu.classList.remove('menu-open');
                const subMenu = menu.querySelector('.nav-treeview');
                if (subMenu) subMenu.style.display = 'none';
            }
        });

        // --- C. SNAP SCROLL (Cuộn tới vị trí chuẩn xác) ---
        const scrollToActive = () => {
            try {
                const containerRect = sidebarContainer.getBoundingClientRect();
                const activeRect = activeLink.getBoundingClientRect();
                const relativeTop = activeRect.top - containerRect.top;
                
                const targetScrollTop = sidebarContainer.scrollTop + relativeTop - (containerRect.height / 2) + (activeRect.height / 2);

                sidebarContainer.scrollTo({
                    top: targetScrollTop,
                    behavior: 'auto'
                });
            } catch (err) {
                console.error("SCMD Scroll Error:", err);
            }
        };

        // --- D. TRIGGER MULTI-PHASE ---
        scrollToActive();
        setTimeout(scrollToActive, 300);
        window.addEventListener('load', () => setTimeout(scrollToActive, 100));
    }
});