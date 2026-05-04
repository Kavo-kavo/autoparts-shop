let products = [];

function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

async function loadProducts() {
    const searchQuery = getQueryParam('q');
    if (searchQuery) {
        document.getElementById('catalogSearchInput').value = searchQuery;
        document.getElementById('searchTitleContainer').innerHTML = `<h2>Результаты для: ${searchQuery}</h2>`;
    }

    let fetchUrl = '/products';
    if (searchQuery) fetchUrl += `?q=${encodeURIComponent(searchQuery)}`;

    const response = await fetch(fetchUrl);
    if (response.ok) {
        products = await response.json();
        renderProducts(products);
    }
}

function renderProducts(data) {
    const container = document.getElementById('productsContainer');
    container.innerHTML = ''; // Очищаем контейнер

    if (data.length === 0) {
        container.innerHTML = '<p>Товары не найдены</p>';
        return;
    }

    // 1. Разделяем товары на оригиналы и аналоги
    const originals = data.filter(item => !item.is_analog);
    const analogs = data.filter(item => item.is_analog);

    // Вспомогательная функция для генерации карточки (чтобы не дублировать код)
    const createCardHTML = (item) => `
        <div class="product-card" style="${item.is_analog ? 'border: 1px dashed #ccc;' : ''}">
            <a href="product.html?id=${item.id}" style="text-decoration:none; color:inherit;">
                <img src="${item.image_url}" alt="${item.name}" style="width:100%; height:150px; object-fit:contain;">
                <h3>${item.name}</h3>
            </a>
            <p>Производитель: ${item.brand}</p>
            <p>Артикул: <b>${item.article || '—'}</b></p>
            <p class="price">${item.price} ₽</p>
            <button onclick="addToCart(${item.id})">В корзину</button>
        </div>
    `;

    // 2. Выводим результаты поиска (Оригиналы)
    if (originals.length > 0) {
        const originalSection = document.createElement('div');
        originalSection.innerHTML = `
            <h2 style="margin-bottom: 20px; border-bottom: 2px solid #007bff; padding-bottom: 5px;">Результаты поиска:</h2>
            <div class="products-grid-inner" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px;">
                ${originals.map(item => createCardHTML(item)).join('')}
            </div>
        `;
        container.appendChild(originalSection);
    }

    // 3. Выводим Аналоги
    if (analogs.length > 0) {
        const analogSection = document.createElement('div');
        analogSection.innerHTML = `
            <h2 style="margin-bottom: 20px; color: #666; border-bottom: 2px solid #ccc; padding-bottom: 5px;">Возможные замены/аналоги:</h2>
            <div class="products-grid-inner" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px;">
                ${analogs.map(item => createCardHTML(item)).join('')}
            </div>
        `;
        container.appendChild(analogSection);
    }
}

function applyFilters() {
    const category = document.getElementById('categoryFilter').value; // Берем значение категории
    const brand = document.getElementById('brandFilter').value;
    const price = document.getElementById('priceFilter').value;

    const filtered = products.filter(item => {
        const itemCat = item.category ? item.category.toLowerCase() : "";
        
        const categoryMatch = (category === 'all') || (itemCat === category.toLowerCase());
        const brandMatch = (brand === 'all') || (item.brand === brand);
        const priceMatch = (!price) || (item.price <= Number(price));

        return categoryMatch && brandMatch && priceMatch;
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
    if(typeof logAction === 'function') logAction(`Добавил в корзину: ${product.name}`);
}

document.addEventListener('DOMContentLoaded', loadProducts);

async function doCatalogSearch() {
    const q = document.getElementById('catalogSearchInput').value;
    const newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + '?q=' + encodeURIComponent(q);
    window.history.pushState({path:newUrl},'',newUrl);
    await loadProducts();
}
