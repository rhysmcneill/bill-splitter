// This is for hot-reload during the payment stage in /choose endpoint - this redirect user to the choice when one of the
// users chooses the bill splitting method.
document.body.addEventListener('htmx:afterOnLoad', function(event) {
  const response = event.detail.xhr.response;
  try {
    const data = JSON.parse(response);
    if (data.redirect_url) {
      window.location.href = data.redirect_url;  // Auto-redirect when mode is set
    }
  } catch (e) {
    // Ignore non-JSON responses
  }
});