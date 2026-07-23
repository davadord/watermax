// Watermax — interacciones globales

(function () {
  document.addEventListener("DOMContentLoaded", function () {
    initTooltips();
    initConfirmModal();
    initPasswordToggle();
    initFilterReset();
    initSubmitGuard();
    initAutoFocus();
    initClientPicker();
  });

  // Tooltips en cualquier elemento con data-bs-toggle="tooltip"
  function initTooltips() {
    var nodes = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    nodes.forEach(function (el) { new bootstrap.Tooltip(el); });
  }

  // Confirmación única para acciones destructivas
  //   <form ... data-confirm="¿Eliminar X?" data-confirm-detail="…"
  //              data-confirm-action="Sí, eliminar" data-confirm-variant="danger">
  function initConfirmModal() {
    var modalEl = document.getElementById("wm-confirm-modal");
    if (!modalEl) return;
    var modal = new bootstrap.Modal(modalEl);
    var titleEl  = modalEl.querySelector(".wm-confirm-title");
    var detailEl = modalEl.querySelector(".wm-confirm-detail");
    var okBtn    = modalEl.querySelector(".wm-confirm-ok");
    var pendingForm = null;

    modalEl.addEventListener("hidden.bs.modal", function () {
      // Si el usuario canceló, devolver foco al submit pendiente
      if (pendingForm && pendingForm.dataset.confirmed !== "1") {
        var trigger = pendingForm.querySelector('button[type="submit"]');
        if (trigger) trigger.focus();
      }
    });

    modalEl.addEventListener("shown.bs.modal", function () {
      okBtn.focus();
    });

    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        if (form.dataset.confirmed === "1") return;
        e.preventDefault();
        pendingForm = form;
        titleEl.textContent = form.dataset.confirm;
        detailEl.textContent = form.dataset.confirmDetail || "";
        detailEl.style.display = form.dataset.confirmDetail ? "" : "none";
        okBtn.textContent = form.dataset.confirmAction || "Confirmar";
        okBtn.className = "btn btn-" + (form.dataset.confirmVariant || "danger") + " wm-confirm-ok";
        modal.show();
      });
    });

    okBtn.addEventListener("click", function () {
      if (!pendingForm) return;
      pendingForm.dataset.confirmed = "1";
      modal.hide();
      pendingForm.submit();
    });
  }

  // Mostrar / ocultar contraseña en login
  function initPasswordToggle() {
    document.querySelectorAll("[data-toggle-password]").forEach(function (btn) {
      var target = document.querySelector(btn.dataset.togglePassword);
      if (!target) return;
      btn.addEventListener("click", function () {
        var isPwd = target.type === "password";
        target.type = isPwd ? "text" : "password";
        var icon = btn.querySelector("i");
        if (icon) icon.className = isPwd ? "bi bi-eye-slash" : "bi bi-eye";
        btn.setAttribute("aria-label", isPwd ? "Ocultar contraseña" : "Mostrar contraseña");
      });
    });
  }

  // Botón "Limpiar" en formularios de filtro
  function initFilterReset() {
    document.querySelectorAll("[data-filter-reset]").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var form = btn.closest("form");
        if (!form) return;
        form.querySelectorAll("select, input[type=text], input[type=search], input[type=date]").forEach(function (el) {
          if (el.tagName === "SELECT") el.selectedIndex = 0;
          else el.value = "";
        });
        form.querySelectorAll("[data-client-picker]").forEach(function (input) {
          var hidden = document.getElementById(input.dataset.clientPickerTarget);
          if (hidden) hidden.value = "";
        });
        form.submit();
      });
    });
  }

  // Prevención de doble envío: deshabilita el submit y muestra spinner
  function initSubmitGuard() {
    document.querySelectorAll("form").forEach(function (form) {
      // No tocar formularios que usan modal — el modal ya gestiona el flujo
      if (form.hasAttribute("data-confirm")) return;
      // No tocar forms GET (filtros)
      if ((form.getAttribute("method") || "GET").toUpperCase() === "GET") return;

      form.addEventListener("submit", function () {
        // Permitir validación HTML5 antes de bloquear
        if (typeof form.checkValidity === "function" && !form.checkValidity()) return;

        form.querySelectorAll('button[type="submit"]').forEach(function (btn) {
          if (btn.disabled) return;
          btn.dataset.originalHtml = btn.innerHTML;
          btn.disabled = true;
          btn.innerHTML =
            '<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>' +
            (btn.dataset.loadingText || "Guardando…");
        });
      });
    });
  }

  // Selector de cliente por búsqueda server-side: al escribir, hace fetch
  // a data-client-picker-url?q=... y muestra sugerencias reales (substring
  // en nombre o identificación, no solo prefijo como un <datalist>).
  //   <input data-client-picker data-client-picker-target="cliente_id"
  //          data-client-picker-url="/admin/clientes/buscar">
  //   <input type="hidden" id="cliente_id">
  //   <ul class="wm-client-picker-results">
  function initClientPicker() {
    document.querySelectorAll("[data-client-picker]").forEach(function (input) {
      var hidden = document.getElementById(input.dataset.clientPickerTarget);
      var url = input.dataset.clientPickerUrl;
      var results = input.parentElement.querySelector(".wm-client-picker-results");
      if (!hidden || !url || !results) return;

      var debounceTimer = null;
      var lastQuery = "";

      function hideResults() {
        results.classList.add("d-none");
        results.innerHTML = "";
      }

      function selectCliente(cliente) {
        input.value = cliente.nombre + " — " + cliente.identificador;
        var previo = hidden.value;
        hidden.value = cliente.id;
        hideResults();
        if (input.hasAttribute("data-client-picker-autosubmit") && hidden.value !== previo) {
          input.form.submit();
        }
      }

      function renderResults(clientes) {
        results.innerHTML = "";
        if (!clientes.length) {
          hideResults();
          return;
        }
        clientes.forEach(function (cliente) {
          var li = document.createElement("li");
          li.className = "list-group-item list-group-item-action";
          li.style.cursor = "pointer";
          li.textContent = cliente.nombre + " — " + cliente.identificador;
          li.addEventListener("mousedown", function (e) {
            e.preventDefault();
            selectCliente(cliente);
          });
          results.appendChild(li);
        });
        results.classList.remove("d-none");
      }

      input.addEventListener("input", function () {
        hidden.value = "";
        var q = input.value.trim();
        clearTimeout(debounceTimer);
        if (q.length < 2) {
          hideResults();
          return;
        }
        debounceTimer = setTimeout(function () {
          lastQuery = q;
          fetch(url + "?q=" + encodeURIComponent(q))
            .then(function (r) { return r.json(); })
            .then(function (clientes) {
              if (q === lastQuery) renderResults(clientes);
            })
            .catch(function () { hideResults(); });
        }, 250);
      });

      input.addEventListener("blur", function () {
        setTimeout(hideResults, 150);
      });
    });
  }

  // Auto-focus al primer input de un formulario marcado con [data-autofocus]
  function initAutoFocus() {
    document.querySelectorAll("[data-autofocus]").forEach(function (form) {
      var first = form.querySelector("input:not([type=hidden]), select, textarea");
      if (first && !first.disabled && first.offsetParent !== null) first.focus();
    });
  }
})();
