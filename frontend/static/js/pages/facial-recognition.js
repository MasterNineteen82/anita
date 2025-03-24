import UI from '/static/js/utils/ui.js';
import Logger from '/static/js/utils/logger.js';

document.addEventListener('DOMContentLoaded', () => {
  const cameraFeed = document.getElementById('face-camera');
  const faceCanvas = document.getElementById('face-canvas');
  const cameraContainer = document.getElementById('camera-container');
  const cameraPlaceholder = document.getElementById('camera-placeholder');
  const startCameraBtn = document.getElementById('start-camera-btn');
  const stopCameraBtn = document.getElementById('stop-camera-btn');
  const cameraModeSelect = document.getElementById('camera-mode');
  const captureFaceBtn = document.getElementById('capture-face-btn');

  let stream = null;
  let faceDetectionActive = false;

  // Function to start the camera
  async function startCamera() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true });
      cameraFeed.srcObject = stream;
      cameraFeed.classList.remove('hidden');
      faceCanvas.classList.remove('hidden');
      cameraPlaceholder.classList.add('hidden');

      const context = faceCanvas.getContext('2d');
      faceDetectionActive = true;
      detectFaces(context); // Start face detection

      UI.toast('Camera started successfully.', 'success');
      Logger.info('Camera started.');
    } catch (error) {
      console.error('Error starting camera:', error);
      UI.toast(`Error starting camera: ${error.message}`, 'error');
      Logger.error(`Error starting camera: ${error.message}`);
      cameraPlaceholder.innerHTML = `<p class="text-red-400">Camera access denied or not available.</p>`;
    }
  }

  // Function to stop the camera
  function stopCamera() {
    if (stream) {
      const tracks = stream.getTracks();
      tracks.forEach(track => track.stop());
      cameraFeed.srcObject = null;
      cameraFeed.classList.add('hidden');
      faceCanvas.classList.add('hidden');
      cameraPlaceholder.classList.remove('hidden');
      faceDetectionActive = false;

      UI.toast('Camera stopped.', 'info');
      Logger.info('Camera stopped.');
    }
  }

  // Function to detect faces in the camera feed
  async function detectFaces(context) {
    while (faceDetectionActive) {
      try {
        faceCanvas.width = cameraFeed.videoWidth;
        faceCanvas.height = cameraFeed.videoHeight;
        context.drawImage(cameraFeed, 0, 0, faceCanvas.width, faceCanvas.height);

        // Send the image data to the backend for face detection
        const imageData = faceCanvas.toDataURL('image/jpeg');
        const response = await fetch('/api/facial/detect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: imageData }),
        });

        const data = await response.json();

        if (data.success && data.faces) {
          // Draw rectangles around the detected faces
          data.faces.forEach(face => {
            context.beginPath();
            context.rect(face.x, face.y, face.width, face.height);
            context.lineWidth = 2;
            context.strokeStyle = 'rgb(0, 255, 0)';
            context.stroke();
          });
        }
      } catch (error) {
        console.error('Face detection error:', error);
        Logger.error(`Face detection error: ${error.message}`);
      }
      await new Promise(resolve => setTimeout(resolve, 50)); // Adjust the delay as needed
    }
  }

  // Event listeners
  startCameraBtn.addEventListener('click', startCamera);
  stopCameraBtn.addEventListener('click', stopCamera);
  captureFaceBtn.addEventListener('click', () => {
    // Placeholder: Implement face capture logic here
    UI.toast('Face captured (not implemented yet).', 'info');
    Logger.info('Face captured (not implemented yet).');
  });

  // Disable capture button initially
  captureFaceBtn.disabled = true;

  // Enable/disable capture button based on camera mode
  cameraModeSelect.addEventListener('change', () => {
    captureFaceBtn.disabled = cameraModeSelect.value !== 'enrollment';
  });
});