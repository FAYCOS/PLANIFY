/**
 * Planify v3.0 - JavaScript Mobile
 * Interactions tactiles et PWA
 */

class MobileApp {
    constructor() {
        this.touchStartX = 0;
        this.touchEndX = 0;
        this.touchStartY = 0;
        this.touchEndY = 0;
        this.pullToRefreshThreshold = 80;
        this.isPulling = false;
        
        this.init();
    }
    
    init() {
        // Détecter si on est sur mobile
        if (!this.isMobile()) {
            return;
        }
        
        this.setupMobileUI();
        this.setupTouchGestures();
        this.setupPullToRefresh();
        this.setupBottomNav();
        this.setupModals();
        this.setupToasts();
        this.setupFAB();
        this.setupVibration();
        
        console.log('✅ Mobile App initialisée');
    }
    
    isMobile() {
        return window.innerWidth <= 768;
    }
    
    // ==================== UI MOBILE ====================
    
    setupMobileUI() {
        // Créer le header mobile s'il n'existe pas
        if (!document.querySelector('.mobile-header')) {
            this.createMobileHeader();
        }
        
        // Créer la navigation bottom s'il n'existe pas
        if (!document.querySelector('.mobile-bottom-nav')) {
            this.createBottomNav();
        }
        
        // Ajouter la classe mobile au body
        document.body.classList.add('mobile-view');
        
        // Empêcher le zoom sur double tap
        let lastTouchEnd = 0;
        document.addEventListener('touchend', (e) => {
            const now = Date.now();
            if (now - lastTouchEnd <= 300) {
                e.preventDefault();
            }
            lastTouchEnd = now;
        }, false);
    }
    
    createMobileHeader() {
        const header = document.createElement('div');
        header.className = 'mobile-header';
        header.innerHTML = `
            <h1>${document.title || 'Planify'}</h1>
            <div class="mobile-header-actions">
                <button class="mobile-header-btn" id="mobile-search-btn">
                    <i class="fas fa-search"></i>
                </button>
                <button class="mobile-header-btn" id="mobile-menu-btn">
                    <i class="fas fa-bars"></i>
                </button>
            </div>
        `;
        document.body.prepend(header);
        
        // Event listeners
        document.getElementById('mobile-search-btn')?.addEventListener('click', () => {
            this.showSearchModal();
        });
        
        document.getElementById('mobile-menu-btn')?.addEventListener('click', () => {
            this.showMenuModal();
        });
    }
    
    createBottomNav() {
        const nav = document.createElement('nav');
        nav.className = 'mobile-bottom-nav';
        
        const currentPath = window.location.pathname;
        
        const navItems = [
            { icon: 'fas fa-home', label: 'Accueil', href: '/' },
            { icon: 'fas fa-calendar', label: 'Prestations', href: '/prestations' },
            { icon: 'fas fa-plus-circle', label: 'Nouveau', href: '/prestations/nouvelle', fab: true },
            { icon: 'fas fa-box', label: 'Matériel', href: '/materiels' },
            { icon: 'fas fa-user', label: 'Profil', href: '/profil' }
        ];
        
        nav.innerHTML = navItems.map(item => {
            const isActive = currentPath === item.href || 
                           (item.href !== '/' && currentPath.startsWith(item.href));
            
            return `
                <a href="${item.href}" class="mobile-nav-item ${isActive ? 'active' : ''} ${item.fab ? 'mobile-nav-fab' : ''}">
                    <i class="${item.icon}"></i>
                    <span>${item.label}</span>
                </a>
            `;
        }).join('');
        
        document.body.appendChild(nav);
    }
    
    // ==================== SWIPE GESTURES ====================
    
    setupTouchGestures() {
        // Swipe sur les items de liste pour afficher actions
        document.addEventListener('touchstart', (e) => {
            const swipeable = e.target.closest('.mobile-swipeable');
            if (swipeable) {
                this.touchStartX = e.touches[0].clientX;
                this.touchStartY = e.touches[0].clientY;
            }
        });
        
        document.addEventListener('touchmove', (e) => {
            const swipeable = e.target.closest('.mobile-swipeable');
            if (swipeable) {
                this.touchEndX = e.touches[0].clientX;
                this.touchEndY = e.touches[0].clientY;
                
                const deltaX = this.touchStartX - this.touchEndX;
                const deltaY = Math.abs(this.touchStartY - this.touchEndY);
                
                // Swipe horizontal uniquement
                if (Math.abs(deltaX) > deltaY && Math.abs(deltaX) > 50) {
                    e.preventDefault();
                    
                    if (deltaX > 0) {
                        // Swipe left - montrer actions
                        swipeable.style.transform = `translateX(-${Math.min(deltaX, 120)}px)`;
                    }
                }
            }
        });
        
        document.addEventListener('touchend', (e) => {
            const swipeable = e.target.closest('.mobile-swipeable');
            if (swipeable) {
                const deltaX = this.touchStartX - this.touchEndX;
                
                if (deltaX > 60) {
                    // Swipe complet - afficher actions
                    swipeable.classList.add('swiped');
                    swipeable.style.transform = 'translateX(-120px)';
                } else {
                    // Retour position initiale
                    swipeable.classList.remove('swiped');
                    swipeable.style.transform = 'translateX(0)';
                }
                
                this.touchStartX = 0;
                this.touchEndX = 0;
            }
        });
        
        // Fermer les swipes ouverts en cliquant ailleurs
        document.addEventListener('touchstart', (e) => {
            if (!e.target.closest('.mobile-swipeable')) {
                document.querySelectorAll('.mobile-swipeable.swiped').forEach(item => {
                    item.classList.remove('swiped');
                    item.style.transform = 'translateX(0)';
                });
            }
        });
    }
    
    // ==================== PULL TO REFRESH ====================
    
    setupPullToRefresh() {
        let pullStartY = 0;
        let pullMoveY = 0;
        
        const mainContent = document.querySelector('.main-content') || document.body;
        
        mainContent.addEventListener('touchstart', (e) => {
            // Seulement si on est en haut de la page
            if (window.scrollY === 0) {
                pullStartY = e.touches[0].clientY;
            }
        });
        
        mainContent.addEventListener('touchmove', (e) => {
            if (pullStartY === 0) return;
            
            pullMoveY = e.touches[0].clientY;
            const pullDistance = pullMoveY - pullStartY;
            
            if (pullDistance > 0 && window.scrollY === 0) {
                e.preventDefault();
                
                // Créer l'indicateur s'il n'existe pas
                let indicator = document.querySelector('.pull-to-refresh');
                if (!indicator) {
                    indicator = document.createElement('div');
                    indicator.className = 'pull-to-refresh';
                    indicator.innerHTML = '<div class="pull-to-refresh-spinner"></div>';
                    document.body.appendChild(indicator);
                }
                
                if (pullDistance > this.pullToRefreshThreshold) {
                    indicator.classList.add('pulling');
                    this.isPulling = true;
                }
            }
        });
        
        mainContent.addEventListener('touchend', () => {
            if (this.isPulling) {
                this.refreshPage();
            }
            
            pullStartY = 0;
            pullMoveY = 0;
            this.isPulling = false;
            
            const indicator = document.querySelector('.pull-to-refresh');
            if (indicator) {
                indicator.classList.remove('pulling');
            }
        });
    }
    
    refreshPage() {
        this.showToast('🔄 Actualisation...', 1000);
        
        setTimeout(() => {
            window.location.reload();
        }, 500);
    }
    
    // ==================== BOTTOM NAVIGATION ====================
    
    setupBottomNav() {
        const navItems = document.querySelectorAll('.mobile-nav-item');
        
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                // Vibration feedback
                this.vibrate(10);
                
                // Animation
                item.classList.add('haptic-feedback');
                setTimeout(() => {
                    item.classList.remove('haptic-feedback');
                }, 100);
            });
        });
    }
    
    // ==================== MODALS ====================
    
    setupModals() {
        // Gérer l'ouverture/fermeture des modals
        document.addEventListener('click', (e) => {
            const modalTrigger = e.target.closest('[data-mobile-modal]');
            if (modalTrigger) {
                e.preventDefault();
                const modalId = modalTrigger.dataset.mobileModal;
                this.showModal(modalId);
            }
            
            const modalClose = e.target.closest('[data-modal-close]');
            if (modalClose) {
                this.hideAllModals();
            }
        });
        
        // Fermer en cliquant sur le backdrop
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('mobile-modal-backdrop')) {
                this.hideAllModals();
            }
        });
        
        // Swipe down pour fermer
        document.querySelectorAll('.mobile-modal').forEach(modal => {
            let startY = 0;
            
            modal.addEventListener('touchstart', (e) => {
                startY = e.touches[0].clientY;
            });
            
            modal.addEventListener('touchmove', (e) => {
                const currentY = e.touches[0].clientY;
                const diff = currentY - startY;
                
                if (diff > 0 && modal.scrollTop === 0) {
                    modal.style.transform = `translateY(${diff}px)`;
                }
            });
            
            modal.addEventListener('touchend', (e) => {
                const endY = e.changedTouches[0].clientY;
                const diff = endY - startY;
                
                if (diff > 100) {
                    this.hideAllModals();
                } else {
                    modal.style.transform = '';
                }
            });
        });
    }
    
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.warn(`Modal ${modalId} not found`);
            return;
        }
        
        // Créer backdrop
        let backdrop = document.querySelector('.mobile-modal-backdrop');
        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.className = 'mobile-modal-backdrop';
            document.body.appendChild(backdrop);
        }
        
        backdrop.classList.add('active');
        modal.classList.add('active');
        
        // Empêcher le scroll du body
        document.body.style.overflow = 'hidden';
        
        this.vibrate(10);
    }
    
    hideAllModals() {
        document.querySelectorAll('.mobile-modal').forEach(modal => {
            modal.classList.remove('active');
        });
        
        const backdrop = document.querySelector('.mobile-modal-backdrop');
        if (backdrop) {
            backdrop.classList.remove('active');
        }
        
        // Réactiver le scroll
        document.body.style.overflow = '';
    }
    
    showSearchModal() {
        // Créer modal de recherche si n'existe pas
        let modal = document.getElementById('mobile-search-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'mobile-search-modal';
            modal.className = 'mobile-modal';
            modal.innerHTML = `
                <div class="mobile-modal-handle"></div>
                <h2>Rechercher</h2>
                <div class="mobile-search">
                    <i class="fas fa-search mobile-search-icon"></i>
                    <input type="text" class="mobile-search-input" placeholder="Rechercher..." id="mobile-search-field">
                    <button class="mobile-search-clear" style="display:none;">×</button>
                </div>
                <div id="mobile-search-results" class="mobile-list"></div>
            `;
            document.body.appendChild(modal);
            
            // Setup search functionality
            const searchField = document.getElementById('mobile-search-field');
            const clearBtn = modal.querySelector('.mobile-search-clear');
            
            searchField.addEventListener('input', (e) => {
                clearBtn.style.display = e.target.value ? 'flex' : 'none';
                this.performSearch(e.target.value);
            });
            
            clearBtn.addEventListener('click', () => {
                searchField.value = '';
                clearBtn.style.display = 'none';
                this.performSearch('');
            });
        }
        
        this.showModal('mobile-search-modal');
        
        // Focus sur le champ de recherche
        setTimeout(() => {
            document.getElementById('mobile-search-field')?.focus();
        }, 300);
    }
    
    showMenuModal() {
        // Créer modal menu si n'existe pas
        let modal = document.getElementById('mobile-menu-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'mobile-menu-modal';
            modal.className = 'mobile-modal';
            modal.innerHTML = `
                <div class="mobile-modal-handle"></div>
                <h2>Menu</h2>
                <ul class="mobile-list">
                    <li class="mobile-list-item" onclick="window.location.href='/'">
                        <div class="mobile-list-icon"><i class="fas fa-home"></i></div>
                        <div class="mobile-list-content">
                            <div class="mobile-list-title">Tableau de bord</div>
                        </div>
                        <i class="fas fa-chevron-right mobile-list-action"></i>
                    </li>
                    <li class="mobile-list-item" onclick="window.location.href='/prestations'">
                        <div class="mobile-list-icon"><i class="fas fa-calendar"></i></div>
                        <div class="mobile-list-content">
                            <div class="mobile-list-title">Prestations</div>
                        </div>
                        <i class="fas fa-chevron-right mobile-list-action"></i>
                    </li>
                    <li class="mobile-list-item" onclick="window.location.href='/materiels'">
                        <div class="mobile-list-icon"><i class="fas fa-box"></i></div>
                        <div class="mobile-list-content">
                            <div class="mobile-list-title">Matériel</div>
                        </div>
                        <i class="fas fa-chevron-right mobile-list-action"></i>
                    </li>
                    <li class="mobile-list-item" onclick="window.location.href='/djs'">
                        <div class="mobile-list-icon"><i class="fas fa-users"></i></div>
                        <div class="mobile-list-content">
                            <div class="mobile-list-title">DJs</div>
                        </div>
                        <i class="fas fa-chevron-right mobile-list-action"></i>
                    </li>
                    <li class="mobile-list-item" onclick="window.location.href='/rapports'">
                        <div class="mobile-list-icon"><i class="fas fa-chart-bar"></i></div>
                        <div class="mobile-list-content">
                            <div class="mobile-list-title">Rapports</div>
                        </div>
                        <i class="fas fa-chevron-right mobile-list-action"></i>
                    </li>
                    <li class="mobile-list-item" onclick="window.location.href='/parametres'">
                        <div class="mobile-list-icon"><i class="fas fa-cog"></i></div>
                        <div class="mobile-list-content">
                            <div class="mobile-list-title">Paramètres</div>
                        </div>
                        <i class="fas fa-chevron-right mobile-list-action"></i>
                    </li>
                    <li class="mobile-list-item" onclick="window.location.href='/logout'" style="border-top: 1px solid #eee; margin-top: 16px;">
                        <div class="mobile-list-icon" style="background: rgba(255,68,68,0.1); color: #ff4444;">
                            <i class="fas fa-sign-out-alt"></i>
                        </div>
                        <div class="mobile-list-content">
                            <div class="mobile-list-title" style="color: #ff4444;">Déconnexion</div>
                        </div>
                        <i class="fas fa-chevron-right mobile-list-action"></i>
                    </li>
                </ul>
            `;
            document.body.appendChild(modal);
        }
        
        this.showModal('mobile-menu-modal');
    }
    
    performSearch(query) {
        const resultsContainer = document.getElementById('mobile-search-results');
        if (!resultsContainer) return;
        
        if (!query) {
            resultsContainer.innerHTML = '';
            return;
        }
        
        resultsContainer.innerHTML = '<div class="mobile-empty-state"><div class="mobile-empty-text">Recherche en cours...</div></div>';
        
        fetch(`/api/recherche?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(data => {
                if (Array.isArray(data) && data.length > 0) {
                    resultsContainer.innerHTML = data.map(item => `
                        <div class="mobile-list-item" onclick="window.location.href='${item.url}'">
                            <div class="mobile-list-icon"><i class="fas fa-${this.iconForType(item.type)}"></i></div>
                            <div class="mobile-list-content">
                                <div class="mobile-list-title">${item.titre}</div>
                                <div class="mobile-list-subtitle">${item.sous_titre || ''}</div>
                            </div>
                            <i class="fas fa-chevron-right mobile-list-action"></i>
                        </div>
                    `).join('');
                } else {
                    resultsContainer.innerHTML = `
                        <div class="mobile-empty-state">
                            <div class="mobile-empty-icon">🔍</div>
                            <div class="mobile-empty-title">Aucun résultat</div>
                            <div class="mobile-empty-text">Essayez une autre recherche</div>
                        </div>
                    `;
                }
            })
            .catch(err => {
                console.error('Erreur recherche:', err);
                resultsContainer.innerHTML = '<div class="mobile-empty-state"><div class="mobile-empty-text">Erreur de recherche</div></div>';
            });
    }

    iconForType(type) {
        switch (type) {
            case 'prestation':
                return 'calendar-check';
            case 'materiel':
                return 'box';
            case 'dj':
                return 'headphones';
            default:
                return 'file';
        }
    }
    
    // ==================== TOASTS ====================
    
    setupToasts() {
        // Le container sera créé à la volée
    }
    
    showToast(message, duration = 3000, icon = null, type = null) {
        let toast = document.querySelector('.mobile-toast');
        
        if (!toast) {
            toast = document.createElement('div');
            toast.className = 'mobile-toast';
            document.body.appendChild(toast);
        }
        
        toast.className = `mobile-toast${type ? ' ' + type : ''}`;
        
        toast.innerHTML = `
            ${icon ? `<span class="mobile-toast-icon">${icon}</span>` : ''}
            <span class="mobile-toast-message">${message}</span>
        `;
        
        toast.classList.add('show');
        this.vibrate(10);
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, duration);
    }
    
    // ==================== FAB (Floating Action Button) ====================
    
    setupFAB() {
        const fab = document.querySelector('.mobile-fab');
        if (fab) {
            fab.addEventListener('click', () => {
                this.vibrate(20);
            });
        }
    }
    
    // ==================== VIBRATION ====================
    
    vibrate(duration = 10) {
        if ('vibrate' in navigator) {
            navigator.vibrate(duration);
        }
    }
    
    // ==================== UTILS ====================
    
    enableSkeletonLoader(container) {
        container.innerHTML = Array(5).fill(0).map(() => 
            '<div class="mobile-skeleton mobile-skeleton-card"></div>'
        ).join('');
    }
    
    disableSkeletonLoader(container) {
        container.querySelectorAll('.mobile-skeleton').forEach(el => el.remove());
    }
}

// ==================== PWA INSTALLATION ====================

class PWAManager {
    constructor() {
        this.deferredPrompt = null;
        this.init();
    }
    
    init() {
        // Écouter l'événement beforeinstallprompt
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallButton();
        });
        
        // Détecter si déjà installé
        if (window.matchMedia('(display-mode: standalone)').matches) {
            console.log('✅ PWA déjà installée');
        }
        
        // Détecter iOS
        const isIos = /iphone|ipad|ipod/.test(window.navigator.userAgent.toLowerCase());
        const isInStandaloneMode = ('standalone' in window.navigator) && (window.navigator.standalone);
        
        if (isIos && !isInStandaloneMode) {
            this.showIOSInstallInstructions();
        }
    }
    
    showInstallButton() {
        // Créer un bouton d'installation
        const installBtn = document.createElement('button');
        installBtn.className = 'mobile-btn mobile-btn-primary';
        installBtn.style.cssText = 'position: fixed; bottom: 80px; left: 16px; right: 16px; z-index: 1000;';
        installBtn.innerHTML = '<i class="fas fa-download"></i> Installer l\'application';
        
        installBtn.addEventListener('click', () => {
            this.promptInstall();
        });
        
        document.body.appendChild(installBtn);
        
        // Cacher après 10 secondes
        setTimeout(() => {
            installBtn.remove();
        }, 10000);
    }
    
    async promptInstall() {
        if (!this.deferredPrompt) {
            return;
        }
        
        this.deferredPrompt.prompt();
        
        const { outcome } = await this.deferredPrompt.userChoice;
        
        if (outcome === 'accepted') {
            console.log('✅ PWA installée');
            if (mobileApp) {
                mobileApp.showToast('✅ Application installée !', 3000);
            }
        }
        
        this.deferredPrompt = null;
    }
    
    showIOSInstallInstructions() {
        // Afficher instructions pour iOS
        const instructions = document.createElement('div');
        instructions.className = 'mobile-toast';
        instructions.style.cssText = 'transform: translateY(0); bottom: 80px;';
        instructions.innerHTML = `
            <span class="mobile-toast-icon">📱</span>
            <span class="mobile-toast-message">
                Appuyez sur <strong>Partager</strong> puis <strong>Sur l'écran d'accueil</strong>
            </span>
        `;
        
        document.body.appendChild(instructions);
        
        setTimeout(() => {
            instructions.remove();
        }, 8000);
    }
}

// ==================== INITIALISATION ====================

let mobileApp;
let pwaManager;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        mobileApp = new MobileApp();
        pwaManager = new PWAManager();
    });
} else {
    mobileApp = new MobileApp();
    pwaManager = new PWAManager();
}

// ==================== EXPORTS ====================

window.MobileApp = MobileApp;
window.PWAManager = PWAManager;
window.mobileApp = mobileApp;
window.pwaManager = pwaManager;
