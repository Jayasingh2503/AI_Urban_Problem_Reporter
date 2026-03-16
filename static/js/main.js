// Auto-dismiss success/info flash messages after 5 seconds
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".alert.alert-success, .alert.alert-info").forEach(el => {
    setTimeout(() => bootstrap.Alert.getOrCreateInstance(el).close(), 5000);
  });
});