document.addEventListener("DOMContentLoaded", () => {
    const navToggle = document.querySelector("[data-nav-toggle]");
    const siteNav = document.querySelector("[data-site-nav]");

    if (navToggle && siteNav) {
        navToggle.addEventListener("click", () => {
            const isOpen = !siteNav.classList.contains("hidden");
            if (isOpen) {
                siteNav.classList.add("hidden");
                navToggle.setAttribute("aria-expanded", "false");
            } else {
                siteNav.classList.remove("hidden");
                navToggle.setAttribute("aria-expanded", "true");
            }
        });
    }

    document.querySelectorAll("[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const message = form.dataset.confirm || "Are you sure?";
            if (!window.confirm(message)) event.preventDefault();
        });
    });

    const formatMoney = (value) => value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    const clampQuantity = (input) => {
        const min = parseInt(input.getAttribute("min") || "1", 10);
        const max = parseInt(input.getAttribute("max") || "999999", 10);
        let value = parseInt(input.value || String(min), 10);
        if (isNaN(value)) value = min;
        value = Math.min(Math.max(value, min), max);
        input.value = String(value);
        return value;
    };

    const cartTable = document.querySelector("[data-cart-table]");
    const totalTarget = document.querySelector("[data-cart-total]");

    const updatePreviewTotals = () => {
        if (!cartTable || !totalTarget) return;
        let total = 0;
        // Cart uses <div> rows, not <table>. Query [data-line-total] directly.
        cartTable.querySelectorAll("[data-line-total]").forEach((lineTotal) => {
            const itemRow = lineTotal.closest("[data-cart-table] > div") || lineTotal.parentElement?.parentElement?.parentElement;
            const quantityInput = itemRow ? itemRow.querySelector("input[name='quantity']") : null;
            if (!quantityInput) return;
            const price = parseFloat(lineTotal.dataset.price || "0");
            const quantity = clampQuantity(quantityInput);
            const rowTotal = price * quantity;
            lineTotal.textContent = `$${formatMoney(rowTotal)}`;
            total += rowTotal;
        });
        // Only overwrite if we found at least one priced row (avoids zeroing a sale-only cart)
        if (cartTable.querySelectorAll("[data-line-total]").length > 0) {
            totalTarget.textContent = `$${formatMoney(total)}`;
        }
    };

    document.querySelectorAll("[data-quantity-step]").forEach((button) => {
        button.addEventListener("click", () => {
            const control = button.closest(".quantity-control");
            const input = control ? control.querySelector("input[name='quantity']") : null;
            if (!input) return;
            const step = parseInt(button.dataset.quantityStep || "0", 10);
            const current = parseInt(input.value || "0", 10);
            input.value = String(current + step);
            clampQuantity(input);
            input.dispatchEvent(new Event("input", { bubbles: true }));
        });
    });

    document.querySelectorAll("input[name='quantity']").forEach((input) => {
        input.addEventListener("input", updatePreviewTotals);
        input.addEventListener("blur", () => { clampQuantity(input); updatePreviewTotals(); });
    });

    document.querySelectorAll("[data-validate-form]").forEach((form) => {
        form.addEventListener("invalid", (event) => { event.preventDefault(); }, true);
        form.addEventListener("submit", (event) => {
            const invalidFields = Array.from(form.querySelectorAll("input, textarea, select"))
                .filter((field) => !field.disabled && !field.checkValidity());
            if (invalidFields.length) {
                event.preventDefault();
                invalidFields[0].focus();
            }
        });
    });

    document.querySelectorAll(".message").forEach((msg) => {
        setTimeout(() => {
            msg.style.transition = "opacity 400ms ease, transform 400ms ease";
            msg.style.opacity = "0";
            msg.style.transform = "translateY(-8px)";
            setTimeout(() => msg.remove(), 400);
        }, 5000);
    });

    updatePreviewTotals();
});
