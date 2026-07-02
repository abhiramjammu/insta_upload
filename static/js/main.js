let currentTab = 'pending';
let allVideos = [];

// Pastel gradients for video card thumbnails (random, different per video)
const thumbGradients = [
    'linear-gradient(145deg, #EDE8FF, #FFE8F4)',
    'linear-gradient(145deg, #D4F0FF, #E8FFE8)',
    'linear-gradient(145deg, #FFF5D4, #FFE8F4)',
    'linear-gradient(145deg, #FFE8D4, #FFEAFF)',
    'linear-gradient(145deg, #D4FFE8, #D4EEFF)',
    'linear-gradient(145deg, #FFDDE1, #E3D4FF)',
    'linear-gradient(145deg, #D4ECFF, #FFD4F0)',
    'linear-gradient(145deg, #F0FFD4, #FFD4E8)',
];

function getGradient(id) {
    return thumbGradients[id % thumbGradients.length];
}

document.addEventListener('DOMContentLoaded', fetchVideos);

// Auto-refresh every 60 seconds
setInterval(fetchVideos, 60000);

async function fetchVideos() {
    try {
        const response = await fetch('/api/videos');
        allVideos = await response.json();
        updateStats();
        renderVideos();
    } catch (error) {
        console.error('Error fetching videos:', error);
        document.getElementById('video-grid').innerHTML = `
            <div class="empty-state" style="grid-column:1/-1">
                <div class="empty-icon">⚠️</div>
                <h4>Connection Error</h4>
                <p>Cannot reach the backend. Make sure the server is running.</p>
            </div>`;
    }
}

function updateStats() {
    const cooling = allVideos.filter(v => v.status === 'pending_staging').length;
    const queued  = allVideos.filter(v => v.status === 'staging').length;
    const uploaded = allVideos.filter(v => v.status === 'uploaded').length;
    const total = allVideos.length;

    animateNumber('stat-cooling', cooling);
    animateNumber('stat-queued', queued);
    animateNumber('stat-uploaded', uploaded);
    animateNumber('stat-total', total);

    document.getElementById('badge-pending').textContent = cooling;
    document.getElementById('badge-staging').textContent = queued;
    document.getElementById('badge-archive').textContent = uploaded;
}

function animateNumber(id, target) {
    const el = document.getElementById(id);
    const start = parseInt(el.textContent) || 0;
    const duration = 600;
    const startTime = performance.now();
    const update = (now) => {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(start + (target - start) * ease);
        if (progress < 1) requestAnimationFrame(update);
    };
    requestAnimationFrame(update);
}

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`tab-${tab}`).classList.add('active');
    renderVideos();
}

function renderVideos() {
    const grid = document.getElementById('video-grid');

    let filtered = [];
    if (currentTab === 'pending') filtered = allVideos.filter(v => v.status === 'pending_staging');
    else if (currentTab === 'staging') filtered = allVideos.filter(v => v.status === 'staging');
    else if (currentTab === 'archive') filtered = allVideos.filter(v => v.status === 'uploaded');

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column:1/-1">
                <div class="empty-icon">${currentTab === 'pending' ? '🎬' : currentTab === 'staging' ? '⏳' : '📸'}</div>
                <h4>Nothing here yet</h4>
                <p>${currentTab === 'pending' ? 'Export a video from Premiere Pro to see it appear here.' : currentTab === 'staging' ? 'Videos will appear here after the 12-hour cooldown.' : 'Successfully uploaded Reels will be archived here.'}</p>
            </div>`;
        return;
    }

    grid.innerHTML = '';
    filtered.forEach((v, i) => {
        const card = document.createElement('div');
        card.className = 'video-card';

        let statusBadge = '';
        let timeInfo = '';
        let actions = '';

        if (v.status === 'pending_staging') {
            const expDate = new Date(v.exported_at);
            const stagingDate = new Date(expDate.getTime() + 12 * 3600 * 1000);
            const remaining = stagingDate - new Date();
            const hrs = Math.max(0, Math.floor(remaining / 3600000));
            const mins = Math.max(0, Math.floor((remaining % 3600000) / 60000));
            statusBadge = `<span class="status-badge cooling"><span class="status-badge-dot"></span>Cooling</span>`;
            timeInfo = `<div class="card-time">Moves to staging in ${hrs}h ${mins}m</div>`;
            actions = `
                <button class="btn-post" onclick="event.stopPropagation();postNow(${v.id})">Post Now</button>
                <button class="btn-delete" onclick="event.stopPropagation();deleteVideo(${v.id})" title="Delete">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
                </button>`;
        } else if (v.status === 'staging') {
            const expDate = new Date(v.exported_at);
            const uploadDate = new Date(expDate.getTime() + 3 * 86400000);
            const diff = uploadDate - new Date();
            const days = Math.max(0, Math.floor(diff / 86400000));
            const hrs = Math.max(0, Math.floor((diff % 86400000) / 3600000));
            statusBadge = `<span class="status-badge staging"><span class="status-badge-dot"></span>Queued</span>`;
            timeInfo = `<div class="card-time">Auto-uploads in ${days}d ${hrs}h</div>`;
            actions = `
                <button class="btn-post" onclick="event.stopPropagation();postNow(${v.id})">Post Now</button>
                <button class="btn-delete" onclick="event.stopPropagation();deleteVideo(${v.id})" title="Delete">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
                </button>`;
        } else if (v.status === 'uploaded') {
            const upDate = new Date(v.uploaded_at);
            const delDate = new Date(upDate.getTime() + 7 * 86400000);
            statusBadge = `<span class="status-badge uploaded"><span class="status-badge-dot"></span>Posted</span>`;
            timeInfo = `<div class="card-time">Auto-deletes on ${delDate.toLocaleDateString('en-IN', {day:'numeric', month:'short'})}</div>`;
            actions = `
                <button class="btn-delete" style="flex:1;padding:8px 0" onclick="event.stopPropagation();deleteVideo(${v.id})">Delete from Archive</button>`;
        }

        card.innerHTML = `
            <div class="video-thumb" style="background:${getGradient(v.id)}" onclick="playVideo(${v.id})">
                <div class="video-thumb-inner">
                    <div class="play-btn-overlay">
                        <svg viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M8 5v14l11-7z"/></svg>
                    </div>
                </div>
            </div>
            <div class="video-card-body">
                <div class="video-filename" title="${v.filename}">${v.filename.replace(/\.[^.]+$/, '')}</div>
                ${statusBadge}
                ${timeInfo}
                <div class="card-actions">${actions}</div>
            </div>`;

        // Staggered entrance animation
        card.style.opacity = '0';
        card.style.transform = 'translateY(16px)';
        card.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
        grid.appendChild(card);
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, i * 50);
    });
}

function playVideo(id) {
    const modal = document.getElementById('videoModal');
    const player = document.getElementById('modalVideoPlayer');
    player.src = `/stream/${id}`;
    modal.classList.add('open');
    player.play();
}

function closeModal() {
    const modal = document.getElementById('videoModal');
    const player = document.getElementById('modalVideoPlayer');
    player.pause();
    player.src = '';
    modal.classList.remove('open');
}

// Close modal on backdrop click
document.getElementById('videoModal').addEventListener('click', function(e) {
    if (e.target === this) closeModal();
});

async function postNow(id) {
    if (!confirm('Post this Reel to Instagram right now?')) return;
    try {
        const res = await fetch(`/api/video/${id}/post_now`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('✅ Video posted to Instagram!');
            fetchVideos();
        } else {
            showToast('❌ Failed: ' + data.error);
        }
    } catch (e) {
        showToast('❌ Server error. Try again.');
    }
}

async function deleteVideo(id) {
    if (!confirm('Delete this video? This cannot be undone.')) return;
    try {
        const res = await fetch(`/api/video/${id}/delete`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('🗑️ Video deleted.');
            fetchVideos();
        } else {
            showToast('❌ Failed: ' + data.error);
        }
    } catch (e) {
        showToast('❌ Server error. Try again.');
    }
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3500);
}

// Drag and drop on sidebar
const dropzone = document.getElementById('dropzone');
dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('over'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('over'));
dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('over');
    showToast('💡 Tip: Place videos directly into your Premiere Pro folder for auto-processing!');
});
