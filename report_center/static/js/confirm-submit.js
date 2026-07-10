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

  function makeRow(label, value) {
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
    return { row: row, valueEl: valueEl };
  }

  function openModalFor(form) {
    body.innerHTML = "";
    var checkboxGroups = {}; // name -> { valueEl, values: [] }
    var fields = form.querySelectorAll("input[name], select[name], textarea[name]");

    fields.forEach(function (el) {
      if (el.name === "csrf_token" || el.type === "hidden") return;
      if (el.offsetParent === null) return; // skip fields hidden by conditional show/hide

      if (el.type === "checkbox") {
        var group = checkboxGroups[el.name];
        if (!group) {
          var built = makeRow(el.dataset.groupLabel || el.name, "");
          built.valueEl.classList.add("empty");
          body.appendChild(built.row);
          group = checkboxGroups[el.name] = { valueEl: built.valueEl, values: [] };
        }
        if (el.checked) {
          group.values.push(el.dataset.optionLabel || el.value);
          group.valueEl.textContent = group.values.join(", ");
          group.valueEl.classList.remove("empty");
        }
        return;
      }

      var label = el.dataset.label || el.name;
      var value = fieldValueText(el).trim();
      body.appendChild(makeRow(label, value).row);
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
