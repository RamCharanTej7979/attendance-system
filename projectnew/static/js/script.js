document.addEventListener('DOMContentLoaded', () => {
    // Dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    if (alerts.length > 0) {
        setTimeout(() => {
            alerts.forEach(alert => {
                alert.style.transition = 'opacity 0.5s ease';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 500);
            });
        }, 5000);
    }

    // Circular Progress Bar Animation logic
    const progressBars = document.querySelectorAll('.circular-progress');
    progressBars.forEach(bar => {
        const targetProgress = bar.getAttribute('data-percentage');
        // Setting up UI rotation purely encoded via inline style in jinja too,
        // but can be animated here if we update CSS dynamically
        let currentProgress = 0;
        const speed = 10;
        
        let progressInterval = setInterval(() => {
            if(currentProgress >= targetProgress) {
                clearInterval(progressInterval);
                bar.style.background = `conic-gradient(var(--primary) ${targetProgress * 3.6}deg, rgba(255, 255, 255, 0.05) 0deg)`;
            } else {
                currentProgress++;
                bar.style.background = `conic-gradient(var(--primary) ${currentProgress * 3.6}deg, rgba(255, 255, 255, 0.05) 0deg)`;
            }
        }, speed);
    });

    // Capture Photo Logic for Add Student Page
    const captureBtn = document.getElementById('capture-btn');
    const webcamImg = document.getElementById('webcam-feed');
    const photoDataInput = document.getElementById('photo-data');
    const capturePreview = document.getElementById('capture-preview');
    const captureStatus = document.getElementById('capture-status');

    if (captureBtn && webcamImg) {
        captureBtn.addEventListener('click', () => {
            // Because we stream MJPEG to an <img> tag, we can capture the current frame
            // by drawing it to a canvas and getting the Data URL.
            // Note: Since MJPEG image might be subject to CORS based on how it's served,
            // we will instead send an AJAX request to the server to trigger a capture,
            // or we grab from canvas if they are same origin. 
            // In our case, same origin is true.
            
            try {
                const canvas = document.createElement('canvas');
                canvas.width = webcamImg.width || 640;
                canvas.height = webcamImg.height || 480;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(webcamImg, 0, 0, canvas.width, canvas.height);
                
                const dataURL = canvas.toDataURL('image/jpeg', 0.9);
                photoDataInput.value = dataURL;
                
                if (capturePreview) {
                    capturePreview.src = dataURL;
                    capturePreview.style.display = 'block';
                }
                
                if(captureStatus) {
                    captureStatus.innerHTML = '<span class="text-success" style="color:var(--success)">Face captured successfully. You can now submit.</span>';
                }
            } catch(e) {
                console.error("Canvas capture error:", e);
                // Fallback for CORS issues if any (unlikely local)
                alert("Could not capture image from stream directly. Please ensure you allow permissions.");
            }
        });
    }
});
