let products = [];

function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

async function loadProducts() {
    const searchQuery = getQueryParam('q');
    const urlCategory = getQueryParam('category');

    // Устанавливаем значение в строку поиска, если оно есть в URL
    if (searchQuery) {
        document.getElementById('catalogSearchInput').value = searchQuery;
    }

    let fetchUrl = '/products';
    if (searchQuery) fetchUrl += `?q=${encodeURIComponent(searchQuery)}`;

    try {
        const response = await fetch(fetchUrl);
        if (response.ok) {
            products = await response.json();
            
            // Если есть категория в URL, фильтруем локально
            if (urlCategory) {
                document.getElementById('categoryFilter').value = urlCategory;
                applyFilters();
            } else {
                renderProducts(products);
            }
        }
    } catch (e) {
        console.error("Ошибка загрузки:", e);
    }
}

function renderProducts(data) {
    const renderArea = document.getElementById('catalogRenderArea');
    renderArea.innerHTML = ''; 

    if (data.length === 0) {
        renderArea.innerHTML = '<p>Ничего не найдено.</p>';
        return;
    }

    const searchQuery = document.getElementById('catalogSearchInput').value.trim();
    
    // Разделяем на группы
    const originals = data.filter(item => !item.is_analog);
    const analogs = data.filter(item => item.is_analog);

    // Функция создания карточки
    const createCard = (item) => `
        <div class="product-card">
            <a href="product.html?id=${item.id}" style="text-decoration:none; color:inherit;">
                <img src="${item.image_url}" alt="${item.name}">
                <h3>${item.name}</h3>
            </a>
            <p>Производитель: ${item.brand}</p>
            <p>Артикул: <b>${item.article || '—'}</b></p>
            <p class="price">${item.price} ₽</p>
            <button onclick="addToCart(${item.id})">В корзину</button>
        </div>
    `;

    // СЦЕНАРИЙ 1: Был поиск по запросу
    if (searchQuery) {
        // Секция результатов
        if (originals.length > 0) {
            renderArea.innerHTML += `
                <h2 style="margin: 20px 0; border-bottom: 2px solid #007bff; padding-bottom: 5px;">Результаты поиска:</h2>
                <div class="products-grid-inner">${originals.map(createCard).join('')}</div>
            `;
        }
        // Секция аналогов
        if (analogs.length > 0) {
            renderArea.innerHTML += `
                <h2 style="margin: 40px 0 20px 0; color: #666; border-bottom: 2px solid #ccc; padding-bottom: 5px;">Возможные аналоги/замены:</h2>
                <div class="products-grid-inner">${analogs.map(createCard).join('')}</div>
            `;
        }
    } 
    // СЦЕНАРИЙ 2: Просто просмотр каталога или фильтры
    else {
        renderArea.innerHTML += `
            <div class="products-grid-inner">${data.map(createCard).join('')}</div>
        `;
    }
}

async function doCatalogSearch() {
    const q = document.getElementById('catalogSearchInput').value.trim();
    // Обновляем URL без перезагрузки
    const newUrl = window.location.pathname + (q ? `?q=${encodeURIComponent(q)}` : '');
    window.history.pushState({}, '', newUrl);
    await loadProducts();
}

function applyFilters() {
    const category = document.getElementById('categoryFilter').value;
    const brand = document.getElementById('brandFilter').value;
    const price = document.getElementById('priceFilter').value;

    const filtered = products.filter(item => {
        const catMatch = (category === 'all') || (item.category === category);
        const brandMatch = (brand === 'all') || (item.brand === brand);
        const priceMatch = (!price) || (item.price <= Number(price));
        return catMatch && brandMatch && priceMatch;
    });

    renderProducts(filtered);
}

function addToCart(productID) {
    const product = products.find(p => p.id == productID);
    if (!product) return;
    let cart = JSON.parse(localStorage.getItem('cart')) || [];
    cart.push(product);
    localStorage.setItem('cart', JSON.stringify(cart));
    alert(`${product.name} добавлен в корзину!`);
}

document.addEventListener('DOMContentLoaded', loadProducts);
