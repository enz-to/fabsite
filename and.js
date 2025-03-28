// Replace the camera initialization code
startCameraBtn.addEventListener('click', async () => {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: "user"
            }
        });
        video.srcObject = stream;
        video.play();
        startCameraBtn.disabled = true;
        capturePhotoBtn.disabled = false;
    } catch (err) {
        console.error('Error:', err);
        alert('Camera access denied. Please check your camera permissions in browser settings.');
    }
});