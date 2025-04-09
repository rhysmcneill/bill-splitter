  let spinnerTimeout;

  document.body.addEventListener("htmx:beforeRequest", function () {
    clearTimeout(spinnerTimeout);
    document.getElementById("search-spinner").classList.remove("hidden");
  });

  document.body.addEventListener("htmx:afterSwap", function () {
    // Ensure spinner shows for at least 300ms
    spinnerTimeout = setTimeout(() => {
      document.getElementById("search-spinner").classList.add("hidden");
    }, 400);
  });