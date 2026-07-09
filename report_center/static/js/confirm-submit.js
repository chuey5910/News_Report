(function () {
  var modal = document.getElementById("confirm-modal");
  if (!modal) return;

  var body = document.getElementById("confirm-modal-body");
  var cancelBtn = document.getElementById("confirm-modal-cancel");
  var submitBtn = document.getElementById("confirm-modal-submit");
  var activeForm = null;

  function fieldValueText(el) {
    if (el.tagName === "SELECT") {
      var opt = el.options[el.selectedIndex];
      return opt ? opt.text : "";
    }
    return el.value;
  }

  function openModalFor(form) {
    body.innerHTML = "";
    var fields = form.querySelectorAll("input[name], select[name], textarea[name]");
    fields.forEach(function (el) {
      if (el.name === "csrf_token" || el.type === "hidden") return;
      if (el.offsetParent === null) return; // skip fields hidden by conditional show/hide
      var label = el.dataset.label || el.name;
      var value = fieldValueText(el).trim();

      var row = document.createElement("div");
      row.className = "confirm-row";

      var labelEl = document.createElement("div");
      labelEl.className = "confirm-label";
      labelEl.textContent = label;

      var valueEl = document.createElement("div");
      valueEl.className = "confirm-value";
      valueEl.textContent = value || "(ไม่ได้กรอก)";
      if (!value) valueEl.classList.add("empty");

      row.appendChild(labelEl);
      row.appendChild(valueEl);
      body.appendChild(row);
    });

    activeForm = form;
    modal.classList.add("open");
  }

  document.querySelectorAll("form.confirm-before-submit").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (form.dataset.confirmed === "true") {
        return;
      }
      e.preventDefault();
      openModalFor(form);
    });
  });

  cancelBtn.addEventListener("click", function () {
    modal.classList.remove("open");
    activeForm = null;
  });

  modal.addEventListener("click", function (e) {
    if (e.target === modal) {
      modal.classList.remove("open");
      activeForm = null;
    }
  });

  submitBtn.addEventListener("click", function () {
    if (!activeForm) return;
    activeForm.dataset.confirmed = "true";
    modal.classList.remove("open");
    activeForm.submit();
  });
})();
