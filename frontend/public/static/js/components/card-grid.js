/**
 * Card Grid Manager - Enables draggable and rearrangeable cards
 */
import Sortable from 'https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js';

class CardGridManager {
    constructor(gridSelector = '#card-grid') {
        this.gridElement = document.querySelector(gridSelector);
        this.sortableInstance = null;
        this.savedLayout = null;
        
        if (this.gridElement) {
            this.initSortable();
            this.loadSavedLayout();
        }
    }
    
    initSortable() {
        // Initialize Sortable.js on the grid
        this.sortableInstance = Sortable.create(this.gridElement, {
            animation: 150,
            handle: '.drag-handle',
            draggable: '.card',
            onStart: (evt) => {
                evt.item.classList.add('dragging');
            },
            onEnd: (evt) => {
                evt.item.classList.remove('dragging');
                this.saveLayout();
            }
        });
    }
    
    saveLayout() {
        // Save the current layout to localStorage
        if (!this.gridElement) return;
        
        const cardOrder = [];
        const cards = this.gridElement.querySelectorAll('.card');
        
        cards.forEach(card => {
            const cardId = card.getAttribute('data-card-id');
            if (cardId) {
                cardOrder.push(cardId);
            }
        });
        
        // Save for the current page
        const currentPage = window.location.pathname;
        const layoutKey = `card-layout-${currentPage}`;
        
        localStorage.setItem(layoutKey, JSON.stringify(cardOrder));
    }
    
    loadSavedLayout() {
        // Load saved layout from localStorage
        if (!this.gridElement) return;
        
        const currentPage = window.location.pathname;
        const layoutKey = `card-layout-${currentPage}`;
        
        const savedLayout = localStorage.getItem(layoutKey);
        if (!savedLayout) return;
        
        try {
            const cardOrder = JSON.parse(savedLayout);
            const cardMap = new Map();
            
            // Get all cards and map them by their IDs
            const cards = this.gridElement.querySelectorAll('.card');
            cards.forEach(card => {
                const cardId = card.getAttribute('data-card-id');
                if (cardId) {
                    cardMap.set(cardId, card);
                }
            });
            
            // Reorder cards based on saved layout
            cardOrder.forEach(cardId => {
                const card = cardMap.get(cardId);
                if (card) {
                    this.gridElement.appendChild(card);
                }
            });
        } catch (error) {
            console.error('Error loading card layout:', error);
        }
    }
}

export default CardGridManager;