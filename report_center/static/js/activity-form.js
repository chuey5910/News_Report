document.addEventListener("DOMContentLoaded", function () {
  var initialData = {};
  var dataEl = document.getElementById("activity-form-data");
  if (dataEl) {
    try {
      initialData = JSON.parse(dataEl.textContent);
    } catch (e) {
      initialData = {};
    }
  }

  setupToggle("permit_status", "มีการขออนุญาต", "permit-detail-wrapper");
  setupToggle("overnight_equipment_status", "มี", "equipment-detail-wrapper");
  setupToggle("vehicle_status", "มี", "vehicle-section-wrapper");

  setupLeaderFields(initialData.leaders || []);
  setupVehicleFields(initialData.vehicles || []);

  function setupToggle(selectName, showValue, wrapperId) {
    var select = document.querySelector('select[name="' + selectName + '"]');
    var wrapper = document.getElementById(wrapperId);
    if (!select || !wrapper) return;

    function update() {
      wrapper.hidden = select.value !== showValue;
    }

    select.addEventListener("change", update);
    update();
  }

  function setupLeaderFields(existingNames) {
    var countSelect = document.querySelector('select[name="leader_count"]');
    var container = document.getElementById("leader-fields-container");
    if (!countSelect || !container) return;

    function render() {
      var count = parseInt(countSelect.value, 10) || 0;
      container.innerHTML = "";
      for (var i = 0; i < count; i++) {
        var wrap = document.createElement("div");
        wrap.className = "form-field";

        var label = document.createElement("label");
        label.textContent = "ชื่อ-นามสกุล แกนนำ คนที่ " + (i + 1);

        var input = document.createElement("input");
        input.type = "text";
        input.name = "leader_name";
        input.dataset.label = "แกนนำ คนที่ " + (i + 1);
        if (existingNames[i]) input.value = existingNames[i];

        wrap.appendChild(label);
        wrap.appendChild(input);
        container.appendChild(wrap);
      }
    }

    countSelect.addEventListener("change", function () {
      existingNames = [];
      render();
    });
    render();
  }

  function setupVehicleFields(existingVehicles) {
    var countSelect = document.querySelector('select[name="vehicle_count"]');
    var container = document.getElementById("vehicle-fields-container");
    if (!countSelect || !container) return;

    function makeField(labelText, name, value, index) {
      var wrap = document.createElement("div");
      wrap.className = "form-field";

      var label = document.createElement("label");
      label.textContent = labelText;

      var input = document.createElement("input");
      input.type = "text";
      input.name = name;
      input.dataset.label = labelText + " (คันที่ " + (index + 1) + ")";
      if (value) input.value = value;

      wrap.appendChild(label);
      wrap.appendChild(input);
      return wrap;
    }

    function render() {
      var count = parseInt(countSelect.value, 10) || 0;
      container.innerHTML = "";
      for (var i = 0; i < count; i++) {
        var row = existingVehicles[i] || {};

        var group = document.createElement("div");
        group.className = "vehicle-group";

        var heading = document.createElement("div");
        heading.className = "vehicle-group-heading";
        heading.textContent = "ยานพาหนะคันที่ " + (i + 1);
        group.appendChild(heading);

        var grid = document.createElement("div");
        grid.className = "form-grid";
        grid.appendChild(makeField("ประเภทรถยนต์", "vehicle_type", row.vehicle_type, i));
        grid.appendChild(makeField("หมายเลขทะเบียน", "vehicle_plate", row.plate_number, i));
        grid.appendChild(makeField("จังหวัด", "vehicle_province", row.province, i));
        grid.appendChild(makeField("สี", "vehicle_color", row.color, i));
        group.appendChild(grid);

        container.appendChild(group);
      }
    }

    countSelect.addEventListener("change", function () {
      existingVehicles = [];
      render();
    });
    render();
  }
});
