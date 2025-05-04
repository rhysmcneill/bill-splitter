// hot reload for /equal when participant count modal is completed.
document.addEventListener("DOMContentLoaded", function () {
  document.addEventListener("htmx:afterOnLoad", function (event) {
    if (
      event.target.id === "polling-participant-count" &&
      event.detail.xhr.responseText === "set"
    ) {
      window.location.reload();
    }
  });
});
