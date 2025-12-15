


async function logAction(actionText) {
    const user = JSON.parse(localStorage.getItem('currentUser'));
    const login = user ? user.login : 'Guest';

    console.log("Логируем:", actionText);

    try {
        await fetch('/logs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                user_login: login, 
                action: actionText 
            })
        });
    } catch (error) {
        console.error("Ошибка записи лога:", error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const user = JSON.parse(localStorage.getItem('currentUser'));
    const navAuth = document.getElementById('nav-auth');
    
    if (navAuth) {
        if (user) {
            navAuth.innerHTML = `
                <span>Привет, ${user.login}</span>
                ${user.role === 'admin' ? '<a href="admin.html">Админ-панель</a>' : ''}
                <a href="#" id="logoutBtn">Выход</a>
            `;
            document.getElementById('logoutBtn').addEventListener('click', logout);
        } else {
            navAuth.innerHTML = `<a href="login.html">Вход / Регистрация</a>`;
        }
    }
});


async function logout(e) {
    e.preventDefault();
    await logAction('Выход из системы');
    localStorage.removeItem('currentUser');
    window.location.href = 'login.html';
}


async function handleAuth(event, type) {
    event.preventDefault();
    const loginInput = document.getElementById('login').value;
    const passInput = document.getElementById('password').value;

    const url = type === 'register' ? '/register' : '/login';

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login: loginInput, password: passInput })
        });

        const data = await response.json();

        if (response.ok) {
            if (type === 'login') {
                // Сервер вернул роль и логин
                localStorage.setItem('currentUser', JSON.stringify(data)); 
                window.location.href = 'catalog.html';
            } else {
                alert('Регистрация успешна! Теперь войдите.');
                // Переключаем форму на вход
                toggleAuthMode();
            }
        } else {
            alert(data.detail || 'Ошибка');
        }
    } catch (error) {
        console.error('Ошибка сети:', error);
        alert('Сервер недоступен');
    }
}