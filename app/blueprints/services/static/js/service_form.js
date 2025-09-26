document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('form');
  const nameField = document.getElementById('name');
  const displayNameField = document.getElementById('display_name');

  nameField.addEventListener('input', function () {
    displayNameField.value = this.value
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  });


  form.addEventListener('submit', function (e) {
    const requiredFields = form.querySelectorAll('[required]');
    let hasError = false;

    requiredFields.forEach(field => {
      if (!field.value.trim()) {
        field.classList.add('is-invalid');
        hasError = true;
      } else {
        field.classList.remove('is-invalid');
      }
    });

    if (hasError) {
      e.preventDefault();
      const firstError = form.querySelector('.is-invalid');
      if (firstError) {
        firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        firstError.focus();
      }
    }
  });

  const inputs = form.querySelectorAll('.form-control, .form-select');
  inputs.forEach(input => {
    input.addEventListener('input', function () {
      if (this.value.trim()) {
        this.classList.remove('is-invalid');
      }
    });
  });
});

function validateServiceName(input) {
  const value = input.value;
  const isValid = /^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$/.test(value);

  if (value && !isValid) {
    input.setCustomValidity('Service name must contain only lowercase letters, numbers, and hyphens. Cannot start or end with a hyphen.');
  } else {
    input.setCustomValidity('');
  }
}

const nameInput = document.getElementById('name');
if (nameInput) {
  nameInput.addEventListener('input', function () {
    validateServiceName(this);
  });
}