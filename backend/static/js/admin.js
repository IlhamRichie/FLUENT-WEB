document.addEventListener('DOMContentLoaded', function () {
  /**
   * Fungsi untuk menginisialisasi semua tooltip Bootstrap di halaman.
   * Ini berguna untuk tombol aksi yang memiliki atribut data-bs-toggle="tooltip".
   */
  function initTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
  }

  /**
   * Fungsi untuk menyorot link sidebar yang aktif berdasarkan URL saat ini.
   * Ini memberikan umpan balik visual yang jelas kepada admin tentang halaman mana yang sedang mereka lihat.
   */
  function highlightActiveSidebarLink() {
    // Dapatkan path URL saat ini, contoh: "/admin/users"
    const currentPath = window.location.pathname;
    
    // Temukan semua link di dalam sidebar
    const sidebarLinks = document.querySelectorAll('.admin-sidebar .nav-link');

    sidebarLinks.forEach(link => {
      // Dapatkan href dari setiap link
      const linkPath = link.getAttribute('href');
      
      // Hapus kelas 'active' dari semua link terlebih dahulu
      link.classList.remove('active');
      
      // Jika path URL saat ini SAMA PERSIS dengan href link, tambahkan kelas 'active'
      if (linkPath === currentPath) {
        link.classList.add('active');
      }
    });
  }

  // Panggil kedua fungsi saat halaman selesai dimuat
  initTooltips();
  highlightActiveSidebarLink();
});
