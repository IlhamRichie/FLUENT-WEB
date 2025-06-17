document.addEventListener('DOMContentLoaded', function () {
    // Fungsi animasi angka (CountUp)
    const animateCountUp = (el) => {
        const target = parseFloat(el.dataset.target) || (el.innerText.includes('K+') ? parseFloat(el.dataset.target) : parseFloat(el.innerText));
        const decimals = parseInt(el.dataset.decimals) || 0;
        const suffix = el.dataset.suffix || '';
        const duration = 1800;
        const framesPerSecond = 60;
        const totalFrames = Math.round((duration / 1000) * framesPerSecond);
        let currentFrame = 0;

        const count = () => {
            currentFrame++;
            const progress = currentFrame / totalFrames;
            const easeOutProgress = 1 - Math.pow(1 - progress, 4);
            let currentValue = easeOutProgress * target;
            let displayValue;

            if (suffix === "K+") {
                displayValue = (currentValue / 1000).toFixed(1) + "K+";
                if(currentValue >= target) displayValue = (target / 1000) + "K+";
            } else if (decimals > 0) {
                displayValue = currentValue.toFixed(decimals) + suffix;
            } else {
                displayValue = Math.round(currentValue).toLocaleString() + suffix;
            }
            el.innerText = displayValue;

            if (currentFrame < totalFrames) {
                requestAnimationFrame(count);
            } else {
                if (suffix === "K+") {
                     el.innerText = (target / 1000) + "K+";
                } else {
                     el.innerText = target.toFixed(decimals) + suffix;
                }
            }
        };
        requestAnimationFrame(count);
    };

    const countUpObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCountUp(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.3
    });

    document.querySelectorAll('.count-up').forEach(el => {
        countUpObserver.observe(el);
    });
});