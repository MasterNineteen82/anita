// button-fixer.js: Utility to standardise button interactions and effects

export default class ButtonFixer {
  
  // Initialise fixing for all buttons on page
  static fixAllButtons() {
    document.querySelectorAll('.btn').forEach(button => {
      ButtonFixer.applyClickEffect(button);
    });
  }

  // Applies a consistent click-effect to buttons
  static applyClickEffect(button) {
    button.addEventListener('click', (e) => {
      if (e.currentTarget) {
        e.currentTarget.classList.add('animate-click');

        setTimeout(() => {
          // Check if element still exists in DOM before removing class
          if (e.currentTarget && e.currentTarget.classList) {
            e.currentTarget.classList.remove('animate-click');
          }
        }, 200);
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', function() {
    // Fix all buttons first
    ButtonFixer.fixAllButtons();
    
    // Additional styling after a short delay
    setTimeout(function() {
        const elements = document.querySelectorAll('.btn, .badge');
        if (elements) {
            elements.forEach(element => {
                if (element) {
                    element.classList.add('rounded-md');
                    // Apply click effect to these elements too
                    ButtonFixer.applyClickEffect(element);
                }
            });
        }
    }, 100);
});


