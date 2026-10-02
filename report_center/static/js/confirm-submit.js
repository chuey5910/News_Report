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
    if (el.type === "file") {       // ช่องแนบรูป: บอกจำนวน ไม่ใช่ path ของไฟล์
      var n = el.files ? el.files.length : 0;
      return n ? "แนบรูปใหม่ " + n + " รูป" : "";
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

  /** ช่องติ๊กที่ให้ "ตัดสินใจในหน้าต่างยืนยัน" (เช่น ส่งการ์ดเข้าไลน์)
      ตัว input จริงถูกซ่อนไว้ในฟอร์ม ที่นี่สร้างช่องติ๊กจริงผูกค่ากันไว้ */
  function appendAskRow(field) {
    var row = document.createElement("div");
    row.className = "confirm-row confirm-ask";

    var label = document.createElement("label");
    label.className = "confirm-ask-label";
    var box = document.createElement("input");
    box.type = "checkbox";
    box.checked = field.checked;
    var text = document.createElement("span");
    text.textContent = field.dataset.askInConfirm;
    label.appendChild(box);
    label.appendChild(text);
    row.appendChild(label);

    if (field.dataset.askHint) {
      var hint = document.createElement("div");
      hint.className = "confirm-ask-hint";
      hint.textContent = field.dataset.askHint;
      row.appendChild(hint);
    }
    box.addEventListener("change", function () {
      field.checked = box.checked;
      row.classList.toggle("on", box.checked);
    });
    row.classList.toggle("on", box.checked);
    body.appendChild(row);
  }

  function openModalFor(form) {
    body.innerHTML = "";
    var checkboxGroups = {}; // name -> { valueEl, values: [] }
    var fields = form.querySelectorAll("input[name], select[name], textarea[name]");

    fields.forEach(function (el) {
      if (el.name === "csrf_token" || el.type === "hidden") return;
      // ช่องเลือกไฟล์ถูกซ่อนไว้ (ใช้ปุ่มสวยแทน) แต่ยังต้องโชว์ในสรุปว่าแนบกี่รูป
      if (el.offsetParent === null && el.type !== "file") return; // skip fields hidden by conditional show/hide

      if (el.type === "checkbox" || el.type === "radio") {
        var group = checkboxGroups[el.name];
        if (!group) {
          var built = makeRow(el.dataset.groupLabel || el.name, "");
          built.valueEl.classList.add("empty");
          // ช่องติ๊กเดี่ยวแบบ "ทำ/ไม่ทำ" บอกข้อความตอนไม่ติ๊กได้ ("(ไม่ได้กรอก)" อ่านไม่รู้เรื่อง)
          if (el.dataset.uncheckedLabel) built.valueEl.textContent = el.dataset.uncheckedLabel;
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

    form.querySelectorAll("[data-ask-in-confirm]").forEach(appendAskRow);

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
