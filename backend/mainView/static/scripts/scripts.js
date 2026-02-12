document.addEventListener('DOMContentLoaded', () => {
    // Проверяем, подключена ли библиотека lucide, чтобы избежать ошибок
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // Логика мобильного меню
    const btn = document.getElementById('mobile-menu-btn');
    const menu = document.getElementById('mobile-menu');

    // Проверяем существование элементов перед добавлением событий
    if (btn && menu) {
        btn.addEventListener('click', () => {
            menu.classList.toggle('hidden');
        });
    }
});