/* ฟอร์มรายงานข่าว — เรนเดอร์ช่องกรอกแบบไดนามิกตามจำนวนที่เลือก และโชว์/ซ่อนส่วนที่มีเงื่อนไข
   อ่าน config จาก <script id="activity-form-data" type="application/json"> ที่ view สร้างให้:
   { toggles: [{select, value, wrappers:[id]}],
     sections: [{count, container, heading, fields:[{name,label}], rows:[{...}]}] } */
document.addEventListener("DOMContentLoaded", function () {
  var config = {};
  var dataEl = document.getElementById("activity-form-data");
  if (dataEl) {
    try {
      config = JSON.parse(dataEl.textContent);
    } catch (e) {
      config = {};
    }
  }

  (config.toggles || []).forEach(function (toggle) {
    var select = document.querySelector('select[name="' + toggle.select + '"]');
    if (!select) return;

    function update() {
      var show = select.value === toggle.value;
      toggle.wrappers.forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.hidden = !show;
      });
    }

    select.addEventListener("change", update);
    update();
  });

  (config.sections || []).forEach(function (section) {
    var countSelect = document.querySelector('select[name="' + section.count + '"]');
    var container = document.getElementById(section.container);
    if (!countSelect || !container) return;

    var rows = section.rows || [];

    function makeField(labelText, name, value, dataLabel) {
      var wrap = document.createElement("div");
      wrap.className = "form-field";

      var label = document.createElement("label");
      label.textContent = labelText;

      var input = document.createElement("input");
      input.type = "text";
      input.name = name;
      input.dataset.label = dataLabel;
      if (value) input.value = value;

      wrap.appendChild(label);
      wrap.appendChild(input);
      return wrap;
    }

    function render() {
      var count = parseInt(countSelect.value, 10) || 0;
      container.innerHTML = "";
      for (var i = 0; i < count; i++) {
        var row = rows[i] || {};
        var suffix = " (" + section.heading + " " + (i + 1) + ")";

        if (section.fields.length === 1) {
          // ช่องเดียวต่อรายการ (เช่น ชื่อแกนนำในฟอร์มข่าวล่วงหน้า) — ไม่ต้องมีกรอบกลุ่ม
          var field = section.fields[0];
          container.appendChild(
            makeField(
              field.label + " " + section.heading + " " + (i + 1),
              field.name,
              row[field.name] || "",
              field.label + suffix
            )
          );
        } else {
          var group = document.createElement("div");
          group.className = "field-group";

          var heading = document.createElement("div");
          heading.className = "field-group-heading";
          heading.textContent = section.heading + " " + (i + 1);
          group.appendChild(heading);

          var grid = document.createElement("div");
          grid.className = "form-grid field-group-grid";
          section.fields.forEach(function (field) {
            grid.appendChild(makeField(field.label, field.name, row[field.name] || "", field.label + suffix));
          });
          group.appendChild(grid);

          container.appendChild(group);
        }
      }
    }

    countSelect.addEventListener("change", function () {
      rows = [];
      render();
    });
    render();
  });
});
