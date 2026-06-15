window.addEventListener('load', function() {
    // Chỉ chạy mã này trên trang thêm/sửa của NhanVien
    if (document.querySelector('body.model-nhanvien.change-form')) {
        
        // Tìm đến khu vực chứa các tab
        const tabContainer = document.querySelector('.nav-tabs');
        if (!tabContainer) return;

        const tabs = Array.from(tabContainer.querySelectorAll('.nav-link'));
        const tabPanes = document.querySelectorAll('.tab-pane');

        tabPanes.forEach((pane, index) => {
            // Tạo một khu vực chứa nút ở cuối mỗi tab pane
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'next-tab-button-container';
            
            // Nếu không phải là tab cuối cùng, thêm nút "Tiếp theo"
            if (index < tabPanes.length - 1) {
                const nextButton = document.createElement('button');
                nextButton.type = 'button';
                nextButton.className = 'btn btn-info btn-next-tab';
                nextButton.innerText = 'Tiếp theo';
                
                nextButton.onclick = function() {
                    // Tìm và click vào tab tiếp theo
                    const nextTabLink = tabs[index + 1];
                    if (nextTabLink) {
                        nextTabLink.click();
                        // Cuộn lên đầu trang để người dùng thấy tab mới
                        window.scrollTo(0, 0);
                    }
                };
                
                buttonContainer.appendChild(nextButton);
            }
            
            pane.appendChild(buttonContainer);
        });
    }
});