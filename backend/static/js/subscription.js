document.addEventListener('DOMContentLoaded', function() {
    const billingSwitch = document.getElementById('billing-cycle-switch');
    const toggleContainer = document.querySelector('.pricing-toggle-container');

    // Fungsi untuk memperbarui harga berdasarkan status toggle
    function updatePrices() {
        const isYearly = billingSwitch.checked;
        const priceElements = document.querySelectorAll('.price-value');
        const periodElements = document.querySelectorAll('.price-period');

        // Menambahkan kelas ke container untuk efek visual (misal: menampilkan badge hemat)
        if (isYearly) {
            toggleContainer.classList.add('yearly-active');
        } else {
            toggleContainer.classList.remove('yearly-active');
        }

        // Memperbarui elemen harga
        priceElements.forEach(el => {
            const price = isYearly ? el.dataset.yearly : el.dataset.monthly;
            // Format angka dengan pemisah ribuan
            el.textContent = new Intl.NumberFormat('id-ID').format(price);
        });

        // Memperbarui elemen periode (bulan/tahun)
        periodElements.forEach(el => {
            const periodTextId = isYearly ? 'tahun' : 'bulan';
            const periodTextEn = isYearly ? 'year' : 'month';
            el.innerHTML = `/ <span class="lang-id">${periodTextId}</span><span class="lang-en">${periodTextEn}</span>`;
        });
    }

    // Menambahkan event listener ke toggle switch
    if (billingSwitch) {
        billingSwitch.addEventListener('change', updatePrices);
    }
    
    // Inisialisasi harga saat halaman dimuat
    updatePrices();
});
