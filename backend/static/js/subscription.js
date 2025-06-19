document.addEventListener('DOMContentLoaded', function() {
    // 1. Temukan elemen-elemen penting di HTML
    const billingSwitch = document.getElementById('billing-cycle-switch');
    const toggleContainer = document.querySelector('.pricing-toggle-container');

    // Hentikan jika elemen toggle tidak ditemukan di halaman ini
    if (!billingSwitch) {
        return;
    }

    // 2. Buat fungsi untuk memperbarui semua harga dan teks
    function updatePrices() {
        // Cek apakah tombol dalam posisi 'checked' (Tahunan)
        const isYearly = billingSwitch.checked;
        
        // Temukan semua elemen yang perlu diubah
        const priceElements = document.querySelectorAll('.price-value');
        const periodElements = document.querySelectorAll('.price-period');

        // Tambah/hapus kelas di container untuk mengubah gaya (misal: warna latar & badge)
        if (isYearly) {
            toggleContainer.classList.add('yearly-active');
        } else {
            toggleContainer.classList.remove('yearly-active');
        }

        // Perbarui setiap elemen harga
        priceElements.forEach(el => {
            // Ambil harga dari atribut data-, tergantung 'isYearly'
            const price = isYearly ? el.dataset.yearly : el.dataset.monthly;
            // Format angka menjadi format mata uang Rupiah (misal: 49000 -> 49.000)
            el.textContent = new Intl.NumberFormat('id-ID').format(price);
        });

        // Perbarui setiap elemen periode
        periodElements.forEach(el => {
            const periodTextId = isYearly ? 'tahun' : 'bulan';
            const periodTextEn = isYearly ? 'year' : 'month';
            // Ganti HTML di dalamnya agar teks bahasa juga ikut berubah
            el.innerHTML = `/ <span class="lang-id">${periodTextId}</span><span class="lang-en">${periodTextEn}</span>`;
        });
    }

    // 3. Tambahkan 'event listener'
    // Setiap kali tombol switch diubah (diklik), panggil fungsi updatePrices
    billingSwitch.addEventListener('change', updatePrices);
    
    // 4. Inisialisasi
    // Panggil fungsi sekali saat halaman pertama kali dimuat untuk memastikan tampilan awal sudah benar
    updatePrices();
});
