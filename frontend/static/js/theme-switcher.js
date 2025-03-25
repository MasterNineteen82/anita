document.addEventListener('DOMContentLoaded', () => {
  const themeToggle = document.getElementById('theme-toggle');
  const themeStyle = document.getElementById('theme-style');
  const themeIcon = document.getElementById('theme-icon');
  const localStorageKey = 'theme';

  // Function to set the theme
  function setTheme(themeName) {
    localStorage.setItem(localStorageKey, themeName);
    if (themeStyle) {
      themeStyle.href = `/static/css/${themeName}.css`;
    }

    // Update the theme icon
    if (themeName === 'light') {
      themeIcon.classList.remove('fa-sun', 'fa-moon');
      themeIcon.classList.add('fa-sun');
    } else if (themeName === 'dark') {
      themeIcon.classList.remove('fa-sun', 'fa-moon');
      themeIcon.classList.add('fa-moon');
    } else {
      themeIcon.classList.remove('fa-sun', 'fa-moon');
      themeIcon.classList.add('fa-magic'); // Or any other appropriate icon
    }
  }

  // Function to toggle the theme
  function toggleTheme() {
    const currentTheme = localStorage.getItem(localStorageKey);
    let nextTheme;

    if (currentTheme === 'light') {
      nextTheme = 'dark';
    } else if (currentTheme === 'dark') {
      nextTheme = 'custom';
    } else {
      nextTheme = 'light';
    }

    setTheme(nextTheme);
  }

  // Event listener for the theme toggle
  if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
  }

  // Immediately invoked function to set the theme on initial load
  (function () {
    let initialTheme = localStorage.getItem(localStorageKey);
    if (!initialTheme) {
      initialTheme = 'light'; // Set a default theme if none is set
    }
    setTheme(initialTheme);
  })();
});