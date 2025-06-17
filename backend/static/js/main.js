document.addEventListener("DOMContentLoaded", function () {
    // --- Efek scroll pada Navbar ---
    const navbar = document.querySelector(".fluent-navbar");
    if (navbar) {
        window.addEventListener("scroll", function () {
            if (window.scrollY > 30) {
                navbar.classList.add("scrolled");
            } else {
                navbar.classList.remove("scrolled");
            }
        });
    }

    // --- Logika Pengalih Bahasa ---
    const langSwitcherLinks = document.querySelectorAll(".lang-switcher");
    const htmlTag = document.documentElement;
    const currentLangDisplay = document.getElementById("currentLangDisplay");

    // Fungsi untuk mengatur bahasa pada <html>, localStorage, dan tampilan UI
    function setLanguage(lang) {
        htmlTag.setAttribute("lang", lang); // CSS akan menangani tampilan elemen
        localStorage.setItem("preferredLang", lang);
        if (currentLangDisplay) {
            currentLangDisplay.textContent = lang.toUpperCase();
        }
    }

    // Tambahkan event listener ke setiap tombol pengalih bahasa
    langSwitcherLinks.forEach((link) => {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            const selectedLang = this.dataset.lang;
            setLanguage(selectedLang);
        });
    });

    // Saat halaman dimuat, periksa bahasa yang tersimpan atau gunakan 'id' sebagai default
    const preferredLang = localStorage.getItem("preferredLang") || "id";
    setLanguage(preferredLang);

    // --- Update Tahun Copyright Secara Dinamis ---
    const yearSpan = document.getElementById("current-year");
    if (yearSpan) {
        yearSpan.textContent = new Date().getFullYear();
    }
});