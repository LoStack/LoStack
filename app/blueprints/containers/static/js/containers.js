let autoRefreshInterval = null;
let containerIdToRemove = null;
let allContainers = [];

async function fetchContainerData() {
    const response = await fetch('/containers/api/all');
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

async function refreshData() {
    hideError();
    try {
        const data = await fetchContainerData();
        allContainers = data.containers;
        updateSummaryPanel(allContainers);
        renderContainers(allContainers);
    } catch (error) {
        showError('Failed to load container data: ' + error.message);
    }
}

function updateSummaryPanel(containers) {
    document.getElementById('runningCount').textContent = containers.filter(c => c.State === 'running').length;
    document.getElementById('stoppedCount').textContent = containers.filter(c => c.State === 'exited').length;
    document.getElementById('totalCount').textContent = containers.length;
}


function renderContainers(containers) {
    const containerGrid = document.getElementById('containersCards');
    if (containers.length === 0) {
        containerGrid.innerHTML = `
<div class="col-12 text-center py-4">
    <i class="bi bi-inbox h2 d-block mb-2"></i>
    No containers found
</div>`;
        return;
    }

    containers.sort((a, b) => a.Names[0].localeCompare(b.Names[0]));
    containerGrid.innerHTML = containers.map(container => {
        const names = container.Names.map(n => n.replace('/', '')).join(', ');
        const statusBadge = getStatusBadge(container.State, container.Status);
        const imageSection = renderImage(container.Image);
        const portsSection = renderPorts(container.Ports || []);
        const volumesSection = renderVolumes(container.Mounts || []);
        const networksSection = renderNetworks(container.NetworkSettings);
        const labelsSection = renderLabels(container.Labels || {});
        const actionButtons = getActionButtons(container);

        // pick icon name (fallback to "docker" if nothing else is meaningful)
        const iconName = container.Labels && container.Labels['homepage.icon']
            ? container.Labels['homepage.icon']
            : 'docker';

        return `
<div class="col-sm-12 col-md-12 col-lg-6 col-xl-6 col-xxl-4">
    <div class="card service-card h-100 shadow">
        <div class="card-header bg-primary text-light">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                <h6 class="fw-semibold mb-0">${names}</h6>
                <div class="mt-1">${statusBadge}</div>
                </div>
                <span class="service-icon ms-2" data-icon="${iconName}"></span>
            </div>
        </div>
        <div class="card-body overflow-auto p-0 mx-0 my-0 d-flex flex-column shadow-sm">
            <div class="mt-2">
                ${imageSection}
                ${networksSection}
                ${portsSection}
                ${volumesSection}
                ${labelsSection}
            </div>
        </div>
        <div class="card-footer bg-transparent mx-2 px-0">
            ${actionButtons}
        </div>
    </div>
</div>`;
    }).join('');

    // now hydrate icons after HTML injection
    document.querySelectorAll('.service-icon').forEach(el => {
        const iconName = el.getAttribute('data-icon');
        const iconEl = createServiceIcon(iconName, 50);
        el.replaceWith(iconEl);
    });
}


function renderImage(image) {
    return `
<div class="mb-3 mx-2">
    <h6 class="small fw-bold text-muted mb-2">
        <i class="bi bi-box-seam-fill me-1 text-secondary"></i>Image
    </h6>
    <div class="small text-muted">
        <div class="ms-2 me-3 image-item d-flex align-items-center mb-1">
            <i class="bi bi-box me-2 text-secondary"></i>
            <code class="text-primary item-break">${image}</code>
        </div>
    </div>
</div>`;
}
function renderPorts(ports) {
    if (!ports.length) return '';
    return `
<div class="mb-3 mx-2">
    <h6 class="small fw-bold text-muted mb-2">
        <i class="bi bi-plug-fill me-1 text-secondary"></i>Ports
    </h6>
    <div class="small text-muted">
        ${ports.map(port => {
        const ip = port.IP && port.PublicPort ? `${port.IP}:${port.PublicPort}` : '<i>not exposed</i>';
        const privatePort = port.PrivatePort || '-';
        const type = (port.Type || '').toUpperCase();
        return `
            <div class="ms-2 me-2 port-item d-flex align-items-center justify-content-between mb-1">
            <div>
                <i class="bi bi-plug me-2 text-secondary"></i>
                <code class="text-primary item-break">${ip}</code>
                <i class="bi bi-arrow-right mx-2"></i>
                <code class="item-break">${privatePort}</code>
            </div>
            <span class="badge rounded-pill bg-info ms-2">${type}</span>
            </div>
        `;
    }).join('')}
    </div>
</div>`;
}

function renderNetworks(networkSettings) {
    if (!networkSettings || !networkSettings.Networks) return '';
    const networks = Object.keys(networkSettings.Networks);
    if (!networks.length) return '';

    return `
<div class="mb-3 mx-2">
    <h6 class="small fw-bold text-muted mb-2">
        <i class="bi bi-hdd-network-fill me-1 text-secondary"></i>Networks
    </h6>
    <div class="small text-muted">
        ${networks.map(networkName => {
        const network = networkSettings.Networks[networkName];
        const ipAddress = network.IPAddress || 'N/A';
        return `
            <div class="ms-2 me-2 network-item d-flex align-items-center justify-content-between mb-1">
            <div>
                <i class="bi bi-diagram-3 me-2 text-secondary"></i>
                <span class="text-primary">${networkName}</span>
                ${ipAddress !== 'N/A' ? `<code class="ms-2 item-break">${ipAddress}</code>` : ''}
            </div>
            <span class="badge rounded-pill bg-success ms-2">Connected</span>
            </div>
        `;
    }).join('')}
    </div>
</div>`;
}

function renderVolumes(mounts) {
    const binds = mounts.filter(m => m.Type === 'bind' || m.Type === 'volume');
    if (!binds.length) return '';
    return `
<div class="mb-3 mx-2">
    <h6 class="small fw-bold text-muted mb-2">
        <i class="bi bi-hdd-fill me-1 text-secondary"></i>Volumes
    </h6>
    <div class="small text-muted">
        ${binds.map(m => `
        <div class="ms-2 me-2 volume-item d-flex align-items-center justify-content-between mb-1">
            <div class="">
                <i class="bi bi-${m.Type === 'volume' ? 'database' : 'folder'} me-2 text-secondary"></i>
                <code class="text-primary item-break">${m.Source || m.Name}</code>
                <i class="bi bi-arrow-right mx-2"></i>
                <code class=" item-break">${m.Destination}</code>
            </div>
            <span class="badge rounded-pill bg-dark ms-2">${(m.Mode || 'rw').toUpperCase()}</span>
        </div>
        `).join('')}
    </div>
</div>`;
}

function renderLabels(labels) {
    if (!labels || Object.keys(labels).length === 0) return '';

    const labelEntries = Object.entries(labels); // Show all labels

    return `
<div class="mb-3 mx-2">
    <h6 class="small fw-bold text-muted mb-2">
    <i class="bi bi-tags-fill me-1"></i>Labels
    </h6>
    <div class="small text-muted">
    ${labelEntries.map(([key, value]) => `
        <div class="ms-2 me-2 label-item d-flex flex-wrap align-items-baseline mb-1">
        <div class="me-2">
            <i class="bi bi-tag me-2 text-secondary"></i>
            <code class="text-primary item-break">${key}</code>
            <i class="bi bi-arrow-right mx-1"></i>
        </div>
        <code class="item-break">${value}</code>
        </div>
    `).join('')}
    </div>
</div>`;
}

function getStatusBadge(state, status) {
    let badgeClass = 'bg-warning', iconClass = 'question-circle';
    if (state === 'running') { badgeClass = 'bg-success'; iconClass = 'play-circle'; }
    else if (state === 'exited') { badgeClass = 'bg-secondary'; iconClass = 'stop-circle'; }
    else if (state === 'paused') { badgeClass = 'bg-info'; iconClass = 'pause-circle'; }
    else if (state === 'restarting') { badgeClass = 'bg-warning'; iconClass = 'arrow-clockwise'; }
    return `<span class="badge rounded-pill ${badgeClass}"><i class="bi bi-${iconClass} me-1"></i>${status}</span>`;
}

function getActionButtons(container) {
    const names = container.Names.map(n => n.replace('/', '')).join(', ');
    const removeDisabled = container.State === 'running' ? 'disabled' : '';
    return `
    <div class="btn-group w-100" role="group">
    <button class="btn btn-sm btn-outline-success" title="Start Container" onclick="launchTerminalWithButtonAnimation('/containers/action/${container.Id}/start', this)" title="Start">
        <i class="bi bi-play"></i>
    </button>
    <button class="btn btn-sm btn-outline-primary" title="Stop Container" onclick="launchTerminalWithButtonAnimation('/containers/action/${container.Id}/stop', this)" title="Stop">
        <i class="bi bi-stop"></i>
    </button>
    <button class="btn btn-sm btn-outline-primary" title="View Logs" onclick="launchTerminalWithButtonAnimation('/containers/action/${container.Id}/logs', this)" title="Logs">
        <i class="bi bi-file-text"></i>
    </button>
    ${container.State === 'running' ? `
        <button class="btn btn-sm btn-outline-primary" title="Attach to Logs" onclick="launchTerminalWithButtonAnimation('/containers/action/${container.Id}/follow', this)" title="Follow Logs">
        <i class="bi bi-eye"></i>
        </button>` : ''}
    <button class="btn btn-sm btn-outline-danger" title="Remove Container" onclick="confirmRemoveContainer('${container.Id}', '${names}')" title="Remove" ${removeDisabled}>
        <i class="bi bi-trash"></i>
    </button>
    </div>
`;
}

function filterContainers() {
    const query = document.getElementById('Search').value.toLowerCase();
    const filtered = allContainers.filter(c =>
        c.Names.some(n => n.toLowerCase().includes(query)) ||
        c.Image.toLowerCase().includes(query) ||
        (c.Labels && Object.keys(c.Labels).some(key =>
            key.toLowerCase().includes(query) ||
            c.Labels[key].toLowerCase().includes(query)
        ))
    );
    renderContainers(filtered);
}

function clearSearch() {
    document.getElementById('Search').value = '';
    renderContainers(allContainers);
}

function setupAutoRefresh() {
    document.getElementById('autoRefresh').addEventListener('change', function () {
        if (this.checked) autoRefreshInterval = setInterval(refreshData, 5000);
        else if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    });
}

function setupRemovalConfirmation() {
    document.getElementById('confirmRemoveButton').addEventListener('click', function () {
        if (!containerIdToRemove) return;
        const button = this;
        button.disabled = true;
        button.innerHTML = '<i class="spinner-border spinner-border-sm me-2"></i>Removing...';
        bootstrap.Modal.getInstance(document.getElementById('removeContainerModal')).hide();
        launchTerminalModal(`/containers/action/${containerIdToRemove}/remove`);
        setTimeout(() => {
            button.disabled = false;
            button.innerHTML = '<i class="bi bi-trash me-2"></i>Remove Container';
            refreshData();
        }, 2000);
    });
}

function confirmRemoveContainer(containerId, containerName) {
    containerIdToRemove = containerId;
    document.getElementById('containerNameToRemove').textContent = containerName;
    new bootstrap.Modal(document.getElementById('removeContainerModal')).show();
}

function showError(message) {
    document.getElementById('errorText').textContent = message;
    document.getElementById('errorMessage').style.display = 'block';
}

function hideError() {
    document.getElementById('errorMessage').style.display = 'none';
}