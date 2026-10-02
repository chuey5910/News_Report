/* รูปภาพแนบในฟอร์ม — เลือกได้หลายครั้ง สะสมรายการ แสดงตัวอย่าง + ช่องคำบรรยายต่อรูป
   ตัว input[type=file] ส่งได้แค่ชุดที่เลือกล่าสุด จึงเก็บไฟล์ไว้เอง (DataTransfer) แล้วยัดกลับทุกครั้ง */
(function () {
  var field = document.getElementById("photo-field");
  var input = document.getElementById("photo-input");
  var preview = document.getElementById("photo-preview");
  var countEl = document.getElementById("photo-count");
  if (!field || !input || !preview) return;

  var max = parseInt(field.dataset.max || "10", 10);
  var existing = parseInt(field.dataset.existing || "0", 10);
  var files = [];

  function existingKept() {
    var boxes = field.querySelectorAll('input[name="photo_delete"]');
    var deleted = 0;
    boxes.forEach(function (b) { if (b.checked) deleted += 1; });
    return existing - deleted;
  }

  function sync() {
    // ยัดรายการไฟล์ที่สะสมไว้กลับเข้า input เพื่อให้ส่งไปกับฟอร์ม
    var dt = new DataTransfer();
    files.forEach(function (f) { dt.items.add(f); });
    input.files = dt.files;
    var total = existingKept() + files.length;
    countEl.textContent = total
      ? "รูปทั้งหมด " + total + " / " + max + " รูป"
      : "ยังไม่ได้แนบรูป";
  }

  function render() {
    preview.innerHTML = "";
    files.forEach(function (file, index) {
      var tile = document.createElement("div");
      tile.className = "photo-tile";

      var img = document.createElement("img");
      img.alt = "";
      var url = URL.createObjectURL(file);
      img.src = url;
      img.onload = function () { URL.revokeObjectURL(url); };
      tile.appendChild(img);

      var caption = document.createElement("input");
      caption.type = "text";
      caption.name = "photo_caption";
      caption.placeholder = "คำบรรยาย (ไม่บังคับ)";
      caption.maxLength = 255;
      caption.dataset.label = "คำบรรยายรูปใหม่ที่ " + (index + 1);
      caption.value = file._caption || "";
      caption.addEventListener("input", function () { file._caption = caption.value; });
      tile.appendChild(caption);

      var remove = document.createElement("button");
      remove.type = "button";
      remove.className = "photo-remove";
      remove.textContent = "เอาออก";
      remove.addEventListener("click", function () {
        files.splice(index, 1);
        render();
        sync();
      });
      tile.appendChild(remove);

      preview.appendChild(tile);
    });
  }

  input.addEventListener("change", function () {
    var room = max - existingKept() - files.length;
    var picked = Array.prototype.slice.call(input.files || []);
    if (picked.length > room) {
      alert("แนบรูปได้สูงสุด " + max + " รูปต่อรายงาน — เพิ่มได้อีก " + Math.max(room, 0) + " รูป");
      picked = picked.slice(0, Math.max(room, 0));
    }
    picked.forEach(function (f) { files.push(f); });
    render();
    sync();
  });

  field.querySelectorAll('input[name="photo_delete"]').forEach(function (box) {
    box.addEventListener("change", sync);
  });

  sync();
})();
