let currentTab = 'pending';
let videos = [];

// Fetch videos on load
document.addEventListener('DOMContentLoaded', fetchVideos);

async function fetchVideos() {
    try {
        const response = await fetch('/api/videos');
        videos = await response.json();
        renderVideos();
    } catch (error) {
        console.error('Error fetching videos:', error);
        document.getElementById('video-grid').innerHTML = '<div class="col-span-full text-center text-red-400">Failed to load videos. Is the backend running?</div>';
    }
}

function switchTab(tab) {
    currentTab = tab;
    
    // Update styling
    const tabs = ['pending', 'staging', 'archive'];
    tabs.forEach(t => {
        const el = document.getElementById(`tab-${t}`);
        if (t === tab) {
            el.className = 'px-4 py-2 text-purple-400 font-semibold border-b-2 border-purple-500';
        } else {
            el.className = 'px-4 py-2 text-gray-400 font-medium hover:text-white transition';
        }
    });
    
    renderVideos();
}

function renderVideos() {
    const grid = document.getElementById('video-grid');
    grid.innerHTML = '';
    
    let filteredVideos = [];
    
    if (currentTab === 'pending') {
        filteredVideos = videos.filter(v => v.status === 'pending_staging');
    } else if (currentTab === 'staging') {
        filteredVideos = videos.filter(v => v.status === 'staging');
    } else if (currentTab === 'archive') {
        filteredVideos = videos.filter(v => v.status === 'uploaded');
    }
    
    if (filteredVideos.length === 0) {
        grid.innerHTML = `<div class="col-span-full text-center text-gray-500 py-10 italic">No videos in this category.</div>`;
        return;
    }
    
    filteredVideos.forEach(v => {
        const card = document.createElement('div');
        card.className = 'glass-panel p-4 rounded-xl video-card flex flex-col';
        
        let statusTag = '';
        let actionButtons = '';
        
        if (v.status === 'pending_staging') {
            const expDate = new Date(v.exported_at);
            const stagingDate = new Date(expDate.getTime() + (12 * 60 * 60 * 1000));
            statusTag = `<span class="bg-blue-500/20 text-blue-300 text-xs px-2 py-1 rounded-full border border-blue-500/30">Moves to Staging at ${stagingDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>`;
            actionButtons = `
                <button onclick="postNow(${v.id})" class="flex-1 bg-purple-600 hover:bg-purple-500 text-white text-sm py-2 rounded-lg transition">Post Now</button>
                <button onclick="deleteVideo(${v.id})" class="flex-1 bg-red-600/50 hover:bg-red-500 text-white text-sm py-2 rounded-lg transition">Delete</button>
            `;
        } else if (v.status === 'staging') {
            const stagedDate = new Date(v.exported_at); // Total 3 days from export
            const uploadDate = new Date(stagedDate.getTime() + (3 * 24 * 60 * 60 * 1000));
            
            // Format remaining time nicely
            const now = new Date();
            const diff = uploadDate - now;
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
            
            statusTag = `<span class="bg-purple-500/20 text-purple-300 text-xs px-2 py-1 rounded-full border border-purple-500/30">Auto-upload in ${days}d ${hours}h</span>`;
            actionButtons = `
                <button onclick="postNow(${v.id})" class="flex-1 bg-purple-600 hover:bg-purple-500 text-white text-sm py-2 rounded-lg transition">Post Now</button>
                <button onclick="deleteVideo(${v.id})" class="flex-1 bg-red-600/50 hover:bg-red-500 text-white text-sm py-2 rounded-lg transition">Delete</button>
            `;
        } else if (v.status === 'uploaded') {
            const upDate = new Date(v.uploaded_at);
            const delDate = new Date(upDate.getTime() + (7 * 24 * 60 * 60 * 1000));
            statusTag = `<span class="bg-green-500/20 text-green-300 text-xs px-2 py-1 rounded-full border border-green-500/30">Uploaded! (Deletes on ${delDate.toLocaleDateString()})</span>`;
            actionButtons = `
                <button onclick="deleteVideo(${v.id})" class="w-full bg-gray-600 hover:bg-red-500 text-white text-sm py-2 rounded-lg transition">Delete Now</button>
            `;
        }
        
        card.innerHTML = `
            <div class="relative w-full aspect-video bg-black rounded-lg mb-4 overflow-hidden group cursor-pointer" onclick="playVideo(${v.id})">
                <div class="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:bg-black/20 transition">
                    <svg class="w-12 h-12 text-white/80 group-hover:text-white group-hover:scale-110 transition" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"></path></svg>
                </div>
            </div>
            <h3 class="font-semibold truncate mb-1" title="${v.filename}">${v.filename}</h3>
            <div class="mb-4 mt-1">${statusTag}</div>
            <div class="mt-auto flex space-x-2">
                ${actionButtons}
            </div>
        `;
        grid.appendChild(card);
    });
}

function playVideo(id) {
    const modal = document.getElementById('videoModal');
    const player = document.getElementById('modalVideoPlayer');
    player.src = `/stream/${id}`;
    modal.classList.remove('hidden');
    player.play();
}

function closeModal() {
    const modal = document.getElementById('videoModal');
    const player = document.getElementById('modalVideoPlayer');
    player.pause();
    player.src = '';
    modal.classList.add('hidden');
}

async function postNow(id) {
    if (!confirm("Are you sure you want to upload this to Instagram immediately?")) return;
    try {
        const res = await fetch(`/api/video/${id}/post_now`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            alert('Video posted successfully!');
            fetchVideos();
        } else {
            alert('Failed: ' + data.error);
        }
    } catch (e) {
        alert('Error communicating with server.');
    }
}

async function deleteVideo(id) {
    if (!confirm("Delete this video? This cannot be undone.")) return;
    try {
        const res = await fetch(`/api/video/${id}/delete`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            fetchVideos();
        } else {
            alert('Failed: ' + data.error);
        }
    } catch (e) {
        alert('Error communicating with server.');
    }
}

// Upload drag and drop stub
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');

dropzone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFiles);
dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('bg-purple-500/20'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('bg-purple-500/20'));
dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('bg-purple-500/20');
    if (e.dataTransfer.files.length) {
        handleFiles({ target: { files: e.dataTransfer.files } });
    }
});

function handleFiles(e) {
    // Note: Actually moving files via a browser input isn't allowed to access D:\ directly on the backend easily.
    // In a real local app, this would use a multipart form upload to the Flask server, which saves it to the Premiere Folder.
    alert("Manual drag-and-drop upload functionality would upload the file here. (Requires additional backend endpoint)");
}
