(function () {
    const quoteDataNode = document.getElementById("login-quotes-data");
    const quoteTitle = document.getElementById("quote-title");
    const quoteMessage = document.getElementById("quote-message");
    const quoteAuthor = document.getElementById("quote-author");
    const quoteStage = document.getElementById("quote-stage");
    const topicButtons = Array.from(document.querySelectorAll(".login-topic"));
    const passwordInput = document.getElementById("id_password");
    const passwordToggle = document.getElementById("password-toggle");
    const loginForm = document.getElementById("login-form");
    const notices = document.getElementById("login-notices");
    const submitButton = document.getElementById("login-submit");
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    let quotes = [];

    if (quoteDataNode) {
        try {
            quotes = JSON.parse(quoteDataNode.textContent);
        } catch (error) {
            quotes = [];
        }
    }

    function setActiveTopic(category) {
        topicButtons.forEach((button) => {
            const isActive = button.dataset.quoteCategory === category;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-selected", isActive ? "true" : "false");
        });
    }

    function updateQuote(category) {
        const selectedQuote = quotes.find((quote) => quote.category === category);
        if (!selectedQuote || !quoteTitle || !quoteMessage || !quoteAuthor) {
            return;
        }

        setActiveTopic(category);

        if (!quoteStage || prefersReducedMotion.matches) {
            quoteTitle.textContent = selectedQuote.title;
            quoteMessage.textContent = selectedQuote.message;
            quoteAuthor.textContent = selectedQuote.author;
            return;
        }

        quoteStage.classList.add("is-fading");

        window.setTimeout(function () {
            quoteTitle.textContent = selectedQuote.title;
            quoteMessage.textContent = selectedQuote.message;
            quoteAuthor.textContent = selectedQuote.author;
            quoteStage.classList.remove("is-fading");
        }, 500);
    }

    topicButtons.forEach((button) => {
        button.addEventListener("click", function () {
            updateQuote(button.dataset.quoteCategory);
        });
    });

    if (passwordInput && passwordToggle) {
        passwordToggle.addEventListener("click", function () {
            const isVisible = passwordInput.type === "text";
            passwordInput.type = isVisible ? "password" : "text";
            passwordToggle.classList.toggle("is-visible", !isVisible);
            passwordToggle.setAttribute("aria-pressed", isVisible ? "false" : "true");
            passwordToggle.setAttribute("aria-label", isVisible ? "Hiển thị mật khẩu" : "Ẩn mật khẩu");
        });
    }

    function renderErrorNotice(message) {
        if (!notices) {
            return;
        }

        notices.hidden = false;
        notices.innerHTML = '<div class="login-notice">' + message + "</div>";
    }

    function parseErrorNoticeFromHtml(html) {
        const parsed = new DOMParser().parseFromString(html, "text/html");
        const nextNotices = parsed.getElementById("login-notices");

        if (!nextNotices) {
            return "Vui lòng kiểm tra lại tài khoản và mật khẩu.";
        }

        return nextNotices.innerHTML;
    }

    function startSuccessTransition(redirectUrl) {
        if (prefersReducedMotion.matches) {
            window.location.assign(redirectUrl);
            return;
        }

        document.body.classList.add("is-transitioning");
        window.setTimeout(function () {
            window.location.assign(redirectUrl);
        }, 420);
    }

    if (loginForm) {
        loginForm.addEventListener("submit", function (event) {
            event.preventDefault();

            if (submitButton) {
                submitButton.disabled = true;
            }

            const requestUrl = window.location.pathname + window.location.search;
            const formData = new FormData(loginForm);

            fetch(requestUrl, {
                method: "POST",
                body: formData,
                credentials: "same-origin",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            })
                .then(function (response) {
                    const contentType = response.headers.get("content-type") || "";

                    if (contentType.includes("application/json")) {
                        return response.json();
                    }

                    return response.text().then(function (html) {
                        throw new Error(parseErrorNoticeFromHtml(html));
                    });
                })
                .then(function (payload) {
                    if (payload && payload.success && payload.redirect_url) {
                        startSuccessTransition(payload.redirect_url);
                        return;
                    }

                    renderErrorNotice("Không thể đăng nhập. Vui lòng thử lại.");
                    if (submitButton) {
                        submitButton.disabled = false;
                    }
                })
                .catch(function (error) {
                    if (notices && error.message && error.message.includes("login-notice")) {
                        notices.hidden = false;
                        notices.innerHTML = error.message;
                    } else {
                        renderErrorNotice(error.message || "Không thể đăng nhập. Vui lòng thử lại.");
                    }

                    if (submitButton) {
                        submitButton.disabled = false;
                    }
                });
        });
    }
})();
