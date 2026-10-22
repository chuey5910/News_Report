/* วางพิกัดชุดเดียวจาก Google Maps (เช่น "18.78830, 98.98530") ในช่องละติจูด
   แล้วแยกใส่ช่องละติจูด/ลองติจูดให้เอง — ผู้กรอกไม่ต้องตัดตัวเลขเอง */
(function () {
  var lat = document.getElementById("coord-lat");
  var lng = document.getElementById("coord-lng");
  if (!lat || !lng) return;

  function split(el) {
    var parts = (el.value || "").split(/[,\s]+/).filter(function (s) {
      return s !== "";
    });
    if (parts.length >= 2 && !isNaN(parseFloat(parts[0])) && !isNaN(parseFloat(parts[1]))) {
      lat.value = parts[0];
      lng.value = parts[1];
    }
  }

  [lat, lng].forEach(function (el) {
    el.addEventListener("paste", function () {
      setTimeout(function () {
        split(el);
      }, 0);
    });
    el.addEventListener("change", function () {
      split(el);
    });
  });
})();
