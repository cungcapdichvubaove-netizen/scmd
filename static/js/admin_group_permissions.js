(function () {
    function normalize(value) {
        return (value || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .trim();
    }

    document.addEventListener("DOMContentLoaded", function () {
        const searchInput = document.getElementById("scmd-permission-search");
        if (!searchInput) {
            return;
        }

        const permissionCards = Array.from(
            document.querySelectorAll(".scmd-permission-section li, .scmd-permission-section label")
        );

        searchInput.addEventListener("input", function () {
            const keyword = normalize(searchInput.value);

            permissionCards.forEach((node) => {
                const target = node.matches("label") ? node : node.querySelector("label") || node;
                const text = normalize(target.textContent);
                const visible = !keyword || text.includes(keyword);
                node.classList.toggle("scmd-permission-hidden", !visible);
            });
        });
    });
})();
