document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('table.table').forEach((table) => {
        if (table.dataset.layout === 'table' || table.classList.contains('table-keep')) {
            return;
        }

        let headers = Array.from(table.querySelectorAll('thead th')).map((th) =>
            (th.textContent || '').trim()
        );
        if (!headers.length) {
            headers = Array.from(table.querySelectorAll('tr th')).map((th) =>
                (th.textContent || '').trim()
            );
        }

        table.classList.add('table-cards');

        table.querySelectorAll('tbody tr').forEach((row) => {
            Array.from(row.children).forEach((cell, idx) => {
                if (!cell.matches('td')) {
                    return;
                }
                if (!cell.hasAttribute('data-label')) {
                    const fallback = `Champ ${idx + 1}`;
                    const label = headers[idx] || fallback;
                    cell.setAttribute('data-label', label);
                }
            });
        });
    });
});
