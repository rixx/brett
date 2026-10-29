document.addEventListener('DOMContentLoaded', () => {
    const dialog = document.getElementById('card-dialog');
    const closeBtn = document.getElementById('close-dialog-btn');
    const permalink = document.getElementById('card-permalink');

    // Handle card clicks to open dialog
    document.addEventListener('click', (event) => {
        const trigger = event.target.closest('.card-open-dialog');
        if (!trigger) return;
        // Buttons and links inside a clickable card keep their own behaviour.
        const interactive = event.target.closest('a, button, input, select, textarea, form');
        if (interactive && interactive !== trigger) return;
        event.preventDefault();
        openCardDialog(trigger.closest('[data-card-id]').dataset.cardId);
    });

    // Close button
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            dialog.close();
        });
    }

    // Close dialog when clicking outside of it (on backdrop)
    if (dialog) {
        dialog.addEventListener('click', (event) => {
            const rect = dialog.getBoundingClientRect();
            const isInDialog = (
                rect.top <= event.clientY &&
                event.clientY <= rect.top + rect.height &&
                rect.left <= event.clientX &&
                event.clientX <= rect.left + rect.width
            );
            if (!isInDialog) {
                dialog.close();
            }
        });
    }

    // Open card dialog and load card details
    function openCardDialog(cardId) {
        // Set permalink
        permalink.href = `/card/${cardId}/`;

        // Load card content via HTMX
        htmx.ajax('GET', `/card/${cardId}/`, {
            target: '#card-dialog-content',
            swap: 'innerHTML'
        }).then(() => {
            dialog.showModal();
        });
    }
});
