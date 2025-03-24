document.addEventListener('DOMContentLoaded', () => {
  const detectCardBtn = document.getElementById('detect-card-btn');
  const cardStatus = document.getElementById('card-status');
  const readerName = document.getElementById('reader-name');
  const cardIcon = document.getElementById('card-icon');
  const detectionRing = document.getElementById('detection-ring');

  const updateCardStatus = (status, reader = null) => {
    cardStatus.textContent = status;
    readerName.textContent = reader || '--';

    if (status === 'Detected') {
      cardStatus.classList.remove('text-yellow-400');
      cardStatus.classList.add('text-green-400');
      cardIcon.classList.remove('text-gray-500');
      cardIcon.classList.add('text-green-400');
      detectionRing.classList.add('border-green-500');
      detectionRing.classList.remove('border-transparent');
    } else {
      cardStatus.classList.remove('text-green-400');
      cardStatus.classList.add('text-yellow-400');
      cardIcon.classList.remove('text-green-400');
      cardIcon.classList.add('text-gray-500');
      detectionRing.classList.remove('border-green-500');
      detectionRing.classList.add('border-transparent');
    }
  };

  detectCardBtn.addEventListener('click', async () => {
    updateCardStatus('Detecting...');
    try {
      const response = await fetch('/api/card/detect');
      const data = await response.json();

      if (data.status === 'success') {
        if (data.data.active_reader !== null) {
          updateCardStatus('Detected', `Reader ${data.data.active_reader}`);
        } else {
          updateCardStatus('Not Detected');
        }
      } else {
        updateCardStatus('Error', data.detail);
      }
    } catch (error) {
      console.error('Error detecting card:', error);
      updateCardStatus('Error', 'Failed to connect to API');
    }
  });
});