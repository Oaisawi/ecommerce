/**
 * Epic AI Reads — Mock Payment UI
 * Tab switching, card formatting, brand detection, Luhn validation.
 * Payment is submitted instantly via fetch; spinner shows while server responds.
 */
(function () {
  "use strict";

  // ─── Tab switching ───────────────────────────────────────────
  var tabBtns   = document.querySelectorAll("[data-pay-tab]");
  var tabPanels = document.querySelectorAll(".pay-panel");

  tabBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var target = btn.dataset.payTab;
      tabBtns.forEach(function (b) {
        b.classList.remove("active");
        b.setAttribute("aria-selected", "false");
      });
      tabPanels.forEach(function (p) { p.classList.add("hidden"); });
      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
      var panel = document.getElementById("pay-" + target);
      if (panel) panel.classList.remove("hidden");
    });
  });

  // ─── Card brand detection ────────────────────────────────────
  var BRAND_PATTERNS = {
    VISA:       /^4/,
    MASTERCARD: /^5[1-5]|^2[2-7]/,
    AMEX:       /^3[47]/,
    DISCOVER:   /^6(?:011|5)/,
  };
  var BRAND_ICONS = {
    VISA:       { text: "VISA", cls: "text-blue-700 font-black text-sm" },
    MASTERCARD: { text: "MC",   cls: "text-red-600  font-black text-sm" },
    AMEX:       { text: "AMEX", cls: "text-blue-500 font-black text-xs" },
    DISCOVER:   { text: "DISC", cls: "text-orange-500 font-black text-xs" },
  };

  function detectBrand(number) {
    var n = number.replace(/\s/g, "");
    for (var brand in BRAND_PATTERNS) {
      if (BRAND_PATTERNS[brand].test(n)) return brand;
    }
    return null;
  }

  // ─── Luhn algorithm ──────────────────────────────────────────
  function luhnValid(number) {
    var digits = number.replace(/\s/g, "");
    if (!/^\d+$/.test(digits) || digits.length < 13) return false;
    var total = 0;
    for (var i = 0; i < digits.length; i++) {
      var d = parseInt(digits[digits.length - 1 - i], 10);
      if (i % 2 === 1) { d *= 2; if (d > 9) d -= 9; }
      total += d;
    }
    return total % 10 === 0;
  }

  // ─── Format card number ──────────────────────────────────────
  function formatCardNumber(value) {
    var raw = value.replace(/\D/g, "");
    if (/^3[47]/.test(raw)) {
      return raw.slice(0, 4) +
        (raw.length > 4  ? " " + raw.slice(4, 10)  : "") +
        (raw.length > 10 ? " " + raw.slice(10, 15) : "");
    }
    return raw.slice(0, 4) +
      (raw.length > 4  ? " " + raw.slice(4, 8)   : "") +
      (raw.length > 8  ? " " + raw.slice(8, 12)  : "") +
      (raw.length > 12 ? " " + raw.slice(12, 16) : "");
  }

  // ─── Format expiry ───────────────────────────────────────────
  function formatExpiry(value) {
    var raw = value.replace(/\D/g, "");
    return raw.length <= 2 ? raw : raw.slice(0, 2) + " / " + raw.slice(2, 4);
  }

  // ─── Wire up card inputs ─────────────────────────────────────
  var cardNumberInput = document.querySelector("[data-card-number]");
  var brandIcon       = document.querySelector("[data-card-brand-icon]");
  var cardExpInput    = document.querySelector("[data-card-exp]");
  var cardNumberError = document.getElementById("card-number-error");

  if (cardNumberInput) {
    cardNumberInput.addEventListener("input", function (e) {
      var raw    = e.target.value.replace(/\D/g, "");
      var maxLen = /^3[47]/.test(raw) ? 15 : 16;
      var capped = raw.slice(0, maxLen);
      e.target.value = formatCardNumber(capped);

      var brand = detectBrand(capped);
      if (brandIcon) {
        if (brand && BRAND_ICONS[brand]) {
          brandIcon.textContent = BRAND_ICONS[brand].text;
          brandIcon.className = "absolute right-3 top-1/2 -translate-y-1/2 select-none transition-all " + BRAND_ICONS[brand].cls;
        } else {
          brandIcon.textContent = "";
        }
      }

      if (cardNumberError) {
        if (capped.length >= 13 && !luhnValid(capped)) {
          cardNumberError.textContent = "Card number appears invalid.";
          cardNumberError.classList.remove("hidden");
        } else {
          cardNumberError.classList.add("hidden");
        }
      }
    });
  }

  if (cardExpInput) {
    cardExpInput.addEventListener("input", function (e) {
      e.target.value = formatExpiry(e.target.value);
    });
  }

  // ─── Spinner modal ───────────────────────────────────────────
  function showModal(label) {
    var modal = document.getElementById("processing-modal");
    var lbl   = document.getElementById("processing-label");
    if (lbl && label) lbl.textContent = label;
    if (modal) modal.classList.remove("hidden");
  }

  // ─── Submit via fetch, redirect the instant server responds ──
  function processPayment(form, label) {
    showModal(label || "Processing…");

    fetch(form.action || window.location.href, {
      method: "POST",
      body: new FormData(form),
      redirect: "follow",
      credentials: "same-origin",
    })
    .then(function (res) {
      var finalPath = new URL(res.url).pathname;
      var backOnPayment = finalPath === "/payment/" || finalPath.startsWith("/payment/");
      if (backOnPayment) {
        // Declined / validation error — reload to display the server-rendered message.
        window.location.reload();
      } else {
        // Success — jump straight to confirmation.
        window.location.href = res.url;
      }
    })
    .catch(function () {
      // Network failure fallback: plain form submit.
      form.submit();
    });
  }

  // ─── Card form ────────────────────────────────────────────────
  var cardForm      = document.getElementById("card-form");
  var cardSubmitBtn = document.getElementById("card-submit-btn");

  if (cardForm) {
    cardForm.addEventListener("submit", function (e) {
      e.preventDefault();

      var numberRaw = cardNumberInput ? cardNumberInput.value.replace(/\s/g, "") : "";
      if (!luhnValid(numberRaw)) {
        if (cardNumberError) {
          cardNumberError.textContent = "Please enter a valid card number.";
          cardNumberError.classList.remove("hidden");
        }
        return;
      }

      if (cardSubmitBtn) {
        cardSubmitBtn.disabled = true;
        cardSubmitBtn.innerHTML =
          '<span class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span> Processing…';
      }

      processPayment(cardForm, "Authorising your card…");
    });
  }

  // ─── Wallet buttons & COD ────────────────────────────────────
  window.mockWalletPay = function (formId, btnId, label) {
    var btn  = document.getElementById(btnId);
    var form = document.getElementById(formId);
    if (btn) { btn.disabled = true; btn.style.opacity = "0.7"; }
    if (form) processPayment(form, label || "Processing payment…");
  };

})();
