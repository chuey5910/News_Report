/* หมดเวลาเมื่อไม่มีความเคลื่อนไหว — ฝั่งหน้าเว็บ (server บังคับอีกชั้นอยู่แล้ว)
   - ทุกการขยับ (คลิก พิมพ์ เลื่อน แตะ) นับเป็นความเคลื่อนไหว
   - ขณะยังขยับอยู่ ส่ง ping ไป server ทุก 5 นาที เพื่อต่ออายุ (กรอกฟอร์มยาวๆ จะไม่โดนเตะ)
   - ก่อนหมดเวลา 60 วินาที เด้งหน้าต่างเตือน กด "ใช้งานต่อ" = ต่ออายุ ไม่กดจนครบ = ออกจากระบบ */
(function () {
  var script = document.currentScript;
  if (!script) return;
  var idleMs = (parseInt(script.dataset.idleMinutes || "30", 10)) * 60 * 1000;
  var pingUrl = script.dataset.pingUrl;
  var logoutUrl = script.dataset.logoutUrl;
  var modal = document.getElementById("session-warning");
  var countdownEl = document.getElementById("session-countdown");
  var extendBtn = document.getElementById("session-extend");
  if (!modal || !pingUrl) return;

  var WARN_MS = 60 * 1000;
  var PING_EVERY = 5 * 60 * 1000;
  var lastActivity = Date.now();
  var lastPing = Date.now();
  var warning = false;
  var countdownTimer = null;

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    var input = document.querySelector('input[name="csrf_token"]');
    return (meta && meta.content) || (input && input.value) || "";
  }

  function ping() {
    lastPing = Date.now();
    var body = new FormData();
    body.append("csrf_token", csrfToken());
    fetch(pingUrl, { method: "POST", body: body, credentials: "same-origin" })
      .then(function (res) {
        if (res.status === 401) window.location.href = logoutUrl;
      })
      .catch(function () { /* เน็ตสะดุด ไม่เป็นไร รอบหน้าค่อยส่งใหม่ */ });
  }

  function onActivity() {
    lastActivity = Date.now();
    if (warning) hideWarning();
    if (Date.now() - lastPing > PING_EVERY) ping();
  }

  function showWarning() {
    warning = true;
    modal.classList.add("open");
    var left = Math.ceil((idleMs - (Date.now() - lastActivity)) / 1000);
    countdownEl.textContent = left;
    countdownTimer = setInterval(function () {
      left = Math.ceil((idleMs - (Date.now() - lastActivity)) / 1000);
      countdownEl.textContent = Math.max(left, 0);
      if (left <= 0) {
        clearInterval(countdownTimer);
        window.location.href = logoutUrl;
      }
    }, 500);
  }

  function hideWarning() {
    warning = false;
    modal.classList.remove("open");
    if (countdownTimer) clearInterval(countdownTimer);
    ping();
  }

  ["click", "keydown", "scroll", "touchstart", "input"].forEach(function (name) {
    document.addEventListener(name, onActivity, { passive: true });
  });
  extendBtn.addEventListener("click", function (e) {
    e.stopPropagation();
    lastActivity = Date.now();
    hideWarning();
  });

  setInterval(function () {
    var idle = Date.now() - lastActivity;
    if (!warning && idle >= idleMs - WARN_MS) showWarning();
  }, 1000);
})();
