let products = [];

function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

async function loadProducts() {
    try {
        const searchQuery = getQueryParam('q');
        const urlCategory = getQueryParam('category');

        let fetchUrl = '/products';
        if (searchQuery) {
            fetchUrl += `?q=${encodeURIComponent(searchQuery)}`;
        }

        const response = await fetch(fetchUrl);
        
        if (response.ok) {
            products = await response.json();
            
            if (urlCategory) {
                const catSelect = document.getElementById('categoryFilter');
                if(catSelect) {
                    catSelect.value = urlCategory;
                }
                applyFilters(); 
            } else {
                renderProducts(products); 
            }

            if (searchQuery) {
                const container = document.getElementById('productsContainer');
                const title = document.createElement('h2');
                title.innerText = `Результаты поиска: ${searchQuery}`;
                title.style.width = '100%';
                title.style.marginBottom = '20px';
                container.prepend(title);
            }
            
        } else {
            console.error("Ошибка загрузки товаров");
        }
    } catch (e) {
        console.error("Сервер недоступен", e);
        document.getElementById('productsContainer').innerHTML = "<p>Не удалось загрузить товары.</p>";
    }
}

function renderProducts(data) {
    const container = document.getElementById('productsContainer');
    // Очищаем всё, КРОМЕ строки поиска (она первая в контейнере)
    const searchBar = container.querySelector('.catalog-search-bar');
    const searchTitle = document.getElementById('searchTitleContainer');
    container.innerHTML = '';
    if (searchBar) container.appendChild(searchBar);
    if (searchTitle) container.appendChild(searchTitle);

    if (data.length === 0) {
        container.innerHTML += '<p>Товары не найдены</p>';
        return;
    }

    data.forEach(item => {
        // Проверяем флаг аналога, который прислал бэкенд
        const analogBadge = item.is_analog 
            ? '<span class="analog-badge" style="background: #6c757d; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; margin-bottom: 5px; display: inline-block;">АНАЛОГ</span>' 
            : '';

        container.innerHTML += `
            <div class="product-card" style="${item.is_analog ? 'border: 1px dashed #ccc; opacity: 0.9;' : ''}">
                <a href="product.html?id=${item.id}" style="text-decoration:none; color:inherit;">
                    <img src="${item.image_url}" alt="${item.name}" style="width:100%; height:150px; object-fit:contain;">
                    ${analogBadge}
                    <h3>${item.name}</h3>
                </a>
                <p>Производитель: ${item.brand}</p>
                <p>Артикул: <b>${item.article || '—'}</b></p>
                <p class="price">${item.price} ₽</p>
                <button onclick="addToCart(${item.id})">В корзину</button>
            </div>
        `;
    });
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
    // Обновляем URL без перезагрузки (полезно для SEO и удобства)
    const newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + '?q=' + encodeURIComponent(q);
    window.history.pushState({path:newUrl},'',newUrl);
    
    // Загружаем товары заново
    await loadProducts();
}
