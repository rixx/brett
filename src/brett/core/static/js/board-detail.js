document.addEventListener('DOMContentLoaded', () => {
    // Stats dialog
    const statsDialog = document.getElementById('stats-dialog');

    document.addEventListener('click', (event) => {
        const statsBtn = event.target.closest('#open-stats-btn');
        if (statsBtn && statsDialog) {
            const url = statsBtn.dataset.statsUrl;
            htmx.ajax('GET', url, {
                target: '#stats-dialog-content',
                swap: 'innerHTML'
            }).then(() => {
                statsDialog.showModal();
            });
        }

        if (event.target.closest('#close-stats-btn')) {
            statsDialog.close();
        }
    });

    if (statsDialog) {
        statsDialog.addEventListener('click', (event) => {
            const rect = statsDialog.getBoundingClientRect();
            const isInDialog = (
                rect.top <= event.clientY &&
                event.clientY <= rect.top + rect.height &&
                rect.left <= event.clientX &&
                event.clientX <= rect.left + rect.width
            );
            if (!isInDialog) {
                statsDialog.close();
            }
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

            // Optimistic UI update - insert at top of column so the user can
            // continue acting on the card without scrolling
            dropZone.prepend(draggedCard);

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
