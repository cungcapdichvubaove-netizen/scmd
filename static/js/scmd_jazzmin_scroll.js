/*
 * SCMD admin sidebar normalization for Jazzmin/AdminLTE.
 * Scope:
 * - localize common admin chrome
 * - normalize sidebar labels to sentence case
 * - add logical group headers
 * - refine user panel role label
 * - keep active item expanded and centered
 */

document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const sidebarContainer = document.querySelector(".sidebar");

    const sharedTextMap = (window.SCMDAdminLocalization && window.SCMDAdminLocalization.textMap) || {};
    const jazzminTextMap = {
        "Account": "T\u00e0i kho\u1ea3n",
        "Change password": "\u0110\u1ed5i m\u1eadt kh\u1ea9u",
        "Log out": "\u0110\u0103ng xu\u1ea5t",
        "See Profile": "Xem h\u1ed3 s\u01a1",
        "Dashboard": "B\u1ea3ng \u0111i\u1ec1u khi\u1ec3n",
        "staff status": "Nh\u00e2n vi\u00ean h\u1ec7 th\u1ed1ng",
        "superuser status": "Qu\u1ea3n tr\u1ecb t\u1ed1i cao",
        "active": "\u0110ang ho\u1ea1t \u0111\u1ed9ng",
        "groups": "Nh\u00f3m quy\u1ec1n",
        "Jazzmin version": "Phi\u00ean b\u1ea3n Jazzmin",
        "All rights reserved.": "\u0110\u00e3 \u0111\u0103ng k\u00fd m\u1ecdi quy\u1ec1n.",
        "Choose language": "Ch\u1ecdn ng\u00f4n ng\u1eef",
    };
    const TEXT_REPLACEMENTS = new Map(Object.entries(Object.assign({}, sharedTextMap, jazzminTextMap)));

    const LABEL_REPLACEMENTS = {
        DASHBOARD: "B\u1ea3ng \u0111i\u1ec1u khi\u1ec3n",
        "QU\u1ea2N TR\u1eca H\u1ec6 TH\u1ed0NG": "Qu\u1ea3n tr\u1ecb h\u1ec7 th\u1ed1ng",
        "C\u1ea4U H\u00ccNH CHUNG": "C\u1ea5u h\u00ecnh chung",
        "QU\u1ea2N TR\u1eca NH\u00c2N S\u1ef0": "Qu\u1ea3n tr\u1ecb nh\u00e2n s\u1ef1",
        "QU\u1ea2N L\u00dd KINH DOANH": "Qu\u1ea3n l\u00fd kinh doanh",
        "\u0110I\u1ec0U H\u00c0NH & GI\u00c1M S\u00c1T": "\u0110i\u1ec1u h\u00e0nh v\u00e0 gi\u00e1m s\u00e1t",
        "THANH TRA & TU\u1ea6N TRA": "Thanh tra v\u00e0 tu\u1ea7n tra",
        "T\u00c0I CH\u00cdNH & K\u1ebe TO\u00c1N": "T\u00e0i ch\u00ednh v\u00e0 k\u1ebf to\u00e1n",
        "QU\u1ea2N L\u00dd KHO & V\u1eacT T\u01af": "Qu\u1ea3n l\u00fd kho v\u00e0 v\u1eadt t\u01b0",
        "V\u0102N PH\u00d2NG S\u1ed0": "V\u0103n ph\u00f2ng s\u1ed1",
        "B\u00c1O C\u00c1O & TH\u1ed0NG K\u00ca": "B\u00e1o c\u00e1o v\u00e0 th\u1ed1ng k\u00ea",
        "L\u1ecaCH TR\u00ccNH T\u1ef0 \u0110\u1ed8NG": "L\u1ecbch tr\u00ecnh t\u1ef1 \u0111\u1ed9ng",
        "K\u1ebeT QU\u1ea2 T\u00c1C V\u1ee4": "K\u1ebft qu\u1ea3 t\u00e1c v\u1ee5",
    };

    const NAV_SECTION_MAP = [
        { title: "T\u1ed5ng quan", labels: ["B\u1ea3ng \u0111i\u1ec1u khi\u1ec3n"] },
        { title: "Qu\u1ea3n tr\u1ecb", labels: ["Qu\u1ea3n tr\u1ecb h\u1ec7 th\u1ed1ng", "C\u1ea5u h\u00ecnh chung"] },
        {
            title: "Nh\u00e2n s\u1ef1 v\u00e0 t\u00e0i ch\u00ednh",
            labels: ["Qu\u1ea3n tr\u1ecb nh\u00e2n s\u1ef1", "T\u00e0i ch\u00ednh v\u00e0 k\u1ebf to\u00e1n", "Qu\u1ea3n l\u00fd kho v\u00e0 v\u1eadt t\u01b0"],
        },
        {
            title: "H\u1ec7 th\u1ed1ng",
            labels: ["V\u0103n ph\u00f2ng s\u1ed1", "B\u00e1o c\u00e1o v\u00e0 th\u1ed1ng k\u00ea", "L\u1ecbch tr\u00ecnh t\u1ef1 \u0111\u1ed9ng", "K\u1ebft qu\u1ea3 t\u00e1c v\u1ee5"],
        },
        {
            title: "V\u1eadn h\u00e0nh",
            labels: ["Qu\u1ea3n l\u00fd kinh doanh", "\u0110i\u1ec1u h\u00e0nh v\u00e0 gi\u00e1m s\u00e1t", "Thanh tra v\u00e0 tu\u1ea7n tra"],
        },
    ];

    function normalizeWhitespace(text) {
        return text.replace(/\s+/g, " ").trim();
    }

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
            input.setAttribute("placeholder", current.replace(/^Search\s*/u, "T\u00ecm ki\u1ebfm "));

            const aria = input.getAttribute("aria-label") || "";
            if (aria) {
                input.setAttribute("aria-label", aria.replace(/^Search\s*/u, "T\u00ecm ki\u1ebfm "));
            }
        });

        document.querySelectorAll('[title="Choose language"]').forEach((node) => {
            node.setAttribute("title", "Ch\u1ecdn ng\u00f4n ng\u1eef");
        });

        document.querySelectorAll('input[type="submit"], button, .btn').forEach((node) => {
            const text = node.textContent.trim();
            if (TEXT_REPLACEMENTS.has(text)) {
                node.textContent = TEXT_REPLACEMENTS.get(text);
            }
        });

        document.querySelectorAll("select option").forEach((option) => {
            const text = option.textContent.trim();
            if (TEXT_REPLACEMENTS.has(text)) {
                option.textContent = TEXT_REPLACEMENTS.get(text);
            }
        });
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
        return LABEL_REPLACEMENTS[upper] || normalized;
    }

    function findLabelNode(link) {
        return link.querySelector("p, span");
    }

    function dedupeSidebarLinks(navSidebar) {
        const seenKeys = new Set();

        navSidebar.querySelectorAll(".nav-treeview .nav-link, .nav-sidebar > .nav-item > .nav-link").forEach((link) => {
            const href = (link.getAttribute("href") || "").trim();
            const labelNode = findLabelNode(link);
            const label = normalizeWhitespace(labelNode ? labelNode.textContent : "");
            const key = `${href}::${label}`;

            if (!href || !label || !key) {
                return;
            }

            if (seenKeys.has(key)) {
                const duplicateItem = link.closest(".nav-item");
                if (duplicateItem) {
                    duplicateItem.remove();
                }
                return;
            }

            seenKeys.add(key);
        });
    }

    function enhanceSidebarNavigation() {
        const navSidebar = sidebarContainer ? sidebarContainer.querySelector(".nav-sidebar") : null;
        if (!navSidebar) {
            return;
        }

        const topLevelItems = Array.from(navSidebar.children).filter(
            (node) => node.classList && node.classList.contains("nav-item"),
        );

        const itemMetadata = topLevelItems.map((item) => {
            const link = item.querySelector(":scope > .nav-link");
            const labelNode = link ? findLabelNode(link) : null;
            const rawLabel = labelNode ? labelNode.textContent : "";
            const cleanedLabel = cleanLabel(rawLabel);

            if (labelNode && cleanedLabel) {
                labelNode.textContent = cleanedLabel;
            }

            if (link && cleanedLabel) {
                link.setAttribute("title", cleanedLabel);
                link.dataset.scmdLabel = cleanedLabel;
            }

            item.querySelectorAll(".nav-treeview .nav-link").forEach((subLink) => {
                const subLabelNode = findLabelNode(subLink);
                if (!subLabelNode) {
                    return;
                }

                const subCleaned = cleanLabel(subLabelNode.textContent);
                subLabelNode.textContent = subCleaned;
                subLink.setAttribute("title", subCleaned);
            });

            return { item, cleanedLabel };
        });

        dedupeSidebarLinks(navSidebar);

        navSidebar.querySelectorAll(".scmd-sidebar-group").forEach((node) => node.remove());

        NAV_SECTION_MAP.forEach((section) => {
            const firstMatch = itemMetadata.find(({ cleanedLabel }) => section.labels.includes(cleanedLabel));
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
        if (!sidebarContainer) {
            return;
        }

        const runtime = window.SCMDAdminSidebarData || {};
        const badgeConfig = {
            "L\u1ecbch tr\u00ecnh t\u1ef1 \u0111\u1ed9ng": runtime.periodicEnabled,
            "K\u1ebft qu\u1ea3 t\u00e1c v\u1ee5": runtime.taskAlerts,
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
        if (!sidebarContainer) {
            return;
        }

        if (sidebarContainer.querySelector(".scmd-sidebar-profile-card")) {
            return;
        }

        const shellConfig = window.SCMDAdminShell || {};
        const userPanel = sidebarContainer.querySelector(".user-panel");
        const nav = sidebarContainer.querySelector("nav.mt-2");

        if (!userPanel || !nav || userPanel.closest(".scmd-sidebar-footer")) {
            return;
        }

        const footer = document.createElement("div");
        footer.className = "scmd-sidebar-footer";

        const profileLink = userPanel.querySelector(".info a");
        const infoNode = userPanel.querySelector(".info");

        if (infoNode && !infoNode.querySelector(".scmd-sidebar-role")) {
            const role = document.createElement("span");
            role.className = "scmd-sidebar-role";
            role.textContent = "Quản trị kỹ thuật";
            infoNode.appendChild(role);
        }

        userPanel.classList.add("scmd-sidebar-user-identity", "scmd-sidebar-user-shortcuts");
        userPanel.classList.remove("scmd-sidebar-user-toggle", "is-open");
        userPanel.removeAttribute("tabindex");
        userPanel.removeAttribute("aria-expanded");
        userPanel.setAttribute("title", "Tài khoản kỹ thuật");

        if (profileLink) {
            profileLink.setAttribute("href", shellConfig.passwordChangeUrl || "/admin/password_change/");
            profileLink.setAttribute("title", "Đổi mật khẩu tài khoản kỹ thuật");
            profileLink.setAttribute("aria-label", "Đổi mật khẩu tài khoản kỹ thuật");
        }

        const actions = document.createElement("div");
        actions.className = "scmd-sidebar-footer-actions";

        [
            {
                href: shellConfig.globalSearchUrl || "/admin/search/",
                icon: "fas fa-search",
                label: "Tìm kiếm",
                title: "Tìm kiếm toàn hệ thống",
            },
            {
                href: shellConfig.adminIndexUrl || "/admin/",
                icon: "fas fa-shield-alt",
                label: "Console",
                title: "Bảng quản trị kỹ thuật",
            },
            {
                href: shellConfig.logoutUrl || "/admin/logout/",
                icon: "fas fa-sign-out-alt",
                label: "Thoát",
                title: "Thoát tài khoản",
                danger: true,
            },
        ].forEach(function (item) {
            const link = document.createElement("a");
            link.className = "scmd-sidebar-footer-action";
            if (item.danger) {
                link.classList.add("is-danger");
            }
            link.href = item.href;
            link.setAttribute("title", item.title);
            link.setAttribute("aria-label", item.title);
            link.innerHTML = `<i class="${item.icon}" aria-hidden="true"></i><span>${item.label}</span>`;
            actions.appendChild(link);
        });

        footer.appendChild(userPanel);
        footer.appendChild(actions);
        sidebarContainer.appendChild(footer);
    }



    function enhanceSidebarAccountPopover() {
        if (!sidebarContainer) {
            return;
        }

        const profileCard = sidebarContainer.querySelector(".scmd-sidebar-profile-card");
        const profileTrigger = profileCard ? profileCard.querySelector("[data-account-tooltip-trigger]") : null;
        const popover = profileCard ? profileCard.querySelector(".scmd-sidebar-profile-popover") : null;

        if (!profileCard || !profileTrigger || !popover) {
            return;
        }

        function markOpen() {
            profileCard.classList.add("is-popover-open");
            profileCard.classList.remove("is-popover-dismissed");
            profileTrigger.setAttribute("aria-expanded", "true");
        }

        function markClosed() {
            profileCard.classList.remove("is-popover-open");
            profileTrigger.setAttribute("aria-expanded", "false");
        }

        profileCard.addEventListener("mouseenter", markOpen);
        profileCard.addEventListener("focusin", markOpen);
        profileCard.addEventListener("mouseleave", markClosed);
        profileCard.addEventListener("focusout", function () {
            window.setTimeout(function () {
                if (!profileCard.contains(document.activeElement)) {
                    markClosed();
                    profileCard.classList.remove("is-popover-dismissed");
                }
            }, 0);
        });

        profileTrigger.addEventListener("click", function (event) {
            if (event.target.closest("a, button, form")) {
                return;
            }
            if (profileCard.classList.contains("is-popover-open")) {
                markClosed();
            } else {
                markOpen();
            }
            event.preventDefault();
            event.stopPropagation();
        });

        profileTrigger.addEventListener("keydown", function (event) {
            if (event.key !== "Enter" && event.key !== " ") {
                return;
            }
            if (profileCard.classList.contains("is-popover-open")) {
                markClosed();
            } else {
                markOpen();
            }
            event.preventDefault();
            event.stopPropagation();
        });

        profileCard.addEventListener("keydown", function (event) {
            if (event.key !== "Escape") {
                return;
            }
            profileCard.classList.add("is-popover-dismissed");
            markClosed();
            profileTrigger.focus();
            event.preventDefault();
            event.stopPropagation();
        });

        document.addEventListener("click", function (event) {
            if (profileCard.contains(event.target)) {
                return;
            }
            markClosed();
        });
    }

    function enhanceHeaderAccountMenu() {
        const accountNav = document.querySelector(".scmd-account-nav");
        const trigger = accountNav ? accountNav.querySelector(".scmd-account-trigger") : null;
        const menu = accountNav ? accountNav.querySelector(".scmd-account-menu") : null;

        if (!accountNav || !trigger || !menu) {
            return;
        }

        function markOpen() {
            accountNav.classList.add("show");
            trigger.classList.add("show");
            menu.classList.add("show");
            trigger.setAttribute("aria-expanded", "true");
        }

        function markClosed() {
            accountNav.classList.remove("show");
            trigger.classList.remove("show");
            menu.classList.remove("show");
            trigger.setAttribute("aria-expanded", "false");
        }

        function toggleMenu() {
            if (menu.classList.contains("show")) {
                markClosed();
            } else {
                markOpen();
            }
        }

        trigger.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            toggleMenu();
        });

        trigger.addEventListener("keydown", function (event) {
            if (event.key !== "Enter" && event.key !== " ") {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            toggleMenu();
        });

        menu.addEventListener("click", function (event) {
            event.stopPropagation();
        });

        document.addEventListener("click", function (event) {
            if (accountNav.contains(event.target)) {
                return;
            }
            markClosed();
        });

        document.addEventListener("keydown", function (event) {
            if (event.key !== "Escape") {
                return;
            }
            markClosed();
        });
    }

    function autoExpandAndScroll() {
        if (!sidebarContainer) {
            return;
        }

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
            } catch (error) {
                console.error("SCMD sidebar scroll error:", error);
            }
        };

        scrollToActive();
        setTimeout(scrollToActive, 300);
        window.addEventListener("load", () => setTimeout(scrollToActive, 100));
    }

    localizeAdminChrome();
    enhanceSidebarNavigation();
    attachSidebarBadges();
    enhanceUserPanel();
    enhanceSidebarAccountPopover();
    enhanceHeaderAccountMenu();
    autoExpandAndScroll();
});
