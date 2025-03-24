// ui.js: Centralised UI utilities for ANITA
import CardStandardizer from '/static/js/utils/card-standardizer.js';

export default class UI {
    // Shows a modal
    static showModal(modalId) {
      const modal = document.getElementById(modalId);
      if (modal) modal.classList.remove('hidden');
    }
  
    // Hides a modal
    static hideModal(modalId) {
      const modal = document.getElementById(modalId);
      if (modal) modal.classList.add('hidden');
    }
  
    // Toggles element visibility
    static toggleVisibility(elementId) {
      const el = document.getElementById(elementId);
      if (el) el.classList.toggle('hidden');
    }
  
    // Updates innerText safely
    static setText(elementId, text) {
      const el = document.getElementById(elementId);
      if (el) el.innerText = text;
    }
  
    // Updates HTML content safely
    static setHTML(elementId, html) {
      const el = document.getElementById(elementId);
      if (el) el.innerHTML = html;
    }
  
    // Adds loading spinner
    static setLoading(elementId, loading = true) {
      const el = document.getElementById(elementId);
      if (el) {
        if (loading) {
          el.dataset.originalContent = el.innerHTML;
          el.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
          el.disabled = true;
        } else {
          el.innerHTML = el.dataset.originalContent;
          el.disabled = false;
        }
      }
    }
  
  // Global Toast Notification
  static toast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `
      fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded shadow-lg z-50 animate-fade-in-out
    `;
    toast.innerText = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.remove();
    }, duration);
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  CardStandardizer.init();
});