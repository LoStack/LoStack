function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function createServiceIcon(iconName, size = 50) {
    if (!iconName) return createFallbackIcon(size);
    
    const iconElement = document.createElement('div');
    Object.assign(iconElement.style, {
        width: `${size}px`,
        height: `${size}px`,
        maxWidth: '100%',
        maxHeight: '100%',
        flexShrink: '0'
    });
    
    if (iconName.startsWith('mdi-')) {
        const mdiIconName = iconName.substring(4);
        Object.assign(iconElement.style, {
            background: 'linear-gradient(180deg, rgb(var(--color-logo-start, 255, 255, 255)), rgb(var(--color-logo-stop, 200, 200, 200)))',
            mask: `url("/svg/${mdiIconName}.svg") center center / contain no-repeat`,
            webkitMask: `url("/static/svg/material-design-icons/${mdiIconName}.svg") center center / contain no-repeat`
        });
        iconElement.className = 'mdi-icon';
        iconElement.setAttribute('data-icon-type', 'mdi');
        iconElement.setAttribute('data-icon-name', mdiIconName);
    } else {
        const img = document.createElement('img');
        Object.assign(img, {
            alt: `${iconName} logo`,
            loading: 'lazy',
            width: size,
            height: size,
            decoding: 'async',
            src: `/static/png/dashboard-icons/${iconName}.png`
        });
        Object.assign(img.style, {
            color: 'transparent',
            width: `${size}px`,
            height: `${size}px`,
            objectFit: 'contain',
            maxHeight: '100%',
            maxWidth: '100%'
        });
        
        img.onerror = function() {
            console.warn(`Dashboard icon not found: ${iconName}`);
            iconElement.replaceWith(createFallbackIcon(size));
        };
        
        iconElement.appendChild(img);
        iconElement.className = 'dashboard-icon';
        iconElement.setAttribute('data-icon-type', 'dashboard');
        iconElement.setAttribute('data-icon-name', iconName);
    }
    
    return iconElement;
}

function createFallbackIcon(size = 50) {
    const fallbackElement = document.createElement('div');
    Object.assign(fallbackElement.style, {
        width: `${size}px`,
        height: `${size}px`,
        maxWidth: '100%',
        maxHeight: '100%',
        flexShrink: '0',
        background: 'linear-gradient(180deg, rgb(var(--color-logo-start, 255, 255, 255)), rgb(var(--color-logo-stop, 200, 200, 200)))',
        mask: `url("/static/svg/material-design-icons/application.svg") center center / contain no-repeat`,
        webkitMask: `url("/static/svg/material-design-icons/application.svg") center center / contain no-repeat`
    });
    
    fallbackElement.className = 'mdi-icon';
    fallbackElement.setAttribute('data-icon-type', 'mdi');
    fallbackElement.setAttribute('data-icon-name', 'application');
    
    return fallbackElement;
}

function extractIconFromLabels(labels) {
    if (!Array.isArray(labels)) return null;
    
    for (const label of labels) {
        if (label.startsWith('homepage.icon=')) {
            return label.split('=', 2)[1];
        }
    }
    return null;
}

 // Auto-dismiss alerts after 5 seconds
setTimeout(function() {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    });
}, 5000);

function toggleService(serviceId) {
    fetch(`/services/action/${serviceId}/toggle`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Network error occurred');
    });
}

function toggleServiceAccessControl(serviceId) {
    fetch(`/services/action/${serviceId}/toggle_access`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Network error occurred');
    });
}

function toggleServiceAutostart(serviceId) {
    fetch(`/services/action/${serviceId}/toggle_autostart`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Network error occurred');
    });
}


function toggleServiceAutoupdate(serviceId) {
    fetch(`/services/action/${serviceId}/toggle_autoupdate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Network error occurred');
    });
}


// Terminal Modal Class
// Used in a lot of places
class TerminalModal {
    constructor() {
        this.modal = null;
        this.log = null;
        this.ansi_up = new AnsiUp();
        this.es = null;
        this.autoscroll = true;
        this.wrapLines = false;
        this.isPaused = false;
        this.messageBuffer = [];
        this.streamEnded = false;
        this.streamEndTimeout = null;
        this.reloadOnClose = false;
    }

    launch(streamUrl) {
        this.modal = new bootstrap.Modal(document.getElementById('terminalModal'), {
            backdrop: 'static',
            keyboard: false
        });
        
        this.log = document.getElementById('modalLog');
        this.setupEventListeners();
        this.initializeEventSource(streamUrl);
        
        // Show the modal
        this.modal.show();
        
        // Clear any previous content
        this.log.innerHTML = '';
        this.streamEnded = false;
        this.reloadOnClose = false;
        
        // Update status
        document.getElementById('streamStatus').textContent = 'Connecting...';
        document.getElementById('streamStatus').className = 'badge bg-warning';
        document.getElementById('doneButton').disabled = false;
    }

    initializeEventSource(streamUrl) {
        this.es = new EventSource(streamUrl);
        
        this.es.onopen = () => {
            document.getElementById('streamStatus').textContent = 'Connected';
            document.getElementById('streamStatus').className = 'badge bg-success';
        };
        
        this.es.onmessage = (e) => {
            if (this.isPaused) {
                this.messageBuffer.push(e.data);
                return;
            }
            this.appendMessage(e.data);
        };
        
        this.es.onerror = (err) => {
            console.log("EventSource closed:", err);
            this.handleStreamEnd();
        };
    }

    handleStreamEnd() {
        if (this.streamEnded) return;
        
        this.streamEnded = true;
        this.appendMessage('\x1b[32m\nStream completed\x1b[0m');
        
        // Update status
        document.getElementById('streamStatus').textContent = 'Completed';
        document.getElementById('streamStatus').className = 'badge bg-success';
        // document.getElementById('doneButton').disabled = false;
        
        // Close event source
        if (this.es) {
            this.es.close();
            this.es = null;
        }
        
        this.reloadOnClose = true;
    }

    appendMessage(data) {
        const html = this.ansi_up.ansi_to_html(data);
        const messageElement = document.createElement('div');
        messageElement.innerHTML = html;
        this.log.appendChild(messageElement);
        
        if (this.autoscroll) {
            this.scrollToBottom();
        }
    }

    scrollToBottom() {
        this.log.scrollTop = this.log.scrollHeight;
    }

    setupEventListeners() {
        // Auto-scroll toggle
        const autoscrollToggle = document.getElementById('modalAutoscrollToggle');
        autoscrollToggle.addEventListener('change', () => {
            this.autoscroll = autoscrollToggle.checked;
            if (this.autoscroll) {
                this.scrollToBottom();
            }
        });

        // Line wrapping toggle
        const wrapLinesToggle = document.getElementById('modalWrapLinesToggle');
        wrapLinesToggle.addEventListener('change', () => {
            this.wrapLines = wrapLinesToggle.checked;
            this.updateLineWrapping();
        });

        // Copy button
        document.getElementById('modalCopyButton').addEventListener('click', () => {
            this.copyToClipboard();
        });

        // Pause/Resume button
        document.getElementById('modalPauseButton').addEventListener('click', () => {
            this.togglePause();
        });

        // Done button
        document.getElementById('doneButton').addEventListener('click', () => {
            this.closeAndReload();
        });

        // Auto-scroll detection
        this.log.addEventListener('scroll', () => {
            const isAtBottom = this.log.scrollTop + this.log.clientHeight >= this.log.scrollHeight - 5;
            if (isAtBottom !== this.autoscroll) {
                this.autoscroll = isAtBottom;
                autoscrollToggle.checked = isAtBottom;
            }
        });

        document.getElementById('terminalModal').addEventListener('hidden.bs.modal', () => {
            this.cleanup();
            if (this.reloadOnClose) {
                location.reload();
            }
        });
    }

    updateLineWrapping() {
        if (this.wrapLines) {
            this.log.style.whiteSpace = 'pre-wrap';
            this.log.style.overflowX = 'hidden';
        } else {
            this.log.style.whiteSpace = 'pre';
            this.log.style.overflowX = 'auto';
        }
    }

    async copyToClipboard() {
        try {
            const text = this.log.textContent || this.log.innerText;
            await navigator.clipboard.writeText(text);
            this.showToast('modalCopyToast');
        } catch (err) {
            console.error('Failed to copy: ', err);
        }
    }

    togglePause() {
        this.isPaused = !this.isPaused;
        const pauseButton = document.getElementById('modalPauseButton');
        
        if (this.isPaused) {
            pauseButton.textContent = 'Resume';
            pauseButton.classList.remove('btn-outline-warning');
            pauseButton.classList.add('btn-outline-success');
            document.getElementById('modalPauseToastText').textContent = 'Stream paused';
        } else {
            pauseButton.textContent = 'Pause';
            pauseButton.classList.remove('btn-outline-success');
            pauseButton.classList.add('btn-outline-warning');
            document.getElementById('modalPauseToastText').textContent = 'Stream resumed';
            
            // Process buffered messages
            while (this.messageBuffer.length > 0) {
                this.appendMessage(this.messageBuffer.shift());
            }
        }
        
        this.showToast('modalPauseToast');
    }

    showToast(toastId) {
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            delay: 2000
        });
        toast.show();
    }

    closeAndReload() {
        if (this.streamEndTimeout) {
            clearTimeout(this.streamEndTimeout);
            this.streamEndTimeout = null;
        }
        this.reloadOnClose = true;
        this.modal.hide();
    }

    cleanup() {
        if (this.es) {
            this.es.close();
            this.es = null;
        }
        if (this.streamEndTimeout) {
            clearTimeout(this.streamEndTimeout);
            this.streamEndTimeout = null;
        }
        this.messageBuffer = [];
    }
}

// Global terminal modal
const terminalModal = new TerminalModal();

// Global function to launch terminal modal
function launchTerminalModal(streamUrl) {
    terminalModal.launch(streamUrl);
}

// Animated spinning loading button
function launchTerminalWithButtonAnimation(streamUrl, buttonElement = null) {
    if (buttonElement) {
        buttonElement.disabled = false;
        const originalContent = buttonElement.innerHTML;
        buttonElement.innerHTML = '<i class="spinner-border spinner-border-sm me-2"></i>Processing...';
        
        setTimeout(() => {
            // buttonElement.disabled = false;
            buttonElement.innerHTML = originalContent;
        }, 2000);
    }
    launchTerminalModal(streamUrl);
}