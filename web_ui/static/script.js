// Pipeline 3-LLM Web UI - JavaScript

const API_BASE = '/api';

// Form submission
document.getElementById('input-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(document.getElementById('input-form'));
    const data = {
        kelas: formData.get('kelas'),
        mata_pelajaran: formData.get('mata_pelajaran'),
        bab: formData.get('bab'),
        subbab: formData.get('subbab') || '',
        topik: formData.get('topik') || ''
    };

    // Validate
    if (!data.kelas || !data.mata_pelajaran || !data.bab) {
        showError('Silakan isi semua field yang diperlukan (*)');
        return;
    }

    // Show loading
    showLoading(true);

    try {
        const response = await fetch(`${API_BASE}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Error generating game');
        }

        console.log('✅ Game generated:', result);
        showLoading(false);

        // Load preview
        await loadPreview();

        // Switch to preview section
        switchSection('preview-section');

    } catch (error) {
        console.error('❌ Error:', error);
        showError(error.message);
        showLoading(false);
    }
});

/**
 * Load game preview dalam iframe
 */
async function loadPreview() {
    try {
        const response = await fetch(`${API_BASE}/preview`);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Error loading preview');
        }

        const iframe = document.getElementById('game-preview');
        iframe.srcdoc = result.html;

    } catch (error) {
        console.error('❌ Preview Error:', error);
        showError('Gagal load preview: ' + error.message);
    }
}

/**
 * Submit revision feedback
 */
async function submitRevision() {
    const feedback = document.getElementById('feedback-input').value.trim();

    if (!feedback) {
        alert('Silakan isi feedback revisi');
        return;
    }

    closeRevisionModal();
    showLoading(true);

    try {
        const response = await fetch(`${API_BASE}/revise`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ feedback })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Error during revision');
        }

        console.log('✅ Revision applied:', result);
        showLoading(false);

        // Reload preview
        await loadPreview();

        showMessage(`📝 Game direvisi (kategori: ${result.category})`, 'publish-message');

    } catch (error) {
        console.error('❌ Revision Error:', error);
        showError('Gagal revisi game: ' + error.message);
        showLoading(false);
    }
}

/**
 * Publish game
 */
async function publishGame() {
    if (!confirm('Publish game ke database?')) {
        return;
    }

    showLoading(true);

    try {
        const response = await fetch(`${API_BASE}/publish`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Error publishing game');
        }

        console.log('✅ Game published:', result);
        showLoading(false);

        // Show success message
        const successMsg = document.getElementById('success-message');
        successMsg.innerHTML = `
            <strong>${result.message}</strong><br>
            Game ID: <code>${result.game_id}</code><br>
            File: <code>${result.file}</code>
        `;

        // Switch to success section
        switchSection('success-section');

    } catch (error) {
        console.error('❌ Publish Error:', error);
        showError('Gagal publikasi game: ' + error.message);
        showLoading(false);
    }
}

/**
 * Go back to input
 */
function goBack() {
    if (confirm('Kembali ke input? Game akan direset.')) {
        switchSection('input-section');
    }
}

/**
 * Show revision modal
 */
function showRevisionModal() {
    document.getElementById('revision-modal').classList.remove('hidden');
}

/**
 * Close revision modal
 */
function closeRevisionModal() {
    document.getElementById('revision-modal').classList.add('hidden');
    document.getElementById('feedback-input').value = '';
}

/**
 * Reset form and start new game
 */
function resetForm() {
    document.getElementById('input-form').reset();
    document.getElementById('feedback-input').value = '';
    switchSection('input-section');
    hideAllMessages();
}

/**
 * Switch between sections
 */
function switchSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => {
        s.classList.remove('active');
    });
    document.getElementById(sectionId).classList.add('active');
}

/**
 * Show loading state
 */
function showLoading(show) {
    const loadingMsg = document.getElementById('loading-message');
    const submitBtn = document.querySelector('#input-form button[type="submit"]');

    if (show) {
        loadingMsg.classList.remove('hidden');
        submitBtn.disabled = true;
    } else {
        loadingMsg.classList.add('hidden');
        submitBtn.disabled = false;
    }
}

/**
 * Show error message
 */
function showError(message) {
    const errorMsg = document.getElementById('error-message');
    errorMsg.textContent = '❌ Error: ' + message;
    errorMsg.classList.remove('hidden');
}

/**
 * Show success message
 */
function showMessage(message, elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = message;
        element.classList.remove('hidden');
    }
}

/**
 * Hide all messages
 */
function hideAllMessages() {
    document.getElementById('error-message').classList.add('hidden');
    document.getElementById('loading-message').classList.add('hidden');
    document.getElementById('publish-message').classList.add('hidden');
}

/**
 * Close modal on outside click
 */
document.addEventListener('click', (e) => {
    const modal = document.getElementById('revision-modal');
    if (e.target === modal) {
        closeRevisionModal();
    }
});

/**
 * Close modal on Escape key
 */
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeRevisionModal();
    }
});
