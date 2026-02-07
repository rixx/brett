document.addEventListener('DOMContentLoaded', () => {
    const dialog = document.getElementById('card-dialog');
    const closeBtn = document.getElementById('close-dialog-btn');
    const permalink = document.getElementById('card-permalink');

    // Handle card link clicks to open dialog
    document.addEventListener('click', (event) => {
        const cardLink = event.target.closest('.card-open-dialog');
        if (cardLink) {
            event.preventDefault();
            const cardId = cardLink.closest('.card').dataset.cardId;
            openCardDialog(cardId);
        }
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

    // Drag and Drop functionality
    let draggedCard = null;

    // Handle dragstart on cards
    document.addEventListener('dragstart', (event) => {
        const card = event.target.closest('.draggable');
        if (card) {
            draggedCard = card;
            card.classList.add('dragging');
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/html', card.innerHTML);
        }
    });

    // Handle dragend on cards
    document.addEventListener('dragend', (event) => {
        const card = event.target.closest('.draggable');
        if (card) {
            card.classList.remove('dragging');
        }
    });

    // Handle dragover on drop zones
    document.addEventListener('dragover', (event) => {
        const dropZone = event.target.closest('.drop-zone');
        if (dropZone && draggedCard) {
            event.preventDefault();
            event.dataTransfer.dropEffect = 'move';
            dropZone.classList.add('drag-over');
        }
    });

    // Handle dragleave on drop zones
    document.addEventListener('dragleave', (event) => {
        const dropZone = event.target.closest('.drop-zone');
        if (dropZone && !dropZone.contains(event.relatedTarget)) {
            dropZone.classList.remove('drag-over');
        }
    });

    // Handle drop on drop zones
    document.addEventListener('drop', (event) => {
        const dropZone = event.target.closest('.drop-zone');
        if (dropZone && draggedCard) {
            event.preventDefault();
            dropZone.classList.remove('drag-over');

            const cardId = draggedCard.dataset.cardId;
            const newColumnId = dropZone.dataset.columnId;
            const oldDropZone = draggedCard.parentElement;

            // Optimistic UI update - move card immediately
            dropZone.appendChild(draggedCard);

            // Get CSRF token
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

            // Make POST request to update server
            fetch(`/card/${cardId}/move/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken,
                },
                body: `column_id=${newColumnId}`
            }).then(response => {
                if (!response.ok) {
                    // Revert on error
                    oldDropZone.appendChild(draggedCard);
                    alert('Failed to move card');
                }
            }).catch(error => {
                // Revert on error
                oldDropZone.appendChild(draggedCard);
                console.error('Error moving card:', error);
                alert('Failed to move card');
            });

            draggedCard = null;
        }
    });
});
