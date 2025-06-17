document.addEventListener('DOMContentLoaded', function () {
  // Inisialisasi Tooltip untuk semua halaman admin yang menggunakannya
  var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
  });
});