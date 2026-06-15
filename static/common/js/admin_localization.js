(function () {
    "use strict";

    const TEXT_MAP = new Map(Object.entries({
        "Save": "Lưu",
        "Save as new": "Lưu thành bản mới",
        "Save and add another": "Lưu và thêm mới",
        "Save and continue editing": "Lưu và tiếp tục sửa",
        "Save and view": "Lưu và xem",
        "Delete": "Xóa",
        "History": "Lịch sử",
        "Close": "Đóng",
        "Go": "Thực hiện",
        "Search": "Tìm kiếm",
        "Add": "Thêm",
        "Change": "Sửa",
        "View": "Xem",
        "Today": "Hôm nay",
        "Now": "Bây giờ",
        "Clear": "Xóa",
        "Currently": "Hiện tại",
        "Change:": "Đổi:",
        "No file chosen": "Chưa chọn tệp",
        "Choose File": "Chọn tệp",
        "Home": "Trang chủ",
        "Authentication and Authorization": "Xác thực và phân quyền",
        "Users": "Người dùng",
        "Groups": "Nhóm quyền",
        "User": "Người dùng",
        "Group": "Nhóm quyền",
        "Action": "Hành động",
        "Module": "Phân hệ",
        "Status": "Trạng thái",
        "Results": "Kết quả",
        "records": "bản ghi",
        "result": "kết quả",
        "results": "kết quả",
        "Add user": "Thêm người dùng",
        "Add group": "Thêm nhóm quyền",
        "Filter": "Bộ lọc",
        "By status": "Theo trạng thái",
        "Yes": "Có",
        "No": "Không",
        "Unknown": "Chưa xác định"
    }));

    window.SCMDAdminLocalization = window.SCMDAdminLocalization || {};
    window.SCMDAdminLocalization.textMap = window.SCMDAdminLocalization.textMap || {};
    TEXT_MAP.forEach(function (value, key) {
        if (!Object.prototype.hasOwnProperty.call(window.SCMDAdminLocalization.textMap, key)) {
            window.SCMDAdminLocalization.textMap[key] = value;
        }
    });

    function normalize(text) {
        return (text || "").replace(/\s+/g, " ").trim();
    }

    function translateValue(el, attr) {
        const current = normalize(el.getAttribute(attr));
        if (TEXT_MAP.has(current)) {
            el.setAttribute(attr, TEXT_MAP.get(current));
        }
    }

    function translateTextNode(el) {
        if (!el || el.dataset.scmdLocalized === "1") return;
        const current = normalize(el.textContent);
        if (TEXT_MAP.has(current)) {
            el.textContent = TEXT_MAP.get(current);
            el.dataset.scmdLocalized = "1";
        }
    }

    function localizeButtons(root) {
        root.querySelectorAll('input[type="submit"], input[type="button"], button').forEach(function (el) {
            if (el.value) translateValue(el, "value");
            translateValue(el, "title");
            translateValue(el, "aria-label");
            translateTextNode(el);
        });

        root.querySelectorAll('a, span, label').forEach(function (el) {
            translateValue(el, "title");
            translateValue(el, "aria-label");
            translateTextNode(el);
        });
    }

    function localizeDateInputs(root) {
        root.querySelectorAll('input.vDateField').forEach(function (input) {
            if (!input.getAttribute("placeholder")) {
                input.setAttribute("placeholder", "YYYY-MM-DD hoặc DD/MM/YYYY");
            }
            if (!input.getAttribute("title")) {
                input.setAttribute("title", "Nhập ngày theo định dạng hệ thống; không tự động đổi dữ liệu trong ô.");
            }
        });
    }

    function upgradeFileInputs(root) {
        root.querySelectorAll('input[type="file"]:not([data-scmd-file-ui])').forEach(function (input) {
            const wrapper = document.createElement("span");
            wrapper.className = "scmd-admin-file-control";

            const button = document.createElement("button");
            button.type = "button";
            button.className = "button scmd-admin-file-button";
            button.textContent = "Chọn tệp";

            const filename = document.createElement("span");
            filename.className = "scmd-admin-file-name";
            filename.textContent = input.files && input.files.length ? input.files[0].name : "Chưa chọn tệp";
            input.dataset.scmdFileUi = "1";
            input.classList.add("scmd-admin-file-input-hidden");
            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(button);
            wrapper.appendChild(filename);
            wrapper.appendChild(input);

            button.addEventListener("click", function () { input.click(); });
            input.addEventListener("change", function () {
                filename.textContent = input.files && input.files.length ? input.files[0].name : "Chưa chọn tệp";
            });
        });
    }


    function normalizeTopbarSearch() {
        const navbar = document.querySelector("#jazzy-navbar");
        if (!navbar) return;

        const searchForms = Array.from(navbar.querySelectorAll("form.form-inline")).filter(function (form) {
            if (form.hasAttribute("data-scmd-global-search")) return false;
            const hasSearchInput = Boolean(form.querySelector('input[name="q"], input[type="search"]'));
            const hasJazzminModelControl = Boolean(form.querySelector('select[name="model_name"], select[name="app_label"], .select2'));
            const hasSearchSubmit = Boolean(form.querySelector('button[type="submit"], input[type="submit"]'));
            return hasSearchSubmit && (hasSearchInput || hasJazzminModelControl);
        });
        // Hide only legacy Jazzmin search forms. Do not hide arbitrary topbar
        // forms that future admin shell features may intentionally add.
        searchForms.forEach(function (form) {
            form.setAttribute("hidden", "hidden");
            form.setAttribute("aria-hidden", "true");
            form.setAttribute("data-scmd-hidden-legacy-search", "1");
        });
    }

    function ensureUnifiedGlobalSearch() {
        const navbar = document.querySelector("#jazzy-navbar");
        if (!navbar || navbar.querySelector("[data-scmd-global-search]")) return;

        const shellConfig = window.SCMDAdminShell || {};
        const searchUrl = shellConfig.globalSearchUrl || "/admin/search/";
        const rightNav = navbar.querySelector(".navbar-nav.ml-auto") || navbar.lastElementChild;
        const currentParams = new URLSearchParams(window.location.search);
        const currentValue = window.location.pathname.indexOf("/admin/search/") === 0 ? (currentParams.get("q") || "") : "";

        const form = document.createElement("form");
        form.className = "scmd-global-search";
        form.setAttribute("data-scmd-global-search", "1");
        form.setAttribute("role", "search");
        form.method = "get";
        form.action = searchUrl;

        const label = document.createElement("label");
        label.className = "sr-only";
        label.setAttribute("for", "scmd-global-search-input");
        label.textContent = "Tìm kiếm toàn hệ thống";

        const input = document.createElement("input");
        input.id = "scmd-global-search-input";
        input.type = "search";
        input.name = "q";
        input.autocomplete = "off";
        input.placeholder = "Tìm nhân viên, mục tiêu, hợp đồng...";
        input.value = currentValue;

        const button = document.createElement("button");
        button.type = "submit";
        button.setAttribute("aria-label", "Tìm kiếm");
        button.innerHTML = "<i class=\"fas fa-search\" aria-hidden=\"true\"></i>";

        form.appendChild(label);
        form.appendChild(input);
        form.appendChild(button);

        if (rightNav && rightNav.parentNode === navbar) {
            navbar.insertBefore(form, rightNav);
        } else {
            navbar.appendChild(form);
        }
    }

    function localizeAdmin(root) {
        localizeButtons(root || document);
        localizeDateInputs(root || document);
        upgradeFileInputs(root || document);
    }

    document.addEventListener("DOMContentLoaded", function () {
        normalizeTopbarSearch();
        ensureUnifiedGlobalSearch();
        localizeAdmin(document);
        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        normalizeTopbarSearch();
                        ensureUnifiedGlobalSearch();
                        localizeAdmin(node);
                    }
                });
            });
        });
        observer.observe(document.body, {childList: true, subtree: true});
    });
})();
