/* ช่องปักหมุดตำแหน่งในฟอร์มบันทึกข่าว — คลิก/แตะบนแผนที่เพื่อกำหนดพิกัด
   เว้นว่างได้ ระบบจะปักหมุดที่ตัวเมืองของจังหวัดที่เลือกให้เอง */
(function () {
  var el = document.getElementById("pick-map");
  if (!el || typeof L === "undefined") return;

  var latInput = document.getElementsByName(el.dataset.latInput)[0];
  var lngInput = document.getElementsByName(el.dataset.lngInput)[0];
  var status = document.getElementById("pick-map-status");
  var clearBtn = document.getElementById("pick-map-clear");
  if (!latInput || !lngInput) return;

  var provinceCoords = {};
  try {
    provinceCoords = JSON.parse(el.dataset.provinceCoords || "{}");
  } catch (e) {
    provinceCoords = {};
  }

  var map = L.map(el, { zoomControl: true, scrollWheelZoom: false });
  L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 18, attribution: "Tiles &copy; Esri" }
  ).addTo(map);
  L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 18 }
  ).addTo(map);

  var marker = null;

  function showStatus(lat, lng) {
    if (!status) return;
    status.textContent = lat == null
      ? "ยังไม่ได้ปักหมุด — จะใช้ตำแหน่งตัวเมืองของจังหวัดที่เลือก"
      : "พิกัดที่ปัก: " + lat.toFixed(5) + ", " + lng.toFixed(5);
  }

  function setPoint(lat, lng, fly) {
    latInput.value = lat.toFixed(6);
    lngInput.value = lng.toFixed(6);
    if (marker) {
      marker.setLatLng([lat, lng]);
    } else {
      marker = L.marker([lat, lng], { draggable: true }).addTo(map);
      marker.on("dragend", function () {
        var pos = marker.getLatLng();
        setPoint(pos.lat, pos.lng, false);
      });
    }
    if (fly) map.setView([lat, lng], Math.max(map.getZoom(), 13));
    showStatus(lat, lng);
  }

  function clearPoint() {
    latInput.value = "";
    lngInput.value = "";
    if (marker) {
      map.removeLayer(marker);
      marker = null;
    }
    showStatus(null);
  }

  // ตำแหน่งเริ่มต้น: พิกัดที่บันทึกไว้ > จังหวัดที่เลือกอยู่ > ภาพรวมภาคเหนือ
  var startLat = parseFloat(latInput.value);
  var startLng = parseFloat(lngInput.value);
  if (!isNaN(startLat) && !isNaN(startLng)) {
    map.setView([startLat, startLng], 13);
    setPoint(startLat, startLng, false);
  } else {
    var checked = document.querySelector('input[name="' + el.dataset.provinceSelect + '"]:checked');
    var coords = checked ? provinceCoords[checked.value] : null;
    map.setView(coords || [17.8, 99.6], coords ? 10 : 7);
    showStatus(null);
  }

  map.on("click", function (ev) {
    setPoint(ev.latlng.lat, ev.latlng.lng, false);
  });
  if (clearBtn) clearBtn.addEventListener("click", clearPoint);

  // เลือกจังหวัดแล้วเลื่อนแผนที่ไปให้ ถ้ายังไม่ได้ปักหมุดเอง
  document.querySelectorAll('input[name="' + el.dataset.provinceSelect + '"]').forEach(function (radio) {
    radio.addEventListener("change", function () {
      var coords = provinceCoords[radio.value];
      if (coords && !marker) map.setView(coords, 10);
    });
  });

  // แผนที่ถูกสร้างตอนช่องยังถูกซ่อน/ยังจัดหน้าไม่เสร็จ ต้องบอกให้วัดขนาดใหม่
  setTimeout(function () {
    map.invalidateSize();
  }, 250);
})();
