/**
 * HR Alert History Manager
 * Xử lý việc lấy dữ liệu từ API và hiển thị lên bảng Dashboard.
 */
document.addEventListener('DOMContentLoaded', function() {
    const alertsBody = document.getElementById('hr-alerts-body');
    const alertsEmpty = document.getElementById('hr-alerts-empty');
    const refreshBtn = document.getElementById('refresh-alerts');
    const searchInput = document.getElementById('hr-alert-search');
    const statusFilter = document.getElementById('hr-alert-status-filter');
    const startDateInput = document.getElementById('hr-alert-start-date');
    const endDateInput = document.getElementById('hr-alert-end-date');
    const pageSizeSelector = document.getElementById('hr-alert-page-size');
    const paginationRow = document.getElementById('hr-alerts-pagination');
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    const pageInfo = document.getElementById('pagination-info');
    const pageNumDisplay = document.getElementById('current-page-num');

    const apiUrl = '/users/api/v1/hr-alerts/';
    let debounceTimer;
    let currentPage = 1;
    let totalCount = 0;

    async function fetchAlertHistory(page = 1) {
        try {
            const params = new URLSearchParams();
            if (searchInput && searchInput.value) params.append('search', searchInput.value);
            if (statusFilter && statusFilter.value) params.append('status', statusFilter.value);
            if (startDateInput && startDateInput.value) params.append('start_date', startDateInput.value);
            if (endDateInput && endDateInput.value) params.append('end_date', endDateInput.value);
            if (pageSizeSelector) params.append('page_size', pageSizeSelector.value);
            params.append('page', page);

            const url = `${apiUrl}?${params.toString()}`;
            const response = await fetch(url);
            const data = await response.json();
            
            // data.data chứa danh sách kết quả từ SCMDPagination tùy chỉnh
            const alerts = data.data || [];
            totalCount = data.count || 0;
            currentPage = page;
            
            renderAlerts(alerts);
            updatePaginationUI(data);
        } catch (error) {
            console.error('Lỗi khi tải lịch sử thông báo:', error);
            alertsBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-10 text-error">
                        Không thể kết nối với máy chủ API.
                    </td>
                </tr>
            `;
        }
    }

    function updatePaginationUI(data) {
        const pageSize = pageSizeSelector ? parseInt(pageSizeSelector.value) : 10;
        if (totalCount > pageSize) {
            paginationRow.classList.remove('hidden');
            pageInfo.innerText = totalCount;
            pageNumDisplay.innerText = `Trang ${currentPage}`;
            prevBtn.disabled = !data.previous;
            nextBtn.disabled = !data.next;
        } else {
            paginationRow.classList.add('hidden');
        }
    }

    function renderAlerts(alerts) {
        if (!alerts || alerts.length === 0) {
            alertsBody.innerHTML = '';
            alertsEmpty.classList.remove('hidden');
            return;
        }

        alertsEmpty.classList.add('hidden');
        let html = '';
        
        alerts.forEach(alert => {
            const date = new Date(alert.timestamp);
            const timeStr = date.toLocaleDateString('vi-VN') + '<br>' + 
                           date.toLocaleTimeString('vi-VN', {hour: '2-digit', minute:'2-digit'});
            
            const statusClass = alert.status === 'SUCCESS' ? 'badge-success' : 'badge-warning';

            html += `
                <tr class="hover">
                    <td class="text-[11px] font-mono text-slate-500">${timeStr}</td>
                    <td>
                        <div class="font-bold text-slate-700 text-sm">${alert.title}</div>
                    </td>
                    <td>
                        <div class="text-xs text-slate-600 max-w-xs truncate md:max-w-md" title="${alert.message}">
                            ${alert.message}
                        </div>
                    </td>
                    <td class="text-center font-bold text-indigo-600">${alert.count}</td>
                    <td class="text-center">
                        <div class="badge ${statusClass} badge-outline text-[10px]">${alert.status}</div>
                    </td>
                </tr>
            `;
        });

        alertsBody.innerHTML = html;
    }

    // Khởi tạo và lắng nghe sự kiện
    if (alertsBody) {
        fetchAlertHistory();
        refreshBtn.addEventListener('click', () => {
            alertsBody.innerHTML = '<tr><td colspan="5" class="text-center py-10"><span class="loading loading-spinner"></span></td></tr>';
            fetchAlertHistory(1);
        });

        // Điều hướng trang
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (currentPage > 1) fetchAlertHistory(currentPage - 1);
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                fetchAlertHistory(currentPage + 1);
            });
        }

        // Lắng nghe tìm kiếm (Debounce 500ms để tránh gọi API liên tục)
        if (searchInput) {
            searchInput.addEventListener('input', () => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    fetchAlertHistory(1);
                }, 500);
            });
        }

        // Lắng nghe thay đổi bộ lọc trạng thái
        if (statusFilter) {
            statusFilter.addEventListener('change', () => fetchAlertHistory(1));
        }

        // Lắng nghe thay đổi khoảng ngày
        if (startDateInput) {
            startDateInput.addEventListener('change', () => fetchAlertHistory(1));
        }
        if (endDateInput) {
            endDateInput.addEventListener('change', () => fetchAlertHistory(1));
        }

        // Lắng nghe thay đổi kích thước trang
        if (pageSizeSelector) {
            pageSizeSelector.addEventListener('change', () => fetchAlertHistory(1));
        }
    }
});