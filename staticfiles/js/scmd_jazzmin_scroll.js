/* File: static/js/scmd_jazzmin_scroll.js
Description: Sidebar enhancement cho Jazzmin/AdminLTE.
             Tính năng: làm sạch nhãn, phân nhóm menu, badge sidebar,
             chuyển account card xuống footer, auto-expand, snap-scroll.
             Updated: 2026-06-02 - admin sidebar shell refinement.
*/

document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const sidebarContainer = document.querySelector(".sidebar");
    const TEXT_REPLACEMENTS = new Map([
        ["Account", "Tài khoản"],
        ["Change password", "Đổi mật khẩu"],
        ["Log out", "Đăng xuất"],
        ["See Profile", "Xem hồ sơ"],
        ["Dashboard", "Bảng điều khiển"],
        ["Jazzmin version", "Phiên bản Jazzmin"],
        ["All rights reserved.", "Đã đăng ký mọi quyền."],
        ["Choose language", "Chọn ngôn ngữ"],
    ]);

    function replaceExactText(root) {
        if (!root) {
            return;
        }

        root.querySelectorAll("*").forEach((node) => {
            if (node.children.length > 0) {
                return;
            }

            const text = node.textContent.trim();
            if (TEXT_REPLACEMENTS.has(text)) {
                node.textContent = TEXT_REPLACEMENTS.get(text);
            }
        });
    }

    function localizeAdminChrome() {
        replaceExactText(document);

        document.querySelectorAll('input[placeholder^="Search"]').forEach((input) => {
            const current = input.getAttribute("placeholder") || "";
            input.setAttribute("placeholder", current.replace(/^Search\s*/u, "Tìm kiếm "));
            const aria = input.getAttribute("aria-label") || "";
            if (aria) {
                input.setAttribute("aria-label", aria.replace(/^Search\s*/u, "Tìm kiếm "));
            }
        });

        document.querySelectorAll('[title="Choose language"]').forEach((node) => {
            node.setAttribute("title", "Chọn ngôn ngữ");
        });
    }

    localizeAdminChrome();

    if (!sidebarContainer) {
        return;
    }

    const NAV_SECTION_MAP = [
        {
            title: "Tổng quan",
            labels: ["Bảng điều khiển"],
        },
        {
            title: "Vận hành",
            labels: [
                "Quản lý kinh doanh",
                "Điều hành & giám sát",
                "Thanh tra & tuần tra",
            ],
        },
        {
            title: "Nhân sự & tài chính",
            labels: [
                "Quản trị nhân sự",
                "Tài chính & kế toán",
                "Quản lý kho & vật tư",
            ],
        },
        {
            title: "Hệ thống",
            labels: [
                "Báo cáo & thống kê",
                "Lịch trình tự động",
                "Kết quả tác vụ",
                "Văn phòng số",
            ],
        },
        {
            title: "Quản trị",
            labels: ["Quản trị hệ thống", "Cấu hình chung"],
        },
    ];

    const LABEL_REPLACEMENTS = {
        "QUẢN TRỊ HỆ THỐNG": "Quản trị hệ thống",
        "CẤU HÌNH CHUNG": "Cấu hình chung",
        "QUẢN TRỊ NHÂN SỰ": "Quản trị nhân sự",
        "QUẢN LÝ KINH DOANH": "Quản lý kinh doanh",
        "ĐIỀU HÀNH & GIÁM SÁT": "Điều hành & giám sát",
        "THANH TRA & TUẦN TRA": "Thanh tra & tuần tra",
        "TÀI CHÍNH & KẾ TOÁN": "Tài chính & kế toán",
        "QUẢN LÝ KHO & VẬT TƯ": "Quản lý kho & vật tư",
        "VĂN PHÒNG SỐ": "Văn phòng số",
        "BÁO CÁO & THỐNG KÊ": "Báo cáo & thống kê",
        "LỊCH TRÌNH TỰ ĐỘNG": "Lịch trình tự động",
        "KẾT QUẢ TÁC VỤ": "Kết quả tác vụ",
        "DASHBOARD": "Bảng điều khiển",
    };

    function normalizeWhitespace(text) {
        return text.replace(/\s+/g, " ").trim();
    }

    function cleanLabel(rawText) {
        const normalized = normalizeWhitespace(rawText)
            .replace(/^\d+\.\s*/u, "")
            .replace(/[‹›]+$/u, "")
            .replace(/\.\.\.$/u, "")
            .trim();

        if (!normalized) {
            return normalized;
        }

        const upper = normalized.toUpperCase();
        if (LABEL_REPLACEMENTS[upper]) {
            return LABEL_REPLACEMENTS[upper];
        }

        return normalized;
    }

    function findLinkLabelNode(link) {
        return link.querySelector("p, span");
    }

    function enhanceSidebarNavigation() {
        const navSidebar = sidebarContainer.querySelector(".nav-sidebar");
        if (!navSidebar) {
            return;
        }

        const topLevelItems = Array.from(navSidebar.children).filter(
            (node) => node.classList && node.classList.contains("nav-item"),
        );

        const itemMetadata = topLevelItems.map((item) => {
            const link = item.querySelector(":scope > .nav-link");
            const labelNode = link ? findLinkLabelNode(link) : null;
            const rawLabel = labelNode ? labelNode.textContent : "";
            const cleanedLabel = cleanLabel(rawLabel);

            if (labelNode && cleanedLabel) {
                labelNode.textContent = cleanedLabel;
            }

            if (link && cleanedLabel) {
                link.setAttribute("title", cleanedLabel);
                link.dataset.scmdLabel = cleanedLabel;
            }

            const subLinks = item.querySelectorAll(".nav-treeview .nav-link");
            subLinks.forEach((subLink) => {
                const subLabelNode = findLinkLabelNode(subLink);
                if (!subLabelNode) {
                    return;
                }
                const subCleaned = cleanLabel(subLabelNode.textContent);
                subLabelNode.textContent = subCleaned;
                subLink.setAttribute("title", subCleaned);
            });

            return { item, cleanedLabel };
        });

        navSidebar.querySelectorAll(".scmd-sidebar-group").forEach((node) => node.remove());

        NAV_SECTION_MAP.forEach((section) => {
            const firstMatch = itemMetadata.find(
                ({ cleanedLabel }) => section.labels.includes(cleanedLabel),
            );
            if (!firstMatch) {
                return;
            }

            const header = document.createElement("li");
            header.className = "nav-header scmd-sidebar-group";
            header.textContent = section.title;
            navSidebar.insertBefore(header, firstMatch.item);
        });
    }

    function attachSidebarBadges() {
        const runtime = window.SCMDAdminSidebarData || {};
        const badgeConfig = {
            "Lịch trình tự động": runtime.periodicEnabled,
            "Kết quả tác vụ": runtime.taskAlerts,
        };

        sidebarContainer.querySelectorAll(".nav-link[data-scmd-label]").forEach((link) => {
            const label = link.dataset.scmdLabel;
            const count = badgeConfig[label];
            if (!count || count < 1 || link.querySelector(".scmd-sidebar-badge")) {
                return;
            }

            const badge = document.createElement("span");
            badge.className = "scmd-sidebar-badge";
            badge.textContent = count > 99 ? "99+" : String(count);
            link.appendChild(badge);
        });
    }

    function enhanceUserPanel() {
        const userPanel = sidebarContainer.querySelector(".user-panel");
        const nav = sidebarContainer.querySelector("nav.mt-2");

        if (!userPanel || !nav || userPanel.closest(".scmd-sidebar-footer")) {
            return;
        }

        const footer = document.createElement("div");
        footer.className = "scmd-sidebar-footer";

        const profileLink = userPanel.querySelector(".info a");
        const profileHref = profileLink ? profileLink.getAttribute("href") : null;
        const infoNode = userPanel.querySelector(".info");

        if (infoNode && !infoNode.querySelector(".scmd-sidebar-role")) {
            const role = document.createElement("span");
            role.className = "scmd-sidebar-role";
            role.textContent = "Quản trị viên";
            infoNode.appendChild(role);
        }

        userPanel.classList.add("scmd-sidebar-user-toggle");
        userPanel.setAttribute("tabindex", "0");

        const menu = document.createElement("div");
        menu.className = "scmd-sidebar-user-menu";

        const links = [];
        if (profileHref) {
            links.push({ href: profileHref, label: "Hồ sơ", icon: "fas fa-id-badge" });
        }
        links.push({ href: "/admin/password_change/", label: "Đổi mật khẩu", icon: "fas fa-key" });
        links.push({ href: "/admin/logout/", label: "Đăng xuất", icon: "fas fa-sign-out-alt", danger: true });

        links.forEach((item) => {
            const anchor = document.createElement("a");
            anchor.href = item.href;
            anchor.className = "scmd-sidebar-user-action";
            if (item.danger) {
                anchor.classList.add("is-danger");
            }
            anchor.innerHTML = `<i class="${item.icon}"></i><span>${item.label}</span>`;
            menu.appendChild(anchor);
        });

        footer.appendChild(userPanel);
        footer.appendChild(menu);
        sidebarContainer.appendChild(footer);

        const closeMenu = () => {
            userPanel.classList.remove("is-open");
            menu.classList.remove("is-open");
        };

        const toggleMenu = (event) => {
            if (event.target.closest(".scmd-sidebar-user-action")) {
                return;
            }
            event.preventDefault();
            userPanel.classList.toggle("is-open");
            menu.classList.toggle("is-open");
        };

        userPanel.addEventListener("click", toggleMenu);
        userPanel.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                toggleMenu(event);
            }
            if (event.key === "Escape") {
                closeMenu();
            }
        });

        document.addEventListener("click", (event) => {
            if (!userPanel.contains(event.target) && !menu.contains(event.target)) {
                closeMenu();
            }
        });
    }

    function autoExpandAndScroll() {
        let activeLink = sidebarContainer.querySelector(".nav-treeview .nav-link.active");

        if (!activeLink) {
            activeLink = sidebarContainer.querySelector(".nav-link.active");
        }

        if (!activeLink) {
            return;
        }

        let parentItem = activeLink.closest(".nav-item.has-treeview");
        while (parentItem) {
            parentItem.classList.add("menu-open");
            const subMenu = parentItem.querySelector(".nav-treeview");
            if (subMenu) {
                subMenu.style.display = "block";
            }
            parentItem = parentItem.parentElement.closest(".nav-item.has-treeview");
        }

        const allOpenMenus = sidebarContainer.querySelectorAll(".nav-item.has-treeview.menu-open");
        allOpenMenus.forEach((menu) => {
            if (!menu.contains(activeLink)) {
                menu.classList.remove("menu-open");
                const subMenu = menu.querySelector(".nav-treeview");
                if (subMenu) {
                    subMenu.style.display = "none";
                }
            }
        });

        const scrollToActive = () => {
            try {
                const containerRect = sidebarContainer.getBoundingClientRect();
                const activeRect = activeLink.getBoundingClientRect();
                const relativeTop = activeRect.top - containerRect.top;
                const targetScrollTop =
                    sidebarContainer.scrollTop +
                    relativeTop -
                    containerRect.height / 2 +
                    activeRect.height / 2;

                sidebarContainer.scrollTo({
                    top: targetScrollTop,
                    behavior: "auto",
                });
            } catch (err) {
                console.error("SCMD sidebar scroll error:", err);
            }
        };

        scrollToActive();
        setTimeout(scrollToActive, 300);
        window.addEventListener("load", () => setTimeout(scrollToActive, 100));
    }

    enhanceSidebarNavigation();
    attachSidebarBadges();
    enhanceUserPanel();
    autoExpandAndScroll();
    localizeAdminChrome();
});
