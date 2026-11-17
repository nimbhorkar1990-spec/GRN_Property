/**
 * GRN PROPERTIES - Admin Dashboard Interactions
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Lead Notes Edit Modal dynamic data
  const editNotesModal = document.getElementById('editNotesModal');
  if (editNotesModal) {
    editNotesModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;
      if (button) {
        const id = button.getAttribute('data-id');
        const name = button.getAttribute('data-name');
        const status = button.getAttribute('data-status');
        const notes = button.getAttribute('data-notes') || '';
        const source = button.getAttribute('data-source') || '';

        const form = editNotesModal.querySelector('#editNotesForm');
        // If form doesn't already have action set or is on admin path:
        if (!form.getAttribute('action') || form.getAttribute('action').includes('/admin/enquiries/update/')) {
          form.action = `/admin/enquiries/update/${id}`;
        }
        
        editNotesModal.querySelector('#modalCustomerName').textContent = name;
        editNotesModal.querySelector('#modalStatusSelect').value = status;
        editNotesModal.querySelector('#modalNotesTextarea').value = notes;
        const sourceSelect = editNotesModal.querySelector('#modalLeadSourceSelect');
        if (sourceSelect && source) {
          sourceSelect.value = source;
        }
      }
    });
  }

  // 2. Real-time client-side filter for tables
  const tableSearchInput = document.getElementById('adminTableSearch');
  if (tableSearchInput) {
    tableSearchInput.addEventListener('keyup', function () {
      const filter = this.value.toLowerCase();
      const rows = document.querySelectorAll('.filterable-row');
      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.indexOf(filter) > -1 ? '' : 'none';
      });
    });
  }
});

