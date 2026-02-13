/**
 * DJ Prestations Manager - JavaScript principal
 * Gestion des interactions et fonctionnalités dynamiques
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialisation des composants
    initFlashMessages();
    initTooltips();
    initFormValidation();
    initAutoRefresh();
});

/**
 * Gestion des messages flash
 */
function initFlashMessages() {
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(message => {
        // Auto-hide après 5 secondes
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => message.remove(), 300);
        }, 5000);
    });
}

/**
 * Initialisation des tooltips
 */
function initTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = e.target.dataset.tooltip;
    tooltip.style.cssText = `
        position: absolute;
        background: rgba(0,0,0,0.8);
        color: white;
        padding: 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        z-index: 1000;
        pointer-events: none;
    `;
    
    document.body.appendChild(tooltip);
    
    const rect = e.target.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
}

function hideTooltip() {
    const tooltip = document.querySelector('.tooltip');
    if (tooltip) tooltip.remove();
}

/**
 * Validation des formulaires
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', validateForm);
    });
}

function validateForm(e) {
    const form = e.target;
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showFieldError(field, 'Ce champ est obligatoire');
            isValid = false;
        } else {
            clearFieldError(field);
        }
    });
    
    if (!isValid) {
        e.preventDefault();
        showNotification('Veuillez corriger les erreurs dans le formulaire', 'error');
    }
}

function showFieldError(field, message) {
    clearFieldError(field);
    field.classList.add('error');
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'field-error';
    errorDiv.textContent = message;
    errorDiv.style.cssText = 'color: #ef4444; font-size: 0.75rem; margin-top: 0.25rem;';
    
    field.parentNode.appendChild(errorDiv);
}

function clearFieldError(field) {
    field.classList.remove('error');
    const errorDiv = field.parentNode.querySelector('.field-error');
    if (errorDiv) errorDiv.remove();
}

/**
 * Auto-refresh pour les pages d'affichage
 */
function initAutoRefresh() {
    const refreshElements = document.querySelectorAll('[data-auto-refresh]');
    refreshElements.forEach(element => {
        const interval = parseInt(element.dataset.autoRefresh) || 30000;
        setInterval(() => {
            refreshElement(element);
        }, interval);
    });
}

function refreshElement(element) {
    const url = element.dataset.refreshUrl;
    if (!url) return;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            updateElementContent(element, data);
        })
        .catch(error => {
            console.error('Erreur lors du rafraîchissement:', error);
        });
}

function updateElementContent(element, data) {
    // Mise à jour personnalisée selon le type d'élément
    if (element.dataset.refreshType === 'materiels') {
        updateMaterielsDisplay(element, data);
    }
}

function updateMaterielsDisplay(element, materiels) {
    // Logique de mise à jour pour l'affichage des matériels
    console.log('Mise à jour des matériels:', materiels);
}

/**
 * Notifications système
 */
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas fa-${getNotificationIcon(type)}"></i>
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    notification.style.cssText = `
        position: fixed;
        top: 1rem;
        right: 1rem;
        background: white;
        border-radius: 0.5rem;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        z-index: 1000;
        max-width: 400px;
        animation: slideInRight 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    if (duration > 0) {
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }
}

function getNotificationIcon(type) {
    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    return icons[type] || 'info-circle';
}

/**
 * Gestion des modales
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('fade-in');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('fade-out');
        setTimeout(() => {
            modal.style.display = 'none';
            modal.classList.remove('fade-out');
        }, 300);
    }
}

/**
 * Utilitaires
 */
function formatDate(date) {
    return new Date(date).toLocaleDateString('fr-FR');
}

function formatDateTime(date) {
    return new Date(date).toLocaleString('fr-FR');
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Gestion des filtres
 */
function initFilters() {
    const filterInputs = document.querySelectorAll('[data-filter]');
    filterInputs.forEach(input => {
        input.addEventListener('input', debounce(applyFilters, 300));
    });
}

function applyFilters() {
    const filters = {};
    document.querySelectorAll('[data-filter]').forEach(input => {
        if (input.value) {
            filters[input.dataset.filter] = input.value;
        }
    });
    
    // Application des filtres
    console.log('Filtres appliqués:', filters);
}

/**
 * Gestion des exports
 */
function exportToCSV(data, filename) {
    const csv = convertToCSV(data);
    downloadFile(csv, filename, 'text/csv');
}

function exportToJSON(data, filename) {
    const json = JSON.stringify(data, null, 2);
    downloadFile(json, filename, 'application/json');
}

function convertToCSV(data) {
    if (!data.length) return '';
    
    const headers = Object.keys(data[0]);
    const csvContent = [
        headers.join(','),
        ...data.map(row => headers.map(header => `"${row[header] || ''}"`).join(','))
    ].join('\n');
    
    return csvContent;
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

/**
 * Gestion des raccourcis clavier
 */
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + N : Nouvelle prestation
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        const newPrestationLink = document.querySelector('a[href*="/prestations/nouvelle"]');
        if (newPrestationLink) newPrestationLink.click();
    }
    
    // Ctrl/Cmd + S : Sauvegarder (si dans un formulaire)
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        const form = document.querySelector('form');
        if (form) {
            e.preventDefault();
            form.submit();
        }
    }
    
    // Échap : Fermer les modales
    if (e.key === 'Escape') {
        const openModal = document.querySelector('.modal[style*="flex"]');
        if (openModal) {
            closeModal(openModal.id);
        }
    }
});

/**
 * Styles CSS dynamiques
 */
const dynamicStyles = `
<style>
.notification-content {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem;
}

.notification-close {
    background: none;
    border: none;
    cursor: pointer;
    color: #6b7280;
    margin-left: auto;
}

.field-error {
    color: #ef4444;
    font-size: 0.75rem;
    margin-top: 0.25rem;
}

.form-control.error {
    border-color: #ef4444;
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

@keyframes slideInRight {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

@keyframes slideOutRight {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
}

.tooltip {
    position: absolute;
    background: rgba(0,0,0,0.8);
    color: white;
    padding: 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    z-index: 1000;
    pointer-events: none;
}
</style>
`;

document.head.insertAdjacentHTML('beforeend', dynamicStyles);

/**
 * Recherche en temps réel
 */
function initSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    
    if (!searchInput || !searchResults) return;
    
    let searchTimeout;
    
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        
        clearTimeout(searchTimeout);
        
        if (query.length < 2) {
            searchResults.style.display = 'none';
            return;
        }
        
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });
    
    // Masquer les résultats quand on clique ailleurs
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });
    
    // Navigation clavier
    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            searchResults.style.display = 'none';
            this.blur();
        }
    });
}

function performSearch(query) {
    const searchResults = document.getElementById('searchResults');
    
    fetch(`/api/recherche?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            displaySearchResults(data);
        })
        .catch(error => {
            console.error('Erreur de recherche:', error);
            searchResults.style.display = 'none';
        });
}

function displaySearchResults(results) {
    const searchResults = document.getElementById('searchResults');
    
    if (results.length === 0) {
        searchResults.innerHTML = '<div class="search-result-item"><div class="text-center text-gray-500 py-4">Aucun résultat trouvé</div></div>';
        searchResults.style.display = 'block';
        return;
    }
    
    let html = '';
    results.forEach(result => {
        html += `
            <div class="search-result-item" onclick="window.location.href='${result.url}'">
                <div class="search-result-title">
                    <span class="search-result-type ${result.type}">${result.type}</span>
                    ${result.titre}
                </div>
                <div class="search-result-subtitle">${result.sous_titre}</div>
            </div>
        `;
    });
    
    searchResults.innerHTML = html;
    searchResults.style.display = 'block';
}

// Initialiser la recherche au chargement
document.addEventListener('DOMContentLoaded', function() {
    initSearch();
});
