let products = [];

function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

async function loadProducts() {
    try {
        const response = await fetch('/products');
        if (response.ok) {
            products = await response.json();
            
            const urlCategory = getQueryParam('category');
            
            if (urlCategory) {
                const catSelect = document.getElementById('categoryFilter');
                if(catSelect) {
                    catSelect.value = urlCategory;
                    if (catSelect.value === "") catSelect.value = "all"; 
                }
                applyFilters(); 
            } else {
                renderProducts(products); 
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
    container.innerHTML = '';

    if (data.length === 0) {
        container.innerHTML = '<p>Товары не найдены</p>';
        return;
    }

    data.forEach(item => {
        container.innerHTML += `
            <div class="product-card">
                <a href="product.html?id=${item.id}" style="text-decoration:none; color:inherit;">
                    <img src="${item.image_url}" alt="${item.name}" style="width:100%; height:150px; object-fit:contain; cursor:pointer;">
                    <h3>${item.name}</h3>
                </a>
                <p>Производитель: ${item.brand}</p>
                
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