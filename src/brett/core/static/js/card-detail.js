document.addEventListener('DOMContentLoaded', () => {
    // Toggle entry expansion - use event delegation for dynamically loaded content
    document.addEventListener('click', (event) => {
        const entryToggle = event.target.closest('.entry-toggle');
        if (entryToggle) {
            const entry = entryToggle.closest('.entry');
            const entryId = entry.dataset.entryId;
            const entryBody = document.getElementById(`entry-body-${entryId}`);

            if (entryBody) {
                if (entryBody.style.display === 'none' || entryBody.style.display === '') {
                    entryBody.style.display = 'block';
                } else {
                    entryBody.style.display = 'none';
                }
            }
        }
    });

    // Keyboard shortcut: [n] to navigate to import page
    document.addEventListener('keydown', (event) => {
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
        if (event.key === 'n') {
            window.location.href = '/import/';
        }
    });

    // Copy message ID to clipboard - use event delegation
    document.addEventListener('click', (event) => {
        const copyBtn = event.target.closest('.copy-message-id');
        if (copyBtn) {
            event.stopPropagation(); // Don't toggle entry
            const messageId = copyBtn.dataset.messageId;

            navigator.clipboard.writeText(messageId).then(() => {
                // Visual feedback
                const originalText = copyBtn.textContent;
                copyBtn.textContent = '✓';
                copyBtn.classList.add('copied');

                setTimeout(() => {
                    copyBtn.textContent = originalText;
                    copyBtn.classList.remove('copied');
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy message ID:', err);
                alert('Failed to copy message ID');
            });
        }
    });
});
