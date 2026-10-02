/* เมนูซ้ายพับเข้า-ออก
   จอใหญ่: จำสถานะพับไว้ใน localStorage  |  จอเล็ก: เมนูเลื่อนทับเนื้อหา ปิดได้ด้วยการแตะพื้นหลัง */
(function () {
  var root = document.documentElement;
  var toggle = document.getElementById("sidebar-toggle");
  var backdrop = document.getElementById("sidebar-backdrop");
  var KEY = "sidebar-collapsed";
  var MOBILE = 900;

  function isMobile() {
    return window.innerWidth <= MOBILE;
  }

  function apply(collapsed) {
    root.classList.toggle("sidebar-collapsed", collapsed);
    if (toggle) toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
  }

  // จอเล็กเริ่มด้วยเมนูปิดไว้เสมอ เพื่อให้เห็นแผนที่/เนื้อหาเต็มจอก่อน
  var stored = null;
  try {
    stored = localStorage.getItem(KEY);
  } catch (e) {
    stored = null;
  }
  apply(isMobile() ? true : stored === "1");

  function setCollapsed(collapsed) {
    apply(collapsed);
    try {
      localStorage.setItem(KEY, collapsed ? "1" : "0");
    } catch (e) {
      /* โหมดส่วนตัวของเบราว์เซอร์อาจห้ามเขียน — ไม่เป็นไร แค่ไม่จำสถานะ */
    }
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      setCollapsed(!root.classList.contains("sidebar-collapsed"));
    });
  }
  if (backdrop) {
    backdrop.addEventListener("click", function () {
      setCollapsed(true);
    });
  }
  // แตะเมนูบนจอเล็กแล้วให้เมนูหุบเอง (ไม่ค้างทับหน้าถัดไป)
  document.querySelectorAll(".sidebar a").forEach(function (link) {
    link.addEventListener("click", function () {
      if (isMobile()) apply(true);
    });
  });

})();
