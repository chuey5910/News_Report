document.addEventListener("DOMContentLoaded", function () {
  var btn = document.getElementById("copy-report-btn");
  var source = document.getElementById("copy-report-source");
  if (!btn || !source) return;

  function flash(ok) {
    var original = "คัดลอกข้อมูล (Copy)";
    btn.textContent = ok ? "คัดลอกแล้ว ✓" : "คัดลอกไม่สำเร็จ";
    btn.disabled = true;
    setTimeout(function () {
      btn.textContent = original;
      btn.disabled = false;
    }, 2000);
  }

  // เว็บรันบน http:// ภายใน LAN — navigator.clipboard ใช้ได้เฉพาะ https/localhost
  // จึงต้องมี fallback แบบ select + execCommand เสมอ
  function copyFallback(text) {
    source.hidden = false;
    source.style.position = "fixed";
    source.style.left = "-9999px";
    source.value = text;
    source.focus();
    source.select();
    source.setSelectionRange(0, text.length);
    var ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (e) {
      ok = false;
    }
    source.hidden = true;
    return ok;
  }

  btn.addEventListener("click", function () {
    var text = source.value || source.textContent;
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(
        function () { flash(true); },
        function () { flash(copyFallback(text)); }
      );
    } else {
      flash(copyFallback(text));
    }
  });
});
