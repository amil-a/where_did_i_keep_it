// Show a spinner on the search button while the request is in flight,
// and prevent double submits (the FastAPI call can take a moment).
document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("search-form");
  if (!form) return;

  form.addEventListener("submit", function () {
    var button = document.getElementById("search-button");
    document.getElementById("search-spinner").classList.remove("d-none");
    document.getElementById("search-icon").classList.add("d-none");
    button.setAttribute("aria-busy", "true");
    // Disable after the submit event has fired so the form still posts.
    setTimeout(function () { button.disabled = true; }, 0);
  });
});

// Re-enable the button if the user comes back with the browser Back button.
window.addEventListener("pageshow", function (event) {
  if (!event.persisted) return;
  var button = document.getElementById("search-button");
  if (!button) return;
  button.disabled = false;
  document.getElementById("search-spinner").classList.add("d-none");
  document.getElementById("search-icon").classList.remove("d-none");
});
