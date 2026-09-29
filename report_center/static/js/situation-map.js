/* แผนที่สถานการณ์ — ปักหมุดจากรายงานที่บันทึกไว้
   หมุดวงกลม = จังหวัด (เลขคือจำนวนรายงาน) | หมุดหยดน้ำ = รายงานที่จิ้มพิกัดไว้เอง
   สีหมุด = ระดับสถานการณ์ที่รุนแรงที่สุดในจุดนั้น (เขียว ปกติ / เหลือง เฝ้าระวัง / แดง มีผลกระทบ) */
(function () {
  var el = document.getElementById("situation-map");
  if (!el || typeof L === "undefined") return;

  var points = [];
  var typeLabels = {};
  try {
    points = JSON.parse(el.dataset.points || "[]");
    typeLabels = JSON.parse(el.dataset.typeLabels || "{}");
  } catch (e) {
    points = [];
  }

  // ขอบเขตประเทศไทย — เลื่อน/ซูมออกนอกนี้ไม่ได้ จึงไม่มีการโหลดภาพแผนที่ส่วนอื่นของโลก
  var THAILAND = L.latLngBounds([5.0, 96.5], [21.0, 106.5]);
  var map = L.map(el, {
    zoomControl: true,
    scrollWheelZoom: true,
    minZoom: 6,
    maxZoom: 17,
    maxBounds: THAILAND,
    maxBoundsViscosity: 1,
  });
  var satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 17, minZoom: 6, bounds: THAILAND, updateWhenIdle: true, keepBuffer: 1,
      attribution: el.dataset.tilesAttribution || "" }
  );
  var streets = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 17,
    minZoom: 6,
    bounds: THAILAND,
    updateWhenIdle: true,
    keepBuffer: 1,
    attribution: "&copy; OpenStreetMap",
  });
  // ชื่อถนน/สถานที่วางทับภาพดาวเทียม เพื่อให้อ่านตำแหน่งได้ (แบบ Hybrid)
  var labels = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 17, minZoom: 6, bounds: THAILAND, updateWhenIdle: true, keepBuffer: 1 }
  );
  satellite.addTo(map);
  L.control
    .layers(
      { "ภาพดาวเทียม": satellite, "แผนที่ถนน": streets },
      { "ชื่อถนน/สถานที่": labels },   // ชั้นเสริม เปิดเมื่อต้องการ (โหลดภาพเพิ่มอีกเท่าตัว)
      { position: "topright" }
    )
    .addTo(map);

  function escapeHtml(text) {
    return String(text == null ? "" : text).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function popupHtml(point) {
    var head =
      '<div class="pin-head"><strong>' +
      escapeHtml(point.label) +
      "</strong>" +
      '<span class="pin-level" style="background:' + escapeHtml(point.color) + '">' +
      escapeHtml(point.level) +
      "</span></div>";
    if (!point.exact) {
      head += '<div class="pin-note">หมุดระดับจังหวัด — ไม่ใช่จุดเกิดเหตุจริง</div>';
    }
    var rows = point.reports
      .map(function (r) {
        return (
          '<a class="pin-report" href="' + escapeHtml(r.u) + '">' +
          '<span class="pin-type type-' + escapeHtml(r.k) + '">' + escapeHtml(typeLabels[r.k] || r.k) + "</span>" +
          '<span class="pin-title">' + escapeHtml(r.t) + "</span>" +
          (r.w ? '<span class="pin-when">' + escapeHtml(r.w) + " น.</span>" : "") +
          '<span class="pin-place">' + escapeHtml(r.p) + "</span>" +
          "</a>"
        );
      })
      .join("");
    var shown = point.reports.length;
    var more =
      point.total > shown
        ? '<div class="pin-note">และอีก ' + (point.total - shown) + " รายการ</div>"
        : "";
    return '<div class="pin-popup">' + head + rows + more + "</div>";
  }

  var markers = [];
  points.forEach(function (point) {
    var marker;
    if (point.exact) {
      marker = L.circleMarker([point.lat, point.lng], {
        className: "exact-pin",
        radius: 9,
        color: "#fff",
        weight: 2,
        fillColor: point.color,
        fillOpacity: 0.95,
      });
    } else {
      var count = point.total;
      var size = count >= 50 ? 52 : count >= 20 ? 46 : count >= 5 ? 40 : 34;
      marker = L.marker([point.lat, point.lng], {
        icon: L.divIcon({
          className: "province-pin-wrap",
          html:
            '<div class="province-pin" style="background:' + point.color + "; width:" + size +
            "px; height:" + size + 'px">' + count + "</div>",
          iconSize: [size, size],
          iconAnchor: [size / 2, size / 2],
        }),
      });
    }
    marker.bindPopup(popupHtml(point), { maxWidth: 340, maxHeight: 320 });
    marker.addTo(map);
    markers.push(marker);
  });

  if (markers.length) {
    map.fitBounds(L.featureGroup(markers).getBounds().pad(0.25));
    if (map.getZoom() > 11) map.setZoom(11);
  } else {
    map.setView([17.8, 99.6], 7); // ภาพรวม 17 จังหวัดภาคเหนือ
  }

  // เปลี่ยนตัวกรองแล้วส่งฟอร์มทันที ไม่ต้องกดปุ่มกรอง
  var filters = document.getElementById("map-filters");
  if (filters) {
    filters.querySelectorAll("select").forEach(function (select) {
      select.addEventListener("change", function () {
        filters.submit();
      });
    });
  }
})();
