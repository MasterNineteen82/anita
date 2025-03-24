document.addEventListener('DOMContentLoaded', () => {
  // You can add any initialization logic here if needed.
  // For example, you might want to fetch some initial data or
  // perform some animations when the splash page loads.

  console.log('Splash page loaded.');

  // Example: Redirect to the main page after a delay
  setTimeout(() => {
    window.location.href = '/index'; // Replace '/index' with your main page URL
  }, 3000); // Redirect after 3 seconds (adjust as needed)
});