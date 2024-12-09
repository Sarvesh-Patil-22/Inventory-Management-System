// static/js/main.js

document.addEventListener('DOMContentLoaded', function () {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function () {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function (alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Form validation
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Dynamic search functionality
    const searchInputs = document.querySelectorAll('[data-search-table]');
    searchInputs.forEach(input => {
        input.addEventListener('keyup', function (e) {
            const searchText = e.target.value.toLowerCase();
            const tableId = e.target.getAttribute('data-search-table');
            const table = document.getElementById(tableId);
            const rows = table.getElementsByTagName('tr');

            Array.from(rows).forEach((row, index) => {
                if (index === 0) return; // Skip header row
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchText) ? '' : 'none';
            });
        });
    });

    // Print functionality
    document.querySelectorAll('.print-button').forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            window.print();
        });
    });

    // Confirmation dialogs
    document.querySelectorAll('[data-confirm]').forEach(element => {
        element.addEventListener('click', function (e) {
            if (!confirm(this.getAttribute('data-confirm'))) {
                e.preventDefault();
            }
        });
    });

    // File input preview
    document.querySelectorAll('.custom-file-input').forEach(input => {
        input.addEventListener('change', function (e) {
            const fileName = e.target.files[0].name;
            const label = e.target.nextElementSibling;
            label.textContent = fileName;
        });
    });

    // Number input validation
    document.querySelectorAll('input[type="number"]').forEach(input => {
        input.addEventListener('input', function (e) {
            if (this.hasAttribute('min') && this.value < parseInt(this.getAttribute('min'))) {
                this.value = this.getAttribute('min');
            }
            if (this.hasAttribute('max') && this.value > parseInt(this.getAttribute('max'))) {
                this.value = this.getAttribute('max');
            }
        });
    });

    // Table sorting
    document.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', function () {
            const table = th.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const index = Array.from(th.parentElement.children).indexOf(th);
            const direction = th.classList.contains('asc') ? -1 : 1;

            rows.sort((a, b) => {
                const aValue = a.children[index].textContent.trim();
                const bValue = b.children[index].textContent.trim();
                return direction * aValue.localeCompare(bValue, undefined, { numeric: true });
            });

            tbody.append(...rows);
            th.classList.toggle('asc');
        });
    });

    // Responsive tables
    const tables = document.querySelectorAll('.table-responsive');
    tables.forEach(table => {
        const wrapper = document.createElement('div');
        wrapper.classList.add('table-wrapper');
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
    });
});