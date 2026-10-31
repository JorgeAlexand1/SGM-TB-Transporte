/** @odoo-module **/

const fieldNames = {
    name: 'techstore-client-name',
    code: 'codigo',
    price: 'precio_unitario',
    stock: 'stock_disponible',
    quantity: 'cantidad',
    discount: 'descuento',
    tax: 'iva_porcentaje',
    digits: 'cedula,telefono',
};

function fieldName(target) {
    if (!(target instanceof HTMLInputElement)) {
        return '';
    }
    if (target.name) {
        return target.name;
    }
    const wrapper = target.closest('.o_field_widget');
    return wrapper ? wrapper.getAttribute('name') || '' : '';
}

function clean(target) {
    const name = fieldName(target);
    if (name === fieldNames.code) {
        target.value = target.value.replace(/[^A-Za-z0-9]/g, '').slice(0, 8);
    } else if (fieldNames.digits.split(',').includes(name)) {
        target.value = target.value.replace(/\D/g, '').slice(0, 10);
    } else if (name === fieldNames.stock) {
        target.value = target.value.replace(/\D/g, '').slice(0, 4);
    } else if (name === fieldNames.quantity) {
        target.value = target.value.replace(/\D/g, '').slice(0, 6);
    } else if (name === fieldNames.name) {
        target.value = target.value.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]/g, '');
    } else if (name === fieldNames.price
        || name === fieldNames.discount
        || name === fieldNames.tax) {
        const normalized = target.value.replace(',', '.').replace(/[^0-9.]/g, '');
        const firstDot = normalized.indexOf('.');
        const maxIntegerDigits = name === fieldNames.price ? 5 : 3;
        const integerPart = (firstDot < 0 ? normalized : normalized.slice(0, firstDot))
            .slice(0, maxIntegerDigits);
        const decimalPart = firstDot < 0
            ? ''
            : normalized.slice(firstDot + 1).replace(/\./g, '').slice(0, 2);
        target.value = firstDot < 0
            ? integerPart
            : `${integerPart}.${decimalPart}`;
        if (name === fieldNames.discount && Number(target.value) > 100) {
            target.value = '100';
        }
    }
}

function accepts(target, key) {
    const name = fieldName(target);
    if (name === fieldNames.code) {
        return /^[A-Za-z0-9]$/.test(key);
    }
    if (fieldNames.digits.split(',').includes(name)
        || name === fieldNames.stock
        || name === fieldNames.quantity) {
        return /^\d$/.test(key);
    }
    if (name === fieldNames.price
        || name === fieldNames.discount
        || name === fieldNames.tax) {
        return /^\d$/.test(key) || key === '.' || key === ',';
    }
    if (name === fieldNames.name) {
        return /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]$/.test(key);
    }
    return true;
}

document.addEventListener('keydown', (event) => {
    if (!(event.target instanceof HTMLInputElement)
        || event.ctrlKey || event.metaKey || event.altKey
        || event.key.length !== 1) {
        return;
    }
    if (!accepts(event.target, event.key)) {
        event.preventDefault();
    }
}, true);

document.addEventListener('input', (event) => {
    if (event.target instanceof HTMLInputElement) {
        clean(event.target);
    }
}, true);

document.addEventListener('paste', (event) => {
    if (!(event.target instanceof HTMLInputElement)) {
        return;
    }
    event.preventDefault();
    const target = event.target;
    const pasted = event.clipboardData.getData('text');
    const start = target.selectionStart || 0;
    const end = target.selectionEnd || 0;
    target.value = `${target.value.slice(0, start)}${pasted}${target.value.slice(end)}`;
    clean(target);
    target.dispatchEvent(new Event('input', { bubbles: true }));
}, true);
