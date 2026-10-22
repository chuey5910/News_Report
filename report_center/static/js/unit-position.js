/* ช่องตำแหน่งแสดงเป็นชื่อระดับเต็มตามสังกัดที่เลือก — "เจ้าหน้าที่ ส.จว.ตาก" / "หน.ส.จว.ตาก"
   ใช้ทั้งหน้าสมัครสมาชิก (radio) และหน้าจัดการผู้ใช้ (select ในแต่ละแถว)
   โครง: กล่อง [data-unit-position] มี select/radio ชื่อ unit กับ position อยู่ข้างใน */
(function () {
  function levelLabel(position, unit) {
    if (!unit) return position === "chief" ? "หัวหน้า" : "เจ้าหน้าที่";
    return position === "chief" ? "หน." + unit : "เจ้าหน้าที่ " + unit;
  }

  function wire(box) {
    var unitEl = box.querySelector('select[name="unit"]');
    if (!unitEl) return;
    function refresh() {
      var unit = unitEl.value;
      box.querySelectorAll('select[name="position"] option').forEach(function (opt) {
        opt.textContent = levelLabel(opt.value, unit);
      });
      box.querySelectorAll('input[name="position"]').forEach(function (radio) {
        var span = radio.parentNode.querySelector("span");
        if (span) span.textContent = levelLabel(radio.value, unit);
      });
    }
    unitEl.addEventListener("change", refresh);
    refresh();
  }

  document.querySelectorAll("[data-unit-position]").forEach(wire);
})();
