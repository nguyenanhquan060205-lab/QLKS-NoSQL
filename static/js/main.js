// ====================================================================
// JAVASCRIPT CHUNG CHO TOÀN BỘ HỆ THỐNG
// PHỤ TRÁCH: NHƯ
// ====================================================================

console.log("Hệ thống Quản lý Khách sạn NoSQL đã sẵn sàng.");

// Ngăn gửi form nhiều lần và phản hồi ngay khi đang chờ Astra DB.
document.querySelectorAll('[data-submit-form]').forEach((form) => {
    form.addEventListener('submit', () => {
        const submitButton = form.querySelector('[data-submit-button]');
        if (!submitButton) return;

        submitButton.disabled = true;
        submitButton.setAttribute('aria-busy', 'true');
        const submittingText = submitButton.dataset.submittingText || 'Đang lưu...';
        submitButton.innerHTML = `
            <i class="bi bi-arrow-repeat animate-spin motion-reduce:animate-none" aria-hidden="true"></i>
            ${submittingText}
        `;
    });
});
