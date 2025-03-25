/**
 * Card Standardizer
 * Applies consistent styling to cards that don't use the standard component
 */
const CardStandardizer = {
  init() {
    this.standardizeCards();
    this.standardizeHeaders();
    this.moveActionsToFooter();
    this.addCardAnimations();
  },
  
  standardizeCards() {
    // Find all cards that need standardization
    const cards = document.querySelectorAll('.bg-gray-800.rounded-lg.shadow-lg:not(.anita-card-processed)');
    
    cards.forEach(card => {
      // Mark as processed
      card.classList.add('anita-card-processed');
      card.classList.add('card-hover');
      card.classList.add('dashboard-card');
      
      // Add gradient border class directly to the card element instead of wrapping
      card.classList.add('card-with-gradient-border');
      
      // Standardize content structure
      this.standardizeCardContent(card);
    });
  },
  
  standardizeCardContent(card) {
    // Add missing footer if needed
    const hasFooter = card.querySelector('.border-t') !== null;
    
    if (!hasFooter) {
      // Find the content area
      const contentArea = card.querySelector('.flex-grow');
      if (contentArea) {
        // Create standard footer
        const footer = document.createElement('div');
        footer.className = 'px-4 py-2 border-t border-gray-700';
        
        const cardHeader = card.querySelector('.text-lg, .text-md');
        const title = cardHeader ? cardHeader.textContent.trim() : 'ANITA';
        
        footer.innerHTML = `
          <div class="flex justify-between items-center">
            <span class="gradient-text text-sm">${title} Module</span>
            <span class="text-xs text-gray-500">${new Date().toLocaleDateString()}</span>
          </div>
        `;
        
        card.appendChild(footer);
      }
    }
  },
  
  // New function to move action buttons to footer or add action buttons to footer
  moveActionsToFooter() {
    const cards = document.querySelectorAll('.dashboard-card.anita-card-processed');
    
    cards.forEach(card => {
      const footer = card.querySelector('.border-t');
      if (!footer) return;
      
      // Check if actions already exist in footer
      if (footer.querySelector('.card-footer-actions')) return;
      
      // Find buttons in content area
      const contentButtons = card.querySelector('.flex-grow')?.querySelectorAll('button.btn');
      if (!contentButtons || contentButtons.length === 0) return;
      
      // Create footer actions container
      const footerActions = document.createElement('div');
      footerActions.className = 'card-footer-actions';
      
      // Add footer-with-buttons class to footer
      footer.classList.add('card-footer-with-buttons');
      
      // Clone buttons and convert to footer style
      Array.from(contentButtons).forEach(btn => {
        const icon = btn.querySelector('i');
        const text = btn.textContent.trim();
        
        const newBtn = document.createElement('button');
        newBtn.id = btn.id;
        newBtn.className = 'card-footer-btn';
        
        // Add primary style if button has cyan color
        if (btn.classList.contains('bg-cyan')) {
          newBtn.classList.add('card-footer-btn-primary');
        } else {
          newBtn.classList.add('card-footer-btn-secondary');
        }
        
        // Copy disabled state
        if (btn.disabled) {
          newBtn.disabled = true;
        }
        
        // Copy click handler
        const clickHandler = btn.getAttribute('onclick');
        if (clickHandler) {
          newBtn.setAttribute('onclick', clickHandler);
        }
        
        // Create button content
        let iconHTML = '';
        if (icon) {
          iconHTML = `<i class="${icon.className}"></i>`;
        }
        
        newBtn.innerHTML = `${iconHTML}${text}`;
        footerActions.appendChild(newBtn);
      });
      
      footer.appendChild(footerActions);
    });
  },
  
  standardizeHeaders() {
    // Find all card headers
    const headers = document.querySelectorAll('.bg-gray-800.rounded-lg .border-b');
    
    headers.forEach(header => {
      // Find icons and make them gradient
      const icons = header.querySelectorAll('.fas');
      icons.forEach(icon => {
        if (!icon.classList.contains('gradient-icon')) {
          icon.classList.add('gradient-icon');
        }
      });
    });
  },
  
  addCardAnimations() {
    // Add staggered animations to cards
    const cards = document.querySelectorAll('.dashboard-card.anita-card-processed');
    cards.forEach((card, index) => {
      card.style.animationDelay = `${0.05 * (index + 1)}s`;
      card.classList.add('animate-fade-in');
    });
  }
};

document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.dashboard-card.anita-card-processed');

    cards.forEach(card => {
        const footer = card.querySelector('.border-t');
        if (footer) {
            // Remove any buttons from the footer
            const footerButtons = footer.querySelectorAll('button');
            footerButtons.forEach(btn => btn.remove());
        }
    });
});

export default CardStandardizer;