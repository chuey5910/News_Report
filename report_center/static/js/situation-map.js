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

  // ใช้แผนที่ถนนแบบเดียว (มีชื่อถนน/สถานที่/จังหวัดเป็นภาษาไทยอยู่แล้ว)
  // ไม่มีภาพดาวเทียมและไม่มีปุ่มสลับชั้น เพื่อไม่ให้ต้องดาวน์โหลดภาพหลายชุด
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 17,
    minZoom: 6,
    bounds: THAILAND,
    updateWhenIdle: true,
    keepBuffer: 1,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  // ---------- เส้นขอบเขตจังหวัด + ชื่อจังหวัด ----------
  var myProvinces = [];
  try {
    myProvinces = JSON.parse(el.dataset.myProvinces || "[]");
  } catch (e) {
    myProvinces = [];
  }

  /** จุดวางป้ายชื่อ: หาจุด "ลึกที่สุด" ในรูปจังหวัด ไม่ใช่ค่าเฉลี่ยของขอบ
      (จังหวัดรูปยาวโค้งอย่างแม่ฮ่องสอน ค่าเฉลี่ยอาจตกนอกพื้นที่) */
  function pointInRing(ring, x, y) {
    var hit = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) hit = !hit;
    }
    return hit;
  }

  function labelPoint(feature) {
    var polys = feature.geometry.type === "Polygon"
      ? [feature.geometry.coordinates]
      : feature.geometry.coordinates;
    // ใช้รูปหลายเหลี่ยมวงนอกที่มีจุดมากที่สุด (คือส่วนแผ่นดินหลักของจังหวัด)
    var ring = polys.map(function (poly) { return poly[0]; })
                    .sort(function (a, b) { return b.length - a.length; })[0];
    var xs = ring.map(function (p) { return p[0]; });
    var ys = ring.map(function (p) { return p[1]; });
    var minX = Math.min.apply(null, xs), maxX = Math.max.apply(null, xs);
    var minY = Math.min.apply(null, ys), maxY = Math.max.apply(null, ys);

    function inside(x, y) {
      return pointInRing(ring, x, y);
    }
    function edgeDist(x, y) {
      var best = Infinity;
      for (var i = 0; i < ring.length; i++) {
        var dx = ring[i][0] - x, dy = ring[i][1] - y;
        var d = dx * dx + dy * dy;
        if (d < best) best = d;
      }
      return best;
    }

    var best = null, bestScore = -1, steps = 14;
    for (var a = 1; a < steps; a++) {
      for (var b = 1; b < steps; b++) {
        var x = minX + ((maxX - minX) * a) / steps;
        var y = minY + ((maxY - minY) * b) / steps;
        if (!inside(x, y)) continue;
        var score = edgeDist(x, y);
        if (score > bestScore) { bestScore = score; best = [y, x]; }
      }
    }
    return {
      latlng: best || [(minY + maxY) / 2, (minX + maxX) / 2],
      bounds: L.latLngBounds([minY, minX], [maxY, maxX]),
      ring: ring,
    };
  }

  var labels = [];

  function overlaps(a, b) {
    return a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
  }

  /** กรอบของหมุดรายงานบนจอ — ชื่อจังหวัดจะได้หลบไม่ไปอยู่ใต้หมุด */
  function pinBoxes() {
    var out = [];
    markers.forEach(function (m) {
      if (!m.getElement || !m.getElement()) return;
      var p = map.latLngToContainerPoint(m.getLatLng());
      var el = m.getElement();
      var w = el.offsetWidth || 24;
      var h = el.offsetHeight || 24;
      out.push({
        left: p.x - w / 2 - 3, right: p.x + w / 2 + 3,
        top: p.y - h / 2 - 3, bottom: p.y + h / 2 + 3,
      });
    });
    return out;
  }

  /** ปรับขนาดตัวอักษรให้ชื่อจังหวัดอยู่ในเขตจังหวัดพอดี ไม่ตัดคำ ไม่ล้นขอบ
      ถ้าเล็กสุดแล้วยังล้น หรือไปทับชื่อจังหวัดอื่น จะซ่อนป้ายนั้นไว้ (ซูมเข้าก็เห็น) */
  function fitLabels() {
    var zoom = map.getZoom();
    var pins = pinBoxes();
    var placed = [];
    labels.forEach(function (item) {
      var root = item.marker.getElement();
      var node = root && root.firstChild;
      if (!node) return;
      if (zoom > 12) {           // ซูมถึงระดับถนนแล้ว ไม่ต้องมีชื่อจังหวัดมาเกะกะ
        node.style.display = "none";
        return;
      }
      // ความกว้างของจังหวัดนี้บนจอ (พิกเซล) — ชื่อต้องแคบกว่านี้
      var nw = map.latLngToLayerPoint(item.bounds.getNorthWest());
      var se = map.latLngToLayerPoint(item.bounds.getSouthEast());
      var boxWidth = Math.abs(se.x - nw.x) * 0.92;
      node.style.display = "block";
      var size = 15;
      node.style.fontSize = size + "px";
      while (node.offsetWidth > boxWidth && size > 9) {
        size -= 1;
        node.style.fontSize = size + "px";
      }
      // เล็กสุดแล้วยังล้นขอบจังหวัด (ซูมออกไกลมาก) — ซ่อนไว้
      if (node.offsetWidth > boxWidth) {
        node.style.display = "none";
        return;
      }
      // กันชื่อจังหวัดซ้อนกันหรือไปอยู่ใต้หมุดจนอ่านไม่ออก
      // จังหวัดใหญ่ได้สิทธิ์ก่อน (เรียงไว้แล้วตอนสร้างป้าย) ถ้าทับก็ขยับขึ้น/ลงในเขตจังหวัดเดิม
      var center = map.latLngToContainerPoint(item.latlng);
      var half = node.offsetWidth / 2 + 2;
      var halfH = node.offsetHeight / 2 + 2;
      var step = node.offsetHeight + 6;
      function boxAt(dy) {
        var y = center.y + dy;
        // ขยับแล้วจุดกลางชื่อต้องยังอยู่ในเขตจังหวัดจริง (ไม่ใช่แค่ในกรอบสี่เหลี่ยม)
        var at = map.containerPointToLatLng(L.point(center.x, y));
        if (dy !== 0 && !pointInRing(item.ring, at.lng, at.lat)) return null;
        return { left: center.x - half, right: center.x + half, top: y - halfH, bottom: y + halfH };
      }
      function hits(box, list) {
        for (var i = 0; i < list.length; i++) {
          if (overlaps(box, list[i])) return true;
        }
        return false;
      }

      // ลำดับความสำคัญ: ไม่ทับชื่ออื่นและไม่ทับหมุด > ไม่ทับชื่ออื่น (ยอมให้หมุดบังบางส่วน)
      var offsets = [0, step, -step, step * 2, -step * 2];
      var spot = null;
      var fallback = null;
      for (var s = 0; s < offsets.length; s++) {
        var box = boxAt(offsets[s]);
        if (!box || hits(box, placed)) continue;
        if (!hits(box, pins)) { spot = { box: box, dy: offsets[s] }; break; }
        if (!fallback) fallback = { box: box, dy: offsets[s] };
      }
      spot = spot || fallback;
      if (!spot) {           // ทับชื่อจังหวัดอื่นทุกตำแหน่ง — ซ่อนไว้ ซูมเข้าก็เห็น
        node.style.display = "none";
        return;
      }
      node.style.marginTop = spot.dy + "px";
      placed.push(spot.box);
    });
  }

  if (el.dataset.provincesUrl) {
    fetch(el.dataset.provincesUrl)
      .then(function (res) { return res.json(); })
      .then(function (geo) {
        // เส้นขาวรองข้างใต้ ทำให้เส้นขอบเขตไม่จมหายไปกับรายละเอียดของแผนที่ถนน
        L.geoJSON(geo, {
          interactive: false,
          style: { color: "#ffffff", weight: 5, opacity: 0.85, fill: false },
        }).addTo(map);
        L.geoJSON(geo, {
          interactive: false,
          style: { color: "#1e3a8a", weight: 2.6, opacity: 0.95, fill: false },
        }).addTo(map);
        // ระบายสีจางเฉพาะจังหวัดในพื้นที่รับผิดชอบ
        L.geoJSON(geo, {
          interactive: false,
          filter: function (f) { return myProvinces.indexOf(f.properties.name) !== -1; },
          style: { color: "#1e3a8a", weight: 2.6, opacity: 0.95,
                   fillColor: "#6366f1", fillOpacity: 0.10 },
        }).addTo(map);

        geo.features.forEach(function (f) {
          if (myProvinces.indexOf(f.properties.name) === -1) return;
          var spot = labelPoint(f);
          var marker = L.marker(spot.latlng, {
            interactive: false,
            keyboard: false,
            zIndexOffset: -1000,   // ให้หมุดรายงานอยู่บนชื่อจังหวัดเสมอ
            icon: L.divIcon({
              className: "pv-label",
              html: '<span class="pv-name">' + escapeHtml(f.properties.name) + "</span>",
              iconSize: [0, 0],
              iconAnchor: [0, 0],
            }),
          }).addTo(map);
          var size = spot.bounds.getNorth() - spot.bounds.getSouth();
          size *= spot.bounds.getEast() - spot.bounds.getWest();
          labels.push({
            marker: marker, bounds: spot.bounds, latlng: spot.latlng, ring: spot.ring, area: size,
          });
        });
        // จังหวัดใหญ่ได้สิทธิ์แสดงชื่อก่อน เวลาชื่อสองจังหวัดจะทับกัน
        labels.sort(function (a, b) { return b.area - a.area; });
        fitLabels();
        map.on("zoomend", fitLabels);
      })
      .catch(function () {
        /* ไม่มีเส้นขอบเขตก็ยังใช้แผนที่ได้ปกติ */
      });
  }

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
    marker.bindPopup(popupHtml(point), {
      maxWidth: 340,
      maxHeight: 320,
      autoPan: false,     // เลื่อนเองด้านล่าง (ของ Leaflet ไม่รู้ว่ามีแถบค้นหา/แถบสีทับอยู่)
    });
    marker.addTo(map);
    markers.push(marker);
  });

  if (markers.length) {
    map.fitBounds(L.featureGroup(markers).getBounds().pad(0.25));
    if (map.getZoom() > 11) map.setZoom(11);
  } else {
    map.setView([17.8, 99.6], 7); // ภาพรวม 17 จังหวัดภาคเหนือ
  }

  /** เปิดกล่องรายละเอียดแล้วเลื่อนแผนที่ให้กล่องพ้นจากแถบค้นหา/แถบสี/ขอบจอเอง
      (แถบค้นหาอยู่บนในจอคอม แต่ย้ายไปอยู่ล่างในมือถือ จึงวัดตำแหน่งจริงทุกครั้ง) */
  function overlayGaps(mapRect) {
    var top = 0;
    var bottom = 0;
    ["#map-filters", ".map-legend", ".map-count"].forEach(function (sel) {
      var node = document.querySelector(sel);
      if (!node || !node.offsetHeight) return;
      var r = node.getBoundingClientRect();
      if ((r.top + r.bottom) / 2 < (mapRect.top + mapRect.bottom) / 2) {
        top = Math.max(top, r.bottom - mapRect.top);
      } else {
        bottom = Math.max(bottom, mapRect.bottom - r.top);
      }
    });
    return { top: top, bottom: bottom };
  }

  function nudgePopupIntoView(popup) {
    var node = popup.getElement();
    if (!node) return;
    var mapRect = map.getContainer().getBoundingClientRect();
    var gaps = overlayGaps(mapRect);
    var pad = 10;
    var limit = {
      top: mapRect.top + gaps.top + pad,
      bottom: mapRect.bottom - gaps.bottom - pad,
      left: mapRect.left + pad,
      right: mapRect.right - pad,
    };
    var box = node.getBoundingClientRect();
    var dx = 0;
    var dy = 0;
    if (box.top < limit.top) dy = box.top - limit.top;
    else if (box.bottom > limit.bottom) dy = Math.min(box.bottom - limit.bottom, box.top - limit.top);
    if (box.left < limit.left) dx = box.left - limit.left;
    else if (box.right > limit.right) dx = Math.min(box.right - limit.right, box.left - limit.left);
    if (dx || dy) map.panBy([dx, dy], { animate: true, duration: 0.25 });
  }

  map.on("popupopen", function (e) {
    // รอให้วาดกล่องเสร็จก่อนค่อยวัดขนาดจริง
    requestAnimationFrame(function () { nudgePopupIntoView(e.popup); });
  });

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
