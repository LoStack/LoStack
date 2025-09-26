function addServiceIcons(packages) {
    if (!packages) return;
    Object.entries(packages).forEach(([packageName, packageData]) => {
        const serviceCard = document.querySelector(`[data-name="${packageName.toLowerCase()}"] .card-header`);
        if (!serviceCard) return;
        const iconName = extractIconFromLabels(packageData.labels) || packageName.toLowerCase();
        const iconElement = createServiceIcon(iconName, 50);
        iconElement.classList.add('ms-2');
        const headerContent = serviceCard.querySelector('.d-flex');
        if (headerContent) headerContent.appendChild(iconElement);
    });
}

// Search and filter state
let currentGroup = 'all';
let currentTag = 'all';
let tagsExpanded = false;

function toggleTagsSection() {
    const content = document.getElementById('tagsContent');
    const chevron = document.getElementById('tagsChevron');
    const summary = document.getElementById('tagsSummary');

    tagsExpanded = !tagsExpanded;

    if (tagsExpanded) {
        content.style.display = "block";
        // Use a large max-height to accommodate any number of tag rows
        content.style.maxHeight = "1000px";  
        chevron.classList.remove('bi-chevron-down');
        chevron.classList.add('bi-chevron-up');
        summary.textContent = 'Click to collapse tag filters';
    } else {
        content.style.maxHeight = "0";
        setTimeout(() => content.style.display = "none", 300);
        chevron.classList.remove('bi-chevron-up');
        chevron.classList.add('bi-chevron-down');
        updateTagsSummary();
    }
}


function updateTagsSummary() {
    const summary = document.getElementById('tagsSummary');
    if (!tagsExpanded) {
        summary.textContent = currentTag === 'all' 
            ? 'Click to expand tag filters' 
            : `Filtered by tag: ${currentTag} (click to expand)`;
    }
}

function performSearch() {
    const searchTerm = document.getElementById('Search').value.toLowerCase();
    const serviceItems = document.querySelectorAll('.service-item');
    const noResultsDiv = document.getElementById('noResults');
    let visibleCount = 0;

    serviceItems.forEach(item => {
        const matchesSearch = !searchTerm || 
            ['name', 'title', 'description', 'group', 'tags']
                .some(attr => (item.dataset[attr] || '').toLowerCase().includes(searchTerm));
        const matchesGroup = currentGroup === 'all' || 
            (item.dataset.group && item.dataset.group.trim() === currentGroup.trim());
        const matchesTag = currentTag === 'all' || 
            (item.dataset.tags && item.dataset.tags.split(',').some(tag => 
                tag.trim().toLowerCase() === currentTag.toLowerCase()));

        if (matchesSearch && matchesGroup && matchesTag) {
            item.classList.remove('d-none');
            visibleCount++;
        } else {
            item.classList.add('d-none');
        }
    });

    noResultsDiv.classList.toggle('d-none', visibleCount > 0);
}

function updateFilterButtons(selector, activeValue, activeClass, defaultClass) {
    document.querySelectorAll(selector).forEach(button => {
        const isActive = button.dataset[selector.includes('group') ? 'group' : 'tag'] === activeValue;
        const isAll = button.dataset[selector.includes('group') ? 'group' : 'tag'] === 'all';
        button.classList.toggle('active', isActive);
        button.classList.remove(activeClass, defaultClass, 'btn-outline-primary', 'btn-outline-primary', 'btn-outline-success');
        if (isActive) button.classList.add(activeClass);
        else if (isAll) button.classList.add(defaultClass);
        else button.classList.add('btn-outline-primary');
    });
}

function filterByGroup(group) {
    currentGroup = group;
    updateFilterButtons('.group-tag', group, 'btn-primary', 'btn-outline-primary');
    performSearch();
}

function filterByTag(tag) {
    currentTag = tag;
    updateFilterButtons('.tag-filter', tag, 'btn-success', 'btn-outline-success');
    updateTagsSummary();
    performSearch();
}

function clearSearch(input) {
    document.getElementById('Search').value = '';
    currentGroup = 'all';
    currentTag = 'all';
    updateFilterButtons('.group-tag', 'all', 'btn-primary', 'btn-outline-primary');
    updateFilterButtons('.tag-filter', 'all', 'btn-success', 'btn-outline-success');
    updateTagsSummary();
    performSearch();
}