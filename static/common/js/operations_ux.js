(function () {
  function rowCheckboxes() {
    return Array.prototype.slice.call(
      document.querySelectorAll('#result_list input.action-select[name="_selected_action"], #result_list input[name="_selected_action"]')
    ).filter(function (checkbox) { return !checkbox.disabled; });
  }

  function setHidden(selector, hidden) {
    document.querySelectorAll(selector).forEach(function (node) {
      node.hidden = hidden;
    });
  }

  function setBulkExpanded(isActive) {
    document.querySelectorAll('[data-scmd-bulkbar]').forEach(function (bar) {
      bar.classList.toggle('is-active', isActive);
      bar.classList.toggle('is-idle', !isActive);
    });
    setHidden('[data-scmd-bulk-active], [data-scmd-bulk-active-note], [data-scmd-bulk-expanded]', !isActive);
    setHidden('[data-scmd-bulk-idle], [data-scmd-bulk-idle-note]', isActive);
  }

  function updateBulkCount() {
    var selected = rowCheckboxes().filter(function (checkbox) { return checkbox.checked; }).length;
    document.querySelectorAll('[data-scmd-bulk-count]').forEach(function (target) {
      target.textContent = String(selected);
    });
    setBulkExpanded(selected > 0);
  }

  function setVisibleRows(checked) {
    rowCheckboxes().forEach(function (checkbox) {
      checkbox.checked = checked;
      checkbox.dispatchEvent(new Event('change', { bubbles: true }));
    });
    var headerToggle = document.querySelector('#result_list input#action-toggle');
    if (headerToggle && !headerToggle.disabled) {
      headerToggle.checked = checked;
      headerToggle.dispatchEvent(new Event('change', { bubbles: true }));
    }
    updateBulkCount();
  }

  function focusActionSelect() {
    var actionSelect = document.querySelector('select[name="action"]');
    if (!actionSelect) { return; }
    actionSelect.scrollIntoView({ behavior: 'smooth', block: 'center' });
    actionSelect.focus();
  }

  function announceBulkStatus(message) {
    document.querySelectorAll('[data-scmd-bulk-status]').forEach(function (target) {
      target.setAttribute('data-scmd-bulk-message', message);
    });
  }


  function selectedRowIds() {
    return rowCheckboxes()
      .filter(function (checkbox) { return checkbox.checked; })
      .map(function (checkbox) { return checkbox.value; })
      .filter(Boolean);
  }

  function printSelectedProfiles(button) {
    var bar = button.closest('[data-scmd-bulkbar]');
    var baseUrl = bar ? bar.getAttribute('data-scmd-print-selected-url') : '';
    var ids = selectedRowIds();
    if (!baseUrl || !ids.length) {
      announceBulkStatus('Chưa có dòng nào được chọn để in hồ sơ');
      return;
    }
    var sep = baseUrl.indexOf('?') >= 0 ? '&' : '?';
    window.open(baseUrl + sep + 'ids=' + encodeURIComponent(ids.join(',')), '_blank', 'noopener');
    announceBulkStatus('Đã mở trang in hồ sơ đã chọn');
  }

  function copyCurrentFilterUrl() {
    var value = window.location.href;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(value).then(function () {
        announceBulkStatus('Đã sao chép URL bộ lọc');
      }).catch(function () {
        window.prompt('Sao chép URL bộ lọc', value);
      });
      return;
    }
    window.prompt('Sao chép URL bộ lọc', value);
  }

  document.addEventListener('click', function (event) {
    var button = event.target.closest('[data-scmd-bulk-action]');
    if (!button) { return; }
    var action = button.getAttribute('data-scmd-bulk-action');
    if (action === 'select-visible') {
      setVisibleRows(true);
    } else if (action === 'clear') {
      setVisibleRows(false);
    } else if (action === 'copy-filter') {
      copyCurrentFilterUrl();
    } else if (action === 'print-selected') {
      printSelectedProfiles(button);
    } else if (action === 'open-action') {
      focusActionSelect();
    }
  });

  document.addEventListener('change', function (event) {
    if (event.target && event.target.matches('input[name="_selected_action"], #action-toggle')) {
      window.setTimeout(updateBulkCount, 0);
    }
  });

  document.addEventListener('DOMContentLoaded', updateBulkCount);
})();
