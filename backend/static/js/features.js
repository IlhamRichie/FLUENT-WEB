document.addEventListener('DOMContentLoaded', function() {
    // Menemukan semua elemen navigasi dan konten fitur
    const featureNavLinks = document.querySelectorAll('.feature-nav .nav-link');
    const featureContents = document.querySelectorAll('.feature-content');

    /**
     * Menangani klik pada link navigasi fitur.
     * @param {Event} e - Event object dari klik.
     */
    function handleFeatureClick(e) {
        e.preventDefault();

        // Mengambil target fitur dari atribut data-feature
        const targetFeature = e.currentTarget.getAttribute('data-feature');

        // 1. Menghapus kelas 'active' dari semua link navigasi
        featureNavLinks.forEach(link => {
            link.classList.remove('active');
        });

        // 2. Menambahkan kelas 'active' ke link yang diklik
        e.currentTarget.classList.add('active');

        // 3. Menyembunyikan semua panel konten
        featureContents.forEach(content => {
            content.classList.remove('active');
        });

        // 4. Menampilkan panel konten yang sesuai
        const targetContent = document.getElementById(`feature-${targetFeature}`);
        if (targetContent) {
            targetContent.classList.add('active');
        }
    }

    // Menambahkan event listener ke setiap link navigasi
    featureNavLinks.forEach(link => {
        link.addEventListener('click', handleFeatureClick);
    });
});
