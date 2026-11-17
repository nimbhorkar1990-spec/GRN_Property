/**
 * GRN PROPERTIES - Main Client JavaScript
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Navbar Scrolled State
  const navbar = document.querySelector('.navbar-grn');
  if (navbar) {
    window.addEventListener('scroll', function () {
      if (window.scrollY > 40) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
    });
  }

  // 2. Schedule Site Visit Modal Dynamic Data
  const scheduleModal = document.getElementById('scheduleVisitModal');
  if (scheduleModal) {
    scheduleModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;
      if (button) {
        const propId = button.getAttribute('data-property-id') || '';
        const propTitle = button.getAttribute('data-property-title') || 'General Pune Site Visit';

        const idInput = scheduleModal.querySelector('#modalPropertyId');
        const titleInput = scheduleModal.querySelector('#modalPropertyTitle');
        const displaySpan = scheduleModal.querySelector('#modalPropertyTitleDisplay');

        if (idInput) idInput.value = propId;
        if (titleInput) titleInput.value = propTitle;
        if (displaySpan) displaySpan.textContent = propTitle;
      }
    });
  }

  // 3. Image Gallery Thumbnail Switcher
  const mainGalleryImg = document.getElementById('mainPropertyImage');
  const thumbItems = document.querySelectorAll('.thumb-item');
  if (mainGalleryImg && thumbItems.length > 0) {
    thumbItems.forEach(thumb => {
      thumb.addEventListener('click', function () {
        const fullSrc = this.getAttribute('data-full-img');
        if (fullSrc) {
          mainGalleryImg.src = fullSrc;
          thumbItems.forEach(t => t.classList.remove('active'));
          this.classList.add('active');
        }
      });
    });
  }

  // 4. Hero Search Bar Tab Purpose Toggle
  const purposeTabs = document.querySelectorAll('.hero-purpose-tab');
  const purposeInput = document.getElementById('heroSearchPurpose');
  if (purposeTabs.length > 0 && purposeInput) {
    purposeTabs.forEach(tab => {
      tab.addEventListener('click', function (e) {
        e.preventDefault();
        purposeTabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        purposeInput.value = this.getAttribute('data-purpose');
      });
    });
  }

  // 5. EMI Calculator on Property Detail
  const emiLoanAmount = document.getElementById('emiAmount');
  const emiRate = document.getElementById('emiRate');
  const emiTenure = document.getElementById('emiTenure');
  const emiResultDisplay = document.getElementById('emiResult');

  function calculateEMI() {
    if (!emiLoanAmount || !emiRate || !emiTenure || !emiResultDisplay) return;
    const P = parseFloat(emiLoanAmount.value) || 0;
    const annualRate = parseFloat(emiRate.value) || 8.5;
    const years = parseFloat(emiTenure.value) || 20;

    const r = (annualRate / 12) / 100;
    const n = years * 12;

    if (P > 0 && r > 0 && n > 0) {
      const emi = (P * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
      emiResultDisplay.textContent = '₹' + Math.round(emi).toLocaleString('en-IN') + ' / month';
    } else {
      emiResultDisplay.textContent = '₹0 / month';
    }
  }

  if (emiLoanAmount && emiRate && emiTenure) {
    emiLoanAmount.addEventListener('input', calculateEMI);
    emiRate.addEventListener('input', calculateEMI);
    emiTenure.addEventListener('input', calculateEMI);
    calculateEMI();
  }

  // 6. Share Property Button
  const shareBtn = document.getElementById('sharePropertyBtn');
  if (shareBtn) {
    shareBtn.addEventListener('click', function (e) {
      e.preventDefault();
      const title = this.getAttribute('data-title') || document.title;
      const url = window.location.href;

      if (navigator.share) {
        navigator.share({
          title: title,
          text: 'Check out this premium property on GRN PROPERTIES:',
          url: url
        }).catch(() => {});
      } else {
        navigator.clipboard.writeText(url).then(() => {
          showToast('Property link copied to clipboard!');
        });
      }
    });
  }

  // 7. Toast Notification Helper
  function showToast(message) {
    let toastContainer = document.getElementById('grnToastContainer');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'grnToastContainer';
      toastContainer.style.position = 'fixed';
      toastContainer.style.top = '24px';
      toastContainer.style.right = '24px';
      toastContainer.style.zIndex = '10000';
      document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    toast.className = 'alert alert-grn d-flex align-items-center gap-2 mb-2 shadow-lg';
    toast.innerHTML = `<i class="fas fa-check-circle text-gold"></i> <span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.5s ease';
      setTimeout(() => toast.remove(), 500);
    }, 3500);
  }

  // 8. Auto-capture Current Website Page URL on all Enquiry forms
  try {
    const currentUrl = window.location.href;
    document.querySelectorAll('.enquiry-page-url').forEach(function (input) {
      if (!input.value || input.value.trim() === '') {
        input.value = currentUrl;
      }
    });
  } catch (e) {
    console.debug('Enquiry page URL capture initialized:', e);
  }
});

