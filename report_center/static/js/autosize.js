(function () {
  function resize(el) {
    el.style.height = "auto";
    el.style.height = el.scrollHeight + "px";
  }

  function init() {
    document.querySelectorAll("textarea").forEach(function (el) {
      resize(el);
      el.addEventListener("input", function () {
        resize(el);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // re-run for textareas created later by other scripts (e.g. dynamic form fields)
  window.autosizeTextareas = init;
})();
