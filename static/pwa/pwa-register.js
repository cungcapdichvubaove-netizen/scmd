(function () {
  "use strict";

  const PWA_DISMISS_KEY = "scmd-pwa-install-dismissed-session";
  const PWA_UPDATE_DISMISS_KEY = "scmd-pwa-update-dismissed-session";
  const PWA_INSTALLED_COOKIE = "scmd_pwa_installed";
  const PWA_INSTALLED_COOKIE_VALUE = "1";
  const PWA_INSTALLED_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;
  const isSecureContextForPwa = window.location.protocol === "https:" || window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
  let deferredInstallPrompt = null;
  let installPromptRendered = false;
  let updatePromptRendered = false;

  function supportsMatchMedia() {
    return typeof window.matchMedia === "function";
  }

  function isDisplayModeStandalone() {
    return supportsMatchMedia() && (
      window.matchMedia("(display-mode: standalone)").matches ||
      window.matchMedia("(display-mode: fullscreen)").matches ||
      window.matchMedia("(display-mode: minimal-ui)").matches ||
      window.matchMedia("(display-mode: window-controls-overlay)").matches
    );
  }

  function isAndroidTrustedWebActivity() {
    return typeof document.referrer === "string" && document.referrer.indexOf("android-app://") === 0;
  }

  function readCookie(name) {
    const cookieName = `${name}=`;
    const cookies = document.cookie ? document.cookie.split(";") : [];

    for (let index = 0; index < cookies.length; index += 1) {
      const cookie = cookies[index].trim();
      if (cookie.indexOf(cookieName) === 0) {
        return cookie.slice(cookieName.length);
      }
    }

    return null;
  }

  function persistInstalledState() {
    try {
      document.cookie = `${PWA_INSTALLED_COOKIE}=${PWA_INSTALLED_COOKIE_VALUE}; Max-Age=${PWA_INSTALLED_COOKIE_MAX_AGE}; Path=/; SameSite=Lax`;
    } catch (error) {
      /* Installed state persistence is best effort only. */
    }
  }

  function hasPersistedInstalledState() {
    return readCookie(PWA_INSTALLED_COOKIE) === PWA_INSTALLED_COOKIE_VALUE;
  }

  function setStandaloneClass() {
    const isStandalone = isDisplayModeStandalone() || window.navigator.standalone === true || isAndroidTrustedWebActivity();
    document.documentElement.classList.toggle("pwa-standalone", Boolean(isStandalone));
    if (isStandalone) {
      persistInstalledState();
      document.documentElement.classList.add("pwa-installed");
    }
  }

  function isStandaloneMode() {
    return document.documentElement.classList.contains("pwa-standalone") || isDisplayModeStandalone() || window.navigator.standalone === true || isAndroidTrustedWebActivity();
  }

  function isAuthBoundaryUrl(url) {
    return /(^|\/)(login|logout|password-reset|password-change)(\/|$)/i.test(url.pathname);
  }

  function shouldSuppressInstallPrompt() {
    if (isStandaloneMode()) return true;
    if (hasPersistedInstalledState()) return true;
    if (!isSecureContextForPwa) return true;
    if (window.sessionStorage && window.sessionStorage.getItem(PWA_DISMISS_KEY) === "1") return true;

    const path = window.location.pathname || "/";
    const isInstallEntry = /^\/($|login\/?$|operations\/mobile\/)/i.test(path);
    return !isInstallEntry || /^\/admin(\/|$)/i.test(path) || /^\/(logout|password-reset|password-change)(\/|$)/i.test(path);
  }

  function isLikelyIosSafari() {
    const ua = window.navigator.userAgent || "";
    const isIos = /iphone|ipad|ipod/i.test(ua) || (window.navigator.platform === "MacIntel" && window.navigator.maxTouchPoints > 1);
    const isWebKit = /safari/i.test(ua) && !/crios|fxios|edgios|chrome|android/i.test(ua);
    return isIos && isWebKit;
  }

  function injectInstallPromptStyle() {
    if (document.getElementById("scmd-pwa-install-style")) return;
    const style = document.createElement("style");
    style.id = "scmd-pwa-install-style";
    style.textContent = [
      ".scmd-pwa-install { position: fixed; left: 1rem; right: 1rem; bottom: calc(1rem + env(safe-area-inset-bottom)); z-index: 9999; display: flex; align-items: center; gap: .75rem; padding: .875rem 1rem; border-radius: 1rem; background: #0f172a; color: #fff; box-shadow: 0 20px 45px rgba(15, 23, 42, .25); font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }",
      ".pwa-standalone .scmd-pwa-install { display: none !important; }",
      ".scmd-pwa-install__icon { width: 2.75rem; height: 2.75rem; border-radius: .85rem; background: #020617; display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto; overflow: hidden; box-shadow: inset 0 0 0 1px rgba(255,255,255,.10); }",
      ".scmd-pwa-install__icon img { width: 2.35rem; height: 2.35rem; display: block; object-fit: contain; }",
      ".scmd-pwa-install__body { min-width: 0; flex: 1; }",
      ".scmd-pwa-install__title { font-weight: 800; font-size: .95rem; line-height: 1.2; margin: 0 0 .15rem; }",
      ".scmd-pwa-install__text { opacity: .82; font-size: .78rem; line-height: 1.35; margin: 0; }",
      ".scmd-pwa-install__actions { display: flex; align-items: center; gap: .5rem; flex: 0 0 auto; }",
      ".scmd-pwa-install__button { border: 0; border-radius: 999px; padding: .55rem .85rem; font-weight: 800; font-size: .78rem; cursor: pointer; background: #f8fafc; color: #0f172a; }",
      ".scmd-pwa-install__close { border: 0; width: 2rem; height: 2rem; border-radius: 999px; cursor: pointer; color: #cbd5e1; background: rgba(255,255,255,.08); font-size: 1.1rem; line-height: 1; }",
      "@media (min-width: 640px) { .scmd-pwa-install { left: auto; right: 1.25rem; bottom: 1.25rem; max-width: 26rem; } }"
    ].join("\n");
    document.head.appendChild(style);
  }

  function dismissInstallPrompt() {
    const prompt = document.getElementById("scmd-pwa-install-prompt");
    if (prompt) prompt.remove();
    installPromptRendered = false;
    try {
      window.sessionStorage && window.sessionStorage.setItem(PWA_DISMISS_KEY, "1");
    } catch (error) {
      /* Session dismissal is best effort only. */
    }
  }

  function dismissUpdatePrompt() {
    const prompt = document.getElementById("scmd-pwa-update-prompt");
    if (prompt) prompt.remove();
    updatePromptRendered = false;
    try {
      window.sessionStorage && window.sessionStorage.setItem(PWA_UPDATE_DISMISS_KEY, "1");
    } catch (error) {
      /* Session dismissal is best effort only. */
    }
  }

  function buildInstallPrompt(options) {
    const prompt = document.createElement("section");
    prompt.id = "scmd-pwa-install-prompt";
    prompt.className = "scmd-pwa-install";
    prompt.setAttribute("role", "status");
    prompt.setAttribute("aria-live", "polite");

    const icon = document.createElement("div");
    icon.className = "scmd-pwa-install__icon";

    const iconImg = document.createElement("img");
    iconImg.src = "/static/img/brand/android-chrome-192x192.png";
    iconImg.alt = "";
    iconImg.width = 38;
    iconImg.height = 38;
    iconImg.loading = "eager";
    iconImg.decoding = "async";
    iconImg.addEventListener("error", function () {
      iconImg.src = "/static/img/brand/favicon-48x48.png";
    }, { once: true });
    icon.appendChild(iconImg);

    const body = document.createElement("div");
    body.className = "scmd-pwa-install__body";

    const title = document.createElement("p");
    title.className = "scmd-pwa-install__title";
    title.textContent = options.title;

    const text = document.createElement("p");
    text.className = "scmd-pwa-install__text";
    text.textContent = options.text;

    body.appendChild(title);
    body.appendChild(text);

    const actions = document.createElement("div");
    actions.className = "scmd-pwa-install__actions";

    if (options.actionLabel && typeof options.onAction === "function") {
      const installButton = document.createElement("button");
      installButton.type = "button";
      installButton.className = "scmd-pwa-install__button";
      installButton.textContent = options.actionLabel;
      installButton.addEventListener("click", options.onAction);
      actions.appendChild(installButton);
    }

    const closeButton = document.createElement("button");
    closeButton.type = "button";
    closeButton.className = "scmd-pwa-install__close";
    closeButton.setAttribute("aria-label", "Ẩn gợi ý cài đặt");
    closeButton.textContent = "×";
    closeButton.addEventListener("click", dismissInstallPrompt);
    actions.appendChild(closeButton);

    prompt.appendChild(icon);
    prompt.appendChild(body);
    prompt.appendChild(actions);
    return prompt;
  }

  function showInstallPrompt(options) {
    if (installPromptRendered || shouldSuppressInstallPrompt()) return;
    injectInstallPromptStyle();
    const existing = document.getElementById("scmd-pwa-install-prompt");
    if (existing) existing.remove();
    document.body.appendChild(buildInstallPrompt(options));
    installPromptRendered = true;
  }

  function showUpdatePrompt(registration) {
    if (!registration || !registration.waiting || updatePromptRendered) return;
    try {
      if (window.sessionStorage && window.sessionStorage.getItem(PWA_UPDATE_DISMISS_KEY) === "1") return;
    } catch (error) {
      /* Session dismissal is best effort only. */
    }

    injectInstallPromptStyle();
    const existing = document.getElementById("scmd-pwa-update-prompt");
    if (existing) existing.remove();

    const prompt = buildInstallPrompt({
      title: "Cap nhat SCMD Pro",
      text: "Phien ban moi san sang. Tai lai de dung shell va du lieu tinh moi nhat.",
      actionLabel: "Cap nhat",
      onAction: function () {
        if (registration.waiting) {
          registration.waiting.postMessage({ type: "SCMD_PWA_SKIP_WAITING" });
        }
      }
    });
    prompt.id = "scmd-pwa-update-prompt";
    const closeButton = prompt.querySelector(".scmd-pwa-install__close");
    if (closeButton) {
      closeButton.addEventListener("click", dismissUpdatePrompt, { once: true });
    }
    document.body.appendChild(prompt);
    updatePromptRendered = true;
  }

  function showBrowserInstallPrompt() {
    showInstallPrompt({
      title: "Cài SCMD Pro",
      text: "Mở nhanh như ứng dụng, giữ giao diện ổn định hơn khi mạng yếu.",
      actionLabel: "Cài đặt",
      onAction: function () {
        const promptEvent = deferredInstallPrompt;
        if (!promptEvent) return;
        deferredInstallPrompt = null;
        const promptNode = document.getElementById("scmd-pwa-install-prompt");
        if (promptNode) promptNode.remove();
        installPromptRendered = false;
        promptEvent.prompt();
        promptEvent.userChoice.finally(function () {
          dismissInstallPrompt();
        });
      }
    });
  }

  function showIosInstallHint() {
    showInstallPrompt({
      title: "Thêm SCMD Pro vào Màn hình chính",
      text: "Trên iPhone/iPad: chạm Chia sẻ, sau đó chọn Thêm vào Màn hình chính.",
      actionLabel: null,
      onAction: null
    });
  }

  function showManualInstallHint() {
    showInstallPrompt({
      title: "Cài SCMD Pro",
      text: "Nếu trình duyệt chưa hiện nút Cài đặt, hãy dùng biểu tượng cài đặt trên thanh địa chỉ hoặc menu trình duyệt.",
      actionLabel: "Hướng dẫn",
      onAction: function () {
        window.alert("Chrome/Edge: chọn biểu tượng cài đặt trên thanh địa chỉ hoặc mở menu trình duyệt và chọn Cài đặt ứng dụng. iPhone/iPad: chọn Chia sẻ rồi Thêm vào Màn hình chính.");
      }
    });
  }

  function clearLocalPwaCaches() {
    if (!window.caches || typeof window.caches.keys !== "function") return Promise.resolve();
    return window.caches.keys()
      .then(function (keys) {
        return Promise.all(keys.filter(function (key) { return key.indexOf("scmd-pro-") === 0; }).map(function (key) { return window.caches.delete(key); }));
      })
      .catch(function () { return undefined; });
  }

  function clearPwaCaches(registration) {
    clearLocalPwaCaches();
    if (!registration || !registration.active) return;
    registration.active.postMessage({ type: "SCMD_PWA_CLEAR_CACHES" });
  }

  function wireServiceWorkerUpdates(registration) {
    if (!registration) return;
    registration.addEventListener("updatefound", function () {
      const installingWorker = registration.installing;
      if (!installingWorker) return;
      installingWorker.addEventListener("statechange", function () {
        if (installingWorker.state === "installed" && navigator.serviceWorker.controller) {
          showUpdatePrompt(registration);
        }
      });
    });

    if (registration.waiting) {
      showUpdatePrompt(registration);
    }
  }

  function registerAuthBoundaryCachePurge(registration) {
    document.addEventListener("click", function (event) {
      const link = event.target && event.target.closest ? event.target.closest("a[href]") : null;
      if (!link) return;
      const url = new URL(link.getAttribute("href"), window.location.origin);
      if (url.origin === window.location.origin && isAuthBoundaryUrl(url)) {
        clearPwaCaches(registration);
      }
    }, true);

    document.addEventListener("submit", function (event) {
      const form = event.target;
      if (!form || !form.action) return;
      const url = new URL(form.action, window.location.origin);
      if (url.origin === window.location.origin && isAuthBoundaryUrl(url)) {
        clearPwaCaches(registration);
      }
    }, true);
  }

  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault();
    deferredInstallPrompt = event;
    showBrowserInstallPrompt();
  });

  window.addEventListener("appinstalled", function () {
    deferredInstallPrompt = null;
    persistInstalledState();
    dismissInstallPrompt();
    document.documentElement.classList.add("pwa-installed");
  });

  if ("serviceWorker" in navigator && isSecureContextForPwa) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { scope: "/" })
        .then(function (registration) {
          setStandaloneClass();
          if (supportsMatchMedia()) {
            window.matchMedia("(display-mode: standalone)").addEventListener?.("change", setStandaloneClass);
          }
          registerAuthBoundaryCachePurge(registration);
          wireServiceWorkerUpdates(registration);

          if (isLikelyIosSafari()) {
            window.setTimeout(showIosInstallHint, 1200);
          } else {
            window.setTimeout(function () {
              if (!deferredInstallPrompt) {
                showManualInstallHint();
              }
            }, 1800);
          }
        })
        .catch(function () {
          /* PWA registration must never block the operational UI. */
        });
    });

    navigator.serviceWorker.addEventListener?.("controllerchange", function () {
      document.documentElement.classList.add("pwa-controller-updated");
      window.location.reload();
    });
  }
})();
