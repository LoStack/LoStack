function serviceActionWithTerminal(streamUrl, actionTitle) {
  const modalTitle = document.getElementById('terminalModalLabel');
  if (modalTitle) {
    modalTitle.innerHTML = `<i class="bi bi-terminal me-2"></i>${actionTitle}`;
  }
  
  launchTerminalModal(streamUrl);
}

let deleteServiceUrl = null;
let deleteServiceName = null;

function showDeleteConfirmation(serviceId, serviceName, deleteUrl) {
  deleteServiceUrl = deleteUrl;
  deleteServiceName = serviceName;
  
  const modalLabel = document.getElementById('deleteServiceModalLabel');
  modalLabel.innerHTML = `<i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>Delete "${serviceName}"`;

  const deleteModal = new bootstrap.Modal(document.getElementById('deleteServiceModal'));
  deleteModal.show();
}

document.getElementById('confirmDeleteBtn').addEventListener('click', function() {
  if (deleteServiceUrl) {
    const deleteModal = bootstrap.Modal.getInstance(document.getElementById('deleteServiceModal'));
    deleteModal.hide();
    
    serviceActionWithTerminal(deleteServiceUrl, `${deleteServiceName} - Delete Service`);
    
    deleteServiceUrl = null;
    deleteServiceName = null;
  }
});