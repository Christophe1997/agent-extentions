// Timestamps: convert UTC to local
document.querySelectorAll('time[data-timestamp]').forEach(function(el) {
    var ts = el.getAttribute('data-timestamp');
    var d = new Date(ts);
    var now = new Date();
    var time = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    if (d.toDateString() === now.toDateString()) {
        el.textContent = time;
    } else {
        el.textContent = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ' ' + time;
    }
});

// Truncation - use event delegation for resilience against DOM changes
function initTruncation() {
    document.querySelectorAll('.truncatable').forEach(function(w) {
        var c = w.querySelector('.truncatable-content');
        var b = w.querySelector('.expand-btn');
        if (c && c.scrollHeight > 250) {
            w.classList.add('truncated');
        }
    });
}

// Event delegation for expand buttons (works after DOM changes)
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('expand-btn')) {
        var w = e.target.closest('.truncatable');
        if (w) {
            if (w.classList.contains('truncated')) {
                w.classList.remove('truncated');
                w.classList.add('expanded');
                e.target.textContent = 'Show less';
            } else {
                w.classList.remove('expanded');
                w.classList.add('truncated');
                e.target.textContent = 'Show more';
            }
        }
    }
});

// Initialize truncation on load
initTruncation();

// Keyboard navigation for pagination
document.addEventListener('keydown', function(e) {
    var prev = document.querySelector('.pagination .prev');
    var next = document.querySelector('.pagination .next');
    if (e.key === 'ArrowLeft' && prev) prev.click();
    if (e.key === 'ArrowRight' && next) next.click();
});
