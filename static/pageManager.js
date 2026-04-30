/**
 * pageManager.js
 * Busca o usuário autenticado via /api/me (JWT cookie)
 * e aplica as restrições de nível na interface.
 */

class User {
    constructor(name, level) {
        this.name  = name;
        this.level = level;
    }

    /** Retorna true se o usuário tem nível suficiente */
    levelManagement(levelRequired) {
        const levels = { admin: 3, operator: 2, user: 1 };
        if (!levelRequired) return true;
        return (levels[this.level] || 0) >= (levels[levelRequired] || 0);
    }
}

class PermissionManager {
    constructor(user) {
        this.user = user;
    }

    applyRestrictions() {
        document.querySelectorAll('[data-nivel]').forEach(el => {
            const required = el.getAttribute('data-nivel');
            if (!this.user.levelManagement(required)) {
                el.classList.add('oculto');
            }
        });
        this._updateSidebarLabel();
    }

    _updateSidebarLabel() {
        // Atualiza qualquer elemento com a classe .user-role-label
        document.querySelectorAll('.user-role-label').forEach(el => {
            el.textContent =
                this.user.level.charAt(0).toUpperCase() + this.user.level.slice(1);
        });

        // Compatibilidade com o seletor antigo do projeto
        const sideElement = document.querySelector('.text-secondary[style*="0.75rem"]');
        if (sideElement) {
            sideElement.textContent =
                this.user.level.charAt(0).toUpperCase() + this.user.level.slice(1);
        }
    }
}

/**
 * Inicialização principal:
 * 1. Busca /api/me para pegar nome e role do usuário logado
 * 2. Aplica restrições de permissão
 * 3. Dispara renderizarLista() se existir na página
 */
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/api/me', { credentials: 'include' });

        if (!res.ok) {
            // JWT inválido ou expirado → redireciona para login
            window.location.href = '/login';
            return;
        }

        const data = await res.json();

        window.currentUser = new User(data.name, data.role);

        const uiManager = new PermissionManager(window.currentUser);
        uiManager.applyRestrictions();

        // Inicializa a lista de tickets, se a função existir na página
        if (typeof renderizarLista === 'function') {
            renderizarLista();
        }

    } catch (err) {
        console.error('Erro ao carregar dados do usuário:', err);
        window.location.href = '/login';
    }
});
