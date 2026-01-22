// ============================================================================
// SEARCHABLE DROPDOWN CLASS
// ============================================================================

class SearchableDropdown {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            placeholder: options.placeholder || 'Select an option...',
            searchPlaceholder: options.searchPlaceholder || 'Search...',
            noResultsText: options.noResultsText || 'No results found',
            maxHeight: options.maxHeight || '250px',
            ...options
        };
        this.data = [];
        this.filteredData = [];
        this.selectedValue = '';
        this.selectedText = '';
        this.isOpen = false;
        this.onSelect = options.onSelect || (() => {});
        
        this.init();
    }
    
    init() {
        this.container.innerHTML = `
            <div class="searchable-dropdown">
                <input type="text" 
                       class="searchable-dropdown-input" 
                       placeholder="${this.options.placeholder}"
                       readonly>
                <i class="bi bi-chevron-down searchable-dropdown-arrow"></i>
                <div class="searchable-dropdown-list" style="max-height: ${this.options.maxHeight}">
                </div>
            </div>
        `;
        
        this.input = this.container.querySelector('.searchable-dropdown-input');
        this.dropdown = this.container.querySelector('.searchable-dropdown');
        this.list = this.container.querySelector('.searchable-dropdown-list');
        
        this.bindEvents();
    }
    
    bindEvents() {
        // Toggle dropdown on input click
        this.input.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });
        
        // Handle input for search
        this.input.addEventListener('input', (e) => {
            if (this.isOpen) {
                this.filter(e.target.value);
            }
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.close();
            }
        });
        
        // Handle keyboard navigation
        this.input.addEventListener('keydown', (e) => {
            if (!this.isOpen) return;
            
            const items = this.list.querySelectorAll('.searchable-dropdown-item:not(.searchable-dropdown-no-results)');
            const currentSelected = this.list.querySelector('.searchable-dropdown-item.selected');
            let currentIndex = Array.from(items).indexOf(currentSelected);
            
            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    currentIndex = Math.min(currentIndex + 1, items.length - 1);
                    this.highlightItem(items[currentIndex]);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    currentIndex = Math.max(currentIndex - 1, 0);
                    this.highlightItem(items[currentIndex]);
                    break;
                case 'Enter':
                    e.preventDefault();
                    if (currentSelected && !currentSelected.classList.contains('searchable-dropdown-no-results')) {
                        this.selectItem(currentSelected);
                    }
                    break;
                case 'Escape':
                    this.close();
                    break;
            }
        });
    }
    
    setData(data) {
        this.data = data;
        this.filteredData = [...data];
        this.renderList();
    }
    
    filter(searchTerm) {
        const term = searchTerm.toLowerCase();
        this.filteredData = this.data.filter(item => 
            item.text.toLowerCase().includes(term) ||
            (item.subtext && item.subtext.toLowerCase().includes(term))
        );
        this.renderList();
    }
    
    renderList() {
        if (this.filteredData.length === 0) {
            this.list.innerHTML = `<div class="searchable-dropdown-no-results">${this.options.noResultsText}</div>`;
            return;
        }
        
        this.list.innerHTML = this.filteredData.map(item => `
            <div class="searchable-dropdown-item" data-value="${item.value}">
                <div>${item.text}</div>
                ${item.subtext ? `<small style="color: var(--text-secondary)">${item.subtext}</small>` : ''}
            </div>
        `).join('');
        
        // Bind click events to items
        this.list.querySelectorAll('.searchable-dropdown-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectItem(item);
            });
        });
    }
    
    highlightItem(item) {
        this.list.querySelectorAll('.searchable-dropdown-item').forEach(i => i.classList.remove('selected'));
        if (item) {
            item.classList.add('selected');
            item.scrollIntoView({ block: 'nearest' });
        }
    }
    
    selectItem(item) {
        const value = item.dataset.value;
        const text = item.querySelector('div').textContent;
        
        this.selectedValue = value;
        this.selectedText = text;
        this.input.value = text;
        this.input.setAttribute('readonly', 'true');
        
        this.close();
        this.onSelect(value, text, this.data.find(d => d.value === value));
    }
    
    open() {
        this.isOpen = true;
        this.dropdown.classList.add('open');
        this.list.classList.add('show');
        this.input.removeAttribute('readonly');
        this.input.setAttribute('placeholder', this.options.searchPlaceholder);
        this.input.focus();
        this.renderList();
    }
    
    close() {
        this.isOpen = false;
        this.dropdown.classList.remove('open');
        this.list.classList.remove('show');
        this.input.setAttribute('readonly', 'true');
        this.input.setAttribute('placeholder', this.options.placeholder);
        
        // Restore selected text if no selection was made
        if (this.selectedText) {
            this.input.value = this.selectedText;
        }
    }
    
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }
    
    getValue() {
        return this.selectedValue;
    }
    
    getText() {
        return this.selectedText;
    }
    
    getSelectedData() {
        return this.data.find(d => d.value === this.selectedValue);
    }
    
    reset() {
        this.selectedValue = '';
        this.selectedText = '';
        this.input.value = '';
        this.close();
    }
    
    setValue(value) {
        const item = this.data.find(d => d.value === value);
        if (item) {
            this.selectedValue = value;
            this.selectedText = item.text;
            this.input.value = item.text;
        }
    }
}

// ============================================================================
// STATE
// ============================================================================

// Initialize all dropdowns when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing dropdowns...');
    
    // Send log to backend
    fetch('/api/log-frontend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            level: 'INFO',
            message: `Frontend: DOM loaded, initializing dropdowns`,
            data: { 
                has_project_container: !!document.getElementById('projectSelectContainer'),
                has_image_container: !!document.getElementById('imageSelectContainer'),
                has_account_container: !!document.getElementById('accountSelectContainer')
            }
        })
    }).catch(e => console.error('Failed to send log:', e));
    
    // Initialize project dropdowns if containers exist
    if (document.getElementById('projectSelectContainer')) {
        initializeProjectDropdowns();
        console.log('Project dropdowns initialized');
    }
    
    // Initialize image dropdowns if containers exist
    if (document.getElementById('imageSelectContainer')) {
        initializeImageDropdowns();
        console.log('Image dropdowns initialized');
    }
    
    // Initialize resource dropdowns if containers exist
    if (document.getElementById('accountSelectContainer')) {
        initializeResourceDropdowns();
        console.log('Resource dropdowns initialized');
    }
});

let currentSection = 'welcome';
let allApis = [];

// Section 1 state
let rulesOriginalPayload = null;
let rulesEntities = [];
let rulesTempCounts = {};  // Temporary counts for preview only
let rulesCustomRules = [];
let rulesDefaultRules = [];
let rulesPreviewData = null;
// App Profile optional features for rules section (0 = exclude from payload)
let rulesProfileOptions = {
    action_list: 0,
    snapshot_config_list: 0,
    restore_config_list: 0,
    patch_list: 0
};

// Section 2 state
let entitySelectedApi = null;
let entityEntities = [];
let entityCounts = {};
let entityGeneratedData = null;

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    loadAllApis();
    loadDefaultRules('blueprint');
    
    // Initialize calculated counts display
    updateCalculatedCounts();
    updateRulesCalculatedCounts();
});

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast-custom';
    toast.style.background = type === 'success' ? 'var(--accent-green)' : 'var(--accent-red)';
    toast.innerHTML = `<i class="bi bi-${type === 'success' ? 'check-circle' : 'x-circle'}"></i>${message}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function showLoading(show) {
    document.getElementById('loadingOverlay').classList.toggle('show', show);
}

function toggleNestedSection(level) {
    const content = document.getElementById(`${level}NestedConfig`);
    const chevron = document.getElementById(`${level}Chevron`);
    const header = chevron?.parentElement;
    
    if (content && chevron) {
        content.classList.toggle('hidden');
        header?.classList.toggle('collapsed');
    }
}

function toggleCollapsible(contentId) {
    const content = document.getElementById(contentId);
    const iconId = contentId.replace('Content', 'Icon');
    const icon = document.getElementById(iconId);
    
    content.classList.toggle('collapsed');
    if (icon) {
        icon.className = content.classList.contains('collapsed') ? 'bi bi-chevron-right' : 'bi bi-chevron-down';
    }
}

// ============================================================================
// SECTION NAVIGATION
// ============================================================================

function showSection(section) {
    currentSection = section;
    
    // Hide all sections
    document.querySelectorAll('.section').forEach(s => s.classList.add('section-hidden'));
    
    // Show selected section
    document.getElementById(`${section}Section`).classList.remove('section-hidden');
    
    // Update nav buttons
    document.querySelectorAll('.nav-btn-secondary').forEach(btn => btn.classList.remove('active'));
    if (section === 'createEntities') {
        document.getElementById('createEntitiesBtn').classList.add('active');
    } else if (section === 'analyzer') {
        document.getElementById('analyzerBtn').classList.add('active');
    } else if (section === 'dashboard') {
        document.getElementById('dashboardBtn').classList.add('active');
    } else if (section === 'perfTester') {
        document.getElementById('perfTesterBtn').classList.add('active');
    } else if (section === 'playwright') {
        document.getElementById('playwrightBtn').classList.add('active');
    }
    
    // Reset section state if needed
    if (section === 'generateRules') {
        resetRulesSection();
    } else if (section === 'createEntities') {
        loadEntityApiList();
        // Also load the new app switcher entity lists
        if (typeof loadBlueprintEntityList === 'function') {
            if (currentAppType === 'blueprint') {
                loadBlueprintEntityList();
            } else {
                loadRunbookEntityList();
            }
        }
    } else if (section === 'analyzer') {
        initAnalyzer();
    } else if (section === 'perfTester') {
        initPerfTester();
    }
}

function resetRulesSection() {
    // Reset to step 1
    goToRulesStep(1);
    document.getElementById('rulesPayloadInput').value = '';
    if (document.getElementById('rulesRunbookPayloadInput')) {
        document.getElementById('rulesRunbookPayloadInput').value = '';
    }
    rulesOriginalPayload = null;
    rulesEntities = [];
    rulesTempCounts = {};
    rulesCustomRules = [];
    rulesEntityName = '';
    rulesExistingEntity = null;
    rulesCurrentAppType = 'blueprint';
    rulesBlueprintType = 'multi_vm';
    rulesTaskExecMode = 'parallel';
    
    // Reset app switcher to blueprint
    switchRulesAppType('blueprint');
    
    // Reset hierarchy counts - NEW HIERARCHY
    const appProfileInput = document.getElementById('rulesAppProfileCountInput');
    const deploymentInput = document.getElementById('rulesDeploymentCountInput');
    const serviceInput = document.getElementById('rulesServiceCountInput');
    
    if (appProfileInput) {
        appProfileInput.value = 1;
        appProfileInput.disabled = false;
    }
    if (deploymentInput) {
        deploymentInput.value = 1;
        deploymentInput.disabled = false;
    }
    if (serviceInput) {
        serviceInput.value = 1;
        serviceInput.disabled = false;
    }
    
    // Re-enable all +/- buttons
    document.querySelectorAll('#rulesBlueprintHierarchy .hierarchy-entity-input').forEach(container => {
        container.querySelectorAll('.count-btn').forEach(btn => btn.disabled = false);
        container.classList.remove('disabled-input');
    });
    
    // Reset calculated counts display
    updateRulesCalculatedCounts();
}

// ============================================================================
// API LIST MANAGEMENT
// ============================================================================

async function loadAllApis() {
    try {
        const response = await fetch('/api/rules');
        const data = await response.json();
        
        if (data.success) {
            allApis = data.apis || [];
            renderApiList();
        }
    } catch (e) {
        console.error('Failed to load APIs:', e);
    }
}

function renderApiList() {
    const container = document.getElementById('apiList');
    
    if (allApis.length === 0) {
        container.innerHTML = `
            <div class="no-apis">
                <i class="bi bi-inbox"></i>
                <div>No saved entities yet</div>
                <small>Create rules to get started</small>
            </div>
        `;
        return;
    }

    container.innerHTML = allApis.map(api => `
        <div class="api-item" onclick="selectApiForEntities('${encodeURIComponent(api.api_url)}')">
            <div class="api-name">${api.api_url}</div>
            <div class="api-meta">
                <span><i class="bi bi-tag"></i> ${api.api_type}</span>
                <span><i class="bi bi-sliders"></i> ${api.rules_count} rules</span>
            </div>
            <div class="api-actions">
                <button class="btn-use" onclick="event.stopPropagation(); selectApiForEntities('${encodeURIComponent(api.api_url)}')">
                    <i class="bi bi-play"></i> Use
                </button>
                <button class="btn-history" onclick="event.stopPropagation(); showHistoryModal('${api.api_url}')" title="View History">
                    <i class="bi bi-clock-history"></i>
                </button>
                <button class="btn-delete" onclick="event.stopPropagation(); deleteApi('${encodeURIComponent(api.api_url)}')">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

// Store recently deleted API for undo functionality
let recentlyDeletedApi = null;
let undoTimeout = null;

async function deleteApi(encodedUrl) {
    const apiUrl = decodeURIComponent(encodedUrl);
    if (!confirm(`Delete rules for "${apiUrl}"?`)) return;
    
    try {
        // First, fetch the full rule data INCLUDING template before deleting (for undo)
        const getRulesResponse = await fetch(`/api/rules/${encodedUrl}?include_template=true`);
        let ruleDataForUndo = null;
        if (getRulesResponse.ok) {
            const fullData = await getRulesResponse.json();
            ruleDataForUndo = {
                api_url: apiUrl,
                api_type: fullData.api_type,
                rules: fullData.rules,
                scalable_entities: fullData.scalable_entities,
                task_execution: fullData.task_execution || 'parallel',
                payload_template: fullData.payload_template || null  // Include template for full restore
            };
        }
        
        const response = await fetch(`/api/rules/${encodedUrl}`, { method: 'DELETE' });
        const data = await response.json();
        
        if (data.success) {
            // Store for undo
            recentlyDeletedApi = ruleDataForUndo;
            
            // Clear any existing undo timeout
            if (undoTimeout) {
                clearTimeout(undoTimeout);
            }
            
            // Show toast with undo button
            showUndoToast(`Rules deleted for "${apiUrl}"`, 5000);
            
            loadAllApis();
        } else {
            showToast(data.error || 'Failed to delete', 'error');
        }
    } catch (e) {
        showToast('Failed to delete', 'error');
    }
}

function showUndoToast(message, duration = 5000) {
    const container = document.getElementById('toastContainer');
    const toastId = 'undoToast_' + Date.now();
    
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = 'toast-custom toast-undo';
    toast.style.background = 'var(--accent-orange)';
    toast.innerHTML = `
        <i class="bi bi-trash"></i>
        <span style="flex: 1;">${message}</span>
        <button class="undo-btn" onclick="event.stopPropagation(); undoDelete('${toastId}')">
            <i class="bi bi-arrow-counterclockwise"></i> Undo
        </button>
        <div class="undo-timer" style="animation: shrink ${duration}ms linear forwards;"></div>
    `;
    container.appendChild(toast);
    
    // Auto-remove after duration
    undoTimeout = setTimeout(() => {
        toast.remove();
        recentlyDeletedApi = null;  // Clear undo data
    }, duration);
}

async function undoDelete(toastId) {
    if (!recentlyDeletedApi) {
        showToast('Nothing to undo', 'error');
        return;
    }
    
    // Clear the timeout
    if (undoTimeout) {
        clearTimeout(undoTimeout);
        undoTimeout = null;
    }
    
    // Remove the undo toast
    const toast = document.getElementById(toastId);
    if (toast) toast.remove();
    
    try {
        // Restore the deleted API rules (including template if available)
        const response = await fetch('/api/rules/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_url: recentlyDeletedApi.api_url,
                api_type: recentlyDeletedApi.api_type,
                rules: recentlyDeletedApi.rules,
                scalable_entities: recentlyDeletedApi.scalable_entities,
                task_execution: recentlyDeletedApi.task_execution,
                payload_template: recentlyDeletedApi.payload_template  // Restore template too
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Rules restored!');
            loadAllApis();
        } else {
            showToast('Failed to restore: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (e) {
        showToast('Failed to restore', 'error');
    }
    
    recentlyDeletedApi = null;
}

async function loadDefaultRules(apiType) {
    try {
        const response = await fetch(`/api/default-rules/${apiType}`);
        if (response.ok) {
            const data = await response.json();
            rulesDefaultRules = data.default_rules || [];
        }
    } catch (e) {
        console.error('Failed to load default rules:', e);
    }
}

// ============================================================================
// SECTION 1: GENERATE NEW PAYLOAD RULES
// ============================================================================

function goToRulesStep(step) {
    // Update step indicators
    for (let i = 1; i <= 3; i++) {
        const stepEl = document.getElementById(`step${i}`);
        stepEl.classList.remove('active', 'completed');
        if (i < step) stepEl.classList.add('completed');
        if (i === step) stepEl.classList.add('active');
    }
    
    // Show/hide step content
    document.getElementById('rulesStep1').classList.toggle('section-hidden', step !== 1);
    document.getElementById('rulesStep2').classList.toggle('section-hidden', step !== 2);
    document.getElementById('rulesStep3').classList.toggle('section-hidden', step !== 3);
    
    // Show/hide appropriate hierarchy in step 2
    if (step === 2) {
        const apiType = document.getElementById('apiTypeSelect').value;
        document.getElementById('rulesBlueprintHierarchy').classList.toggle('section-hidden', apiType === 'runbook');
        document.getElementById('rulesRunbookHierarchy').classList.toggle('section-hidden', apiType !== 'runbook');
        
        // Sync hierarchy counts with rulesTempCounts
        syncRulesHierarchyCounts();
    }
    
    // Show/hide task execution dropdown for runbooks in step 3
    if (step === 3) {
        const apiType = document.getElementById('apiTypeSelect').value;
        const taskExecContainer = document.getElementById('rulesTaskExecutionContainer');
        taskExecContainer.style.display = apiType === 'runbook' ? 'block' : 'none';
        
        // Update entity name input
        const entityNameInput = document.getElementById('entityNameInput');
        entityNameInput.value = rulesEntityName;
        
        // Show warning if entity exists
        const warning = document.getElementById('entityExistsWarning');
        warning.style.display = rulesExistingEntity ? 'flex' : 'none';
    }
}

// Sync hierarchy input counts with the actual rulesTempCounts
function syncRulesHierarchyCounts() {
    const apiType = document.getElementById('apiTypeSelect').value;
    
    if (apiType === 'blueprint' || apiType === 'app') {
        const serviceCount = rulesTempCounts['spec.resources.service_definition_list'] || 1;
        document.getElementById('rulesServiceCountInput').value = serviceCount;
        
        const credCount = rulesTempCounts['spec.resources.credential_definition_list'] || 1;
        if (document.getElementById('rulesCredentialCount')) {
            document.getElementById('rulesCredentialCount').value = credCount;
        }
        
        const profileCount = rulesTempCounts['spec.resources.app_profile_list'] || 1;
        if (document.getElementById('rulesAppProfileCount')) {
            document.getElementById('rulesAppProfileCount').value = profileCount;
        }
    } else if (apiType === 'runbook') {
        const taskCount = rulesTempCounts['spec.resources.runbook.task_definition_list'] || 1;
        if (document.getElementById('rulesTaskCount')) {
            document.getElementById('rulesTaskCount').value = taskCount;
        }
        
        const endpointCount = rulesTempCounts['spec.resources.endpoint_definition_list'] || 1;
        if (document.getElementById('rulesEndpointCount')) {
            document.getElementById('rulesEndpointCount').value = endpointCount;
        }
        
        const credCount = rulesTempCounts['spec.resources.credential_definition_list'] || 1;
        if (document.getElementById('rulesRunbookCredentialCount')) {
            document.getElementById('rulesRunbookCredentialCount').value = credCount;
        }
    }
}

// Blueprint type for rules
let rulesBlueprintType = 'multi_vm';
let rulesTaskExecMode = 'parallel';

function setRulesBlueprintType(type) {
    rulesBlueprintType = type;
    document.querySelectorAll('#rulesBlueprintHierarchy .bp-type-btn[data-bptype]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.bptype === type);
    });
    
    const appProfileInput = document.getElementById('rulesAppProfileCountInput');
    const deploymentInput = document.getElementById('rulesDeploymentCountInput');
    const serviceInput = document.getElementById('rulesServiceCountInput');
    
    const appProfileContainer = appProfileInput?.closest('.hierarchy-entity-input');
    const deploymentContainer = deploymentInput?.closest('.hierarchy-entity-input');
    
    // If single_vm, set all to 1 and disable
    if (type === 'single_vm') {
        // Set all counts to 1
        // NOTE: substrate_definition_list and package_definition_list are calculated by backend
        rulesTempCounts['spec.resources.app_profile_list'] = 1;
        rulesTempCounts['spec.resources.app_profile_list.deployment_create_list'] = 1;
        rulesTempCounts['spec.resources.service_definition_list'] = 1;
        
        // Update inputs
        if (appProfileInput) {
            appProfileInput.value = 1;
            appProfileInput.disabled = true;
        }
        if (deploymentInput) {
            deploymentInput.value = 1;
            deploymentInput.disabled = true;
        }
        if (serviceInput) {
            serviceInput.value = 1;
            serviceInput.disabled = true;
        }
        
        // Disable +/- buttons
        if (appProfileContainer) {
            appProfileContainer.querySelectorAll('.count-btn').forEach(btn => btn.disabled = true);
            appProfileContainer.classList.add('disabled-input');
        }
        if (deploymentContainer) {
            deploymentContainer.querySelectorAll('.count-btn').forEach(btn => btn.disabled = true);
            deploymentContainer.classList.add('disabled-input');
        }
        
        // Update calculated counts display
        updateRulesCalculatedCounts();
    } else {
        // Enable all inputs
        if (appProfileInput) appProfileInput.disabled = false;
        if (deploymentInput) deploymentInput.disabled = false;
        if (serviceInput) serviceInput.disabled = false;
        
        // Enable +/- buttons
        if (appProfileContainer) {
            appProfileContainer.querySelectorAll('.count-btn').forEach(btn => btn.disabled = false);
            appProfileContainer.classList.remove('disabled-input');
        }
        if (deploymentContainer) {
            deploymentContainer.querySelectorAll('.count-btn').forEach(btn => btn.disabled = false);
            deploymentContainer.classList.remove('disabled-input');
        }
    }
}

function setRulesTaskExecution(type) {
    rulesTaskExecMode = type;
    document.querySelectorAll('#rulesRunbookHierarchy .bp-type-btn[data-exectype]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.exectype === type);
    });
}

// ===== RULES SECTION: App Profile & Deployment Count Functions =====
function adjustRulesAppProfileCount(delta) {
    const input = document.getElementById('rulesAppProfileCountInput');
    let value = parseInt(input.value) || 1;
    value = Math.max(1, Math.min(10, value + delta));
    input.value = value;
    onRulesAppProfileCountChange(value);
}

function onRulesAppProfileCountChange(value) {
    const count = parseInt(value) || 1;
    rulesTempCounts['spec.resources.app_profile_list'] = count;
    updateRulesCalculatedCounts();
}

function adjustRulesDeploymentCount(delta) {
    const input = document.getElementById('rulesDeploymentCountInput');
    let value = parseInt(input.value) || 1;
    value = Math.max(1, Math.min(50, value + delta));
    input.value = value;
    onRulesDeploymentCountChange(value);
}

function onRulesDeploymentCountChange(value) {
    const count = parseInt(value) || 1;
    rulesTempCounts['spec.resources.app_profile_list.deployment_create_list'] = count;
    updateRulesCalculatedCounts();
}

function updateRulesCalculatedCounts() {
    const appProfiles = parseInt(document.getElementById('rulesAppProfileCountInput')?.value) || 1;
    const deploymentsPerProfile = parseInt(document.getElementById('rulesDeploymentCountInput')?.value) || 1;
    const totalDeployments = appProfiles * deploymentsPerProfile;
    
    // Update UI badges to show calculated values (for display only)
    // NOTE: Do NOT store these in rulesTempCounts - let backend calculate them
    const substrateCalc = document.querySelector('#rulesSubstrateCalc span');
    const packageCalc = document.querySelector('#rulesPackageCalc span');
    if (substrateCalc) substrateCalc.textContent = totalDeployments;
    if (packageCalc) packageCalc.textContent = totalDeployments;
}

// Legacy function for backward compatibility
function adjustRulesServiceCount(delta) {
    const input = document.getElementById('rulesServiceCountInput');
    if (!input) return;
    let value = parseInt(input.value) || 1;
    value = Math.max(1, Math.min(100, value + delta));
    input.value = value;
    updateRulesSubEntityCount('service_definition_list', value);
}

function onRulesServiceCountChange(value) {
    updateRulesSubEntityCount('service_definition_list', parseInt(value) || 1);
}

function updateRulesSubEntityCount(entity, value) {
    const count = parseInt(value) || 0;
    rulesTempCounts[`spec.resources.${entity}`] = count;
}

function updateRulesRunbookEntityCount(entity, value) {
    const count = parseInt(value) || 0;
    if (entity === 'task_definition_list') {
        rulesTempCounts[`spec.resources.runbook.${entity}`] = count;
    } else {
        rulesTempCounts[`spec.resources.${entity}`] = count;
    }
}

function toggleEntityNameEdit() {
    const input = document.getElementById('entityNameInput');
    const btn = document.getElementById('editEntityNameBtn');
    
    if (input.readOnly) {
        input.readOnly = false;
        input.focus();
        btn.innerHTML = '<i class="bi bi-check"></i> Done';
        btn.classList.remove('btn-outline-secondary');
        btn.classList.add('btn-success');
    } else {
        input.readOnly = true;
        rulesEntityName = input.value.trim() || rulesEntityName;
        btn.innerHTML = '<i class="bi bi-pencil"></i> Edit';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-outline-secondary');
        
        // Re-check if this entity exists
        checkExistingEntity(rulesEntityName).then(() => {
            const warning = document.getElementById('entityExistsWarning');
            warning.style.display = rulesExistingEntity ? 'flex' : 'none';
        });
    }
}

// Store generated entity name for current analysis
let rulesEntityName = '';
let rulesExistingEntity = null;  // Stores existing entity data if found

function generateEntityName(payload, apiType) {
    // Try to extract a meaningful name from the payload
    try {
        const parsed = typeof payload === 'string' ? JSON.parse(payload) : payload;
        
        // Common name fields to check
        const nameFields = [
            parsed?.spec?.name,
            parsed?.metadata?.name,
            parsed?.name,
            parsed?.spec?.resources?.name,
            parsed?.spec?.resources?.app_name,
            parsed?.spec?.description?.name
        ];
        
        const name = nameFields.find(n => n && typeof n === 'string');
        if (name) {
            // Clean up the name and combine with type
            const cleanName = name.replace(/[^a-zA-Z0-9_-]/g, '_').substring(0, 30);
            return `${apiType}_${cleanName}`;
        }
    } catch (e) {
        // Ignore parsing errors
    }
    
    // Fallback to type + timestamp
    return `${apiType}_${Date.now().toString(36)}`;
}

// Current app type for rules section
let rulesCurrentAppType = 'blueprint';

function switchRulesAppType(type) {
    rulesCurrentAppType = type;
    
    // Update tab buttons
    document.querySelectorAll('#generateRulesSection .app-switcher-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.type === type);
    });
    
    // Update hidden select for compatibility
    document.getElementById('apiTypeSelect').value = type;
    
    // Show/hide payload inputs
    document.getElementById('rulesBlueprintInput').classList.toggle('section-hidden', type !== 'blueprint');
    document.getElementById('rulesRunbookInput').classList.toggle('section-hidden', type !== 'runbook');
}

async function analyzeRunbookPayload() {
    const payload = document.getElementById('rulesRunbookPayloadInput').value.trim();
    
    if (!payload) {
        showToast('Please enter a JSON payload', 'error');
        return;
    }
    
    // Copy to main input and set type, then call analyze
    document.getElementById('rulesPayloadInput').value = payload;
    document.getElementById('apiTypeSelect').value = 'runbook';
    await analyzePayloadForRules();
}

// ============================================================================
// DEBUG FUNCTIONS
// ============================================================================

// Manual test function for project selection
window.testProjectSelection = async function() {
    try {
        console.log('Testing project selection...');
        
        // First test connection
        const connResponse = await fetch('/api/live-uuid/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pc_url: 'https://iam.nconprem-10-53-58-35.ccpnx.com/',
                username: 'admin',
                password: 'Nutanix.123'
            })
        });
        
        const connResult = await connResponse.json();
        console.log('Connection test:', connResult);
        
        if (connResult.success) {
            // Fetch projects
            const projResponse = await fetch('/api/live-uuid/projects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pc_url: 'https://iam.nconprem-10-53-58-35.ccpnx.com/',
                    username: 'admin',
                    password: 'Nutanix.123'
                })
            });
            
            const projResult = await projResponse.json();
            console.log('Projects result:', projResult);
            
            if (projResult.success && projResult.projects.length > 0) {
                // Populate project dropdown
                populateProjectSelect(projResult.projects);
                
                // Test selecting the first project
                const firstProject = projResult.projects[0];
                console.log('Testing selection of first project:', firstProject);
                onProjectSelected(firstProject);
                
                return firstProject;
            }
        }
    } catch (error) {
        console.error('Test error:', error);
    }
};

// ============================================================================
// LIVE UUID FUNCTIONS
// ============================================================================

let currentProjects = [];
let selectedProject = null;
let searchTimeout = null;

async function fetchAccountDetails(accounts) {
    /**
     * Fetch account details for given account UUIDs using GET API calls.
     * Returns account details including pc_uuid which should be used as the actual account UUID.
     */
    try {
        console.log('fetchAccountDetails called with accounts:', accounts);
        
        if (!accounts || accounts.length === 0) {
            console.log('No accounts to fetch details for');
            return [];
        }
        
        const pcUrl = document.getElementById('pcUrlInput').value;
        const username = document.getElementById('pcUsernameInput').value;
        const password = document.getElementById('pcPasswordInput').value;
        
        console.log('PC credentials check:', {pcUrl: !!pcUrl, username: !!username, password: !!password});
        
        if (!pcUrl || !username || !password) {
            throw new Error('PC credentials are required');
        }
        
        const accountUuids = accounts.map(account => account.uuid);
        console.log(`Fetching details for ${accountUuids.length} accounts:`, accountUuids);
        
        const response = await fetch('/api/live-uuid/account-details', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pc_url: pcUrl,
                username: username,
                password: password,
                account_uuids: accountUuids
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('Successfully fetched account details:', result.accounts);
            return result.accounts;
        } else {
            throw new Error(result.error || 'Failed to fetch account details');
        }
    } catch (error) {
        console.error('Error fetching account details:', error);
        // Return fallback account data
        return accounts.map(account => ({
            uuid: account.uuid,
            name: account.name,
            pc_uuid: account.pc_uuid,
            status: 'Fetch Error'
        }));
    }
}

async function fetchClusterNames(clusters) {
    /**
     * Fetch cluster names for given cluster UUIDs using GET API calls.
     */
    try {
        console.log('fetchClusterNames called with clusters:', clusters);
        
        const pcUrl = document.getElementById('pcUrlInput').value;
        const username = document.getElementById('pcUsernameInput').value;
        const password = document.getElementById('pcPasswordInput').value;
        
        console.log('PC credentials check:', {pcUrl: !!pcUrl, username: !!username, password: !!password});
        
        if (!pcUrl || !username || !password) {
            throw new Error('PC credentials are required');
        }
        
        const clusterUuids = clusters.map(cluster => cluster.uuid);
        console.log(`Fetching names for ${clusterUuids.length} clusters:`, clusterUuids);
        
        const response = await fetch('/api/live-uuid/cluster-names', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pc_url: pcUrl,
                username: username,
                password: password,
                cluster_uuids: clusterUuids
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('Successfully fetched cluster names:', result.clusters);
            return result.clusters;
        } else {
            throw new Error(result.error || 'Failed to fetch cluster names');
        }
    } catch (error) {
        console.error('Error in fetchClusterNames:', error);
        throw error;
    }
}

async function fetchEntityNames(entities, entityType) {
    /**
     * Generic function to fetch entity names using GET API calls.
     * Currently supports clusters, environments, networks, subnets.
     */
    try {
        const pcUrl = document.getElementById('pcUrl').value;
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        if (!pcUrl || !username || !password) {
            throw new Error('PC credentials are required');
        }
        
        const entityUuids = entities.map(entity => entity.uuid);
        console.log(`Fetching names for ${entityUuids.length} ${entityType}s:`, entityUuids);
        
        // For now, only clusters are supported via API
        if (entityType === 'cluster') {
            return await fetchClusterNames(entities);
        } else {
            // For other entity types, return with fallback names
            return entities.map(entity => ({
                uuid: entity.uuid,
                name: entity.name || `${entityType}-${entity.uuid.substring(0, 8)}`,
                status: 'UNKNOWN'
            }));
        }
    } catch (error) {
        console.error(`Error fetching ${entityType} names:`, error);
        // Return fallback data
        return entities.map(entity => ({
            uuid: entity.uuid,
            name: entity.name || `${entityType}-${entity.uuid.substring(0, 8)}`,
            status: 'ERROR'
        }));
    }
}

async function testPCConnection() {
    const pcUrl = document.getElementById('pcUrlInput').value.trim();
    const username = document.getElementById('pcUsernameInput').value.trim() || 'admin';
    const password = document.getElementById('pcPasswordInput').value.trim() || 'Nutanix.123';
    
    if (!pcUrl) {
        showToast('Please enter a PC URL', 'error');
        return;
    }
    
    const testBtn = document.getElementById('testConnectionBtn');
    const originalText = testBtn.innerHTML;
    testBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Testing...';
    testBtn.disabled = true;
    
    try {
        const response = await fetch('/api/live-uuid/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                pc_url: pcUrl,
                username: username,
                password: password
            })
        });
        
        const result = await response.json();
        
        document.getElementById('connectionStatus').style.display = 'block';
        
        if (result.success) {
            document.getElementById('connectionSuccess').style.display = 'block';
            document.getElementById('connectionError').style.display = 'none';
            document.getElementById('fetchProjectsBtn').disabled = false;
            showToast('Connection successful!', 'success');
        } else {
            document.getElementById('connectionSuccess').style.display = 'none';
            document.getElementById('connectionError').style.display = 'block';
            document.getElementById('connectionErrorText').textContent = result.message || result.error;
            document.getElementById('fetchProjectsBtn').disabled = true;
            showToast('Connection failed: ' + (result.message || result.error), 'error');
        }
    } catch (error) {
        document.getElementById('connectionStatus').style.display = 'block';
        document.getElementById('connectionSuccess').style.display = 'none';
        document.getElementById('connectionError').style.display = 'block';
        document.getElementById('connectionErrorText').textContent = error.message;
        document.getElementById('fetchProjectsBtn').disabled = true;
        showToast('Connection error: ' + error.message, 'error');
    } finally {
        testBtn.innerHTML = originalText;
        testBtn.disabled = false;
    }
}

async function fetchProjects() {
    const pcUrl = document.getElementById('pcUrlInput').value.trim();
    const username = document.getElementById('pcUsernameInput').value.trim() || 'admin';
    const password = document.getElementById('pcPasswordInput').value.trim() || 'Nutanix.123';
    
    if (!pcUrl) {
        showToast('Please enter a PC URL', 'error');
        return;
    }
    
    const fetchBtn = document.getElementById('fetchProjectsBtn');
    const originalText = fetchBtn.innerHTML;
    fetchBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Fetching...';
    fetchBtn.disabled = true;
    
    try {
        const response = await fetch('/api/live-uuid/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                pc_url: pcUrl,
                username: username,
                password: password
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentProjects = result.projects;
            populateProjectSelect(result.projects);
            document.getElementById('projectsSection').style.display = 'block';
            showToast(`Fetched ${result.projects.length} projects`, 'success');
        } else {
            showToast('Failed to fetch projects: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Error fetching projects: ' + error.message, 'error');
    } finally {
        fetchBtn.innerHTML = originalText;
        fetchBtn.disabled = false;
    }
}

function populateProjectSelect(projects) {
    console.log('populateProjectSelect called with projects:', projects);
    
    // Send log to backend
    fetch('/api/log-frontend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            level: 'INFO',
            message: `Frontend: populateProjectSelect called with ${projects.length} projects`,
            data: { project_count: projects.length, project_names: projects.map(p => p.name) }
        })
    }).catch(e => console.error('Failed to send log:', e));
    
    if (!projectDropdown) {
        console.log('Initializing project dropdowns...');
        initializeProjectDropdowns();
    }
    
    const projectData = projects.map(project => ({
        value: project.uuid,
        text: project.name,
        subtext: project.uuid,
        data: project
    }));
    
    console.log('Project dropdown data:', projectData);
    projectDropdown.setData(projectData);
}

function debouncedSearchProjects() {
    // Clear existing timeout
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }
    
    // Set new timeout to delay the search
    searchTimeout = setTimeout(searchProjects, 500); // 500ms delay
}

async function searchProjects() {
    const searchTerm = document.getElementById('projectSearchInput').value.trim();
    const searchInput = document.getElementById('projectSearchInput');
    
    // If search term is empty, fetch all projects
    if (!searchTerm) {
        await fetchProjects();
        return;
    }
    
    // Show loading state
    searchInput.style.opacity = '0.7';
    searchInput.disabled = true;
    
    // Make API call with search filter
    try {
        const pcUrl = document.getElementById('pcUrl').value;
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        if (!pcUrl || !username || !password) {
            showToast('Please fill in PC credentials first', 'error');
            return;
        }
        
        console.log(`Searching projects with term: "${searchTerm}"`);
        
        const response = await fetch('/api/live-uuid/projects', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pc_url: pcUrl,
                username: username,
                password: password,
                search_term: searchTerm  // This will trigger the backend filter
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentProjects = result.projects;
            populateProjectSelect(result.projects);
            console.log(`Found ${result.projects.length} projects matching "${searchTerm}"`);
            showToast(`Found ${result.projects.length} projects matching "${searchTerm}"`, 'success');
        } else {
            console.error('Search failed:', result.error);
            showToast(`Search failed: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error searching projects:', error);
        showToast('Error searching projects', 'error');
    } finally {
        // Restore input state
        searchInput.style.opacity = '1';
        searchInput.disabled = false;
    }
}

// GET SELECTED LIVE UUIDS FROM UI
function getSelectedLiveUUIDs() {
    console.log('=== COLLECTING LIVE UUIDS FROM UI ===');
    
    // Try to get from simple dropdowns first, then fall back to complex dropdowns
    const result = {
        project: { uuid: '', name: '' },
        account: { uuid: '', name: '' , pc_uuid: ''},
        cluster: { uuid: '', name: '' },
        environment: { uuid: '', name: '' },
        network: { uuid: '', name: '' },
        subnet: { uuid: '', name: '' },
        image: { uuid: '', name: '' }
    };
    
    // Project (from global variable)
    if (selectedProject) {
        result.project.uuid = selectedProject.uuid;
        result.project.name = selectedProject.name;
        console.log('Project from selectedProject:', result.project);
    }
    
    // Account - Send both original account_uuid and pc_uuid
    console.log('Account from selectedProject:', selectedProject);
    const simpleAccountSelect = document.getElementById('simpleAccountSelect');
    console.log('simpleAccountSelect:', simpleAccountSelect);
    if (simpleAccountSelect && simpleAccountSelect.value) {
        // Get the selected option to access its accuuid attribute
        const selectedOption = simpleAccountSelect.selectedOptions[0];
        const pcUuid = selectedOption?.getAttribute('accuuid');
        
        result.account.uuid = simpleAccountSelect.value; // Original account UUID
        result.account.pc_uuid = pcUuid; // PC UUID from selected option
        result.account.name = selectedOption?.textContent || simpleAccountSelect.value;
        result.account.original_uuid = simpleAccountSelect.value; // Original account UUID for images API
        
        console.log('Account from simple dropdown:', result.account);
        console.log('Selected option:', selectedOption);
        console.log('PC UUID from selected option:', pcUuid);
        console.log('Account UUID (original):', result.account.uuid);
        console.log('Account PC UUID (for payload):', result.account.pc_uuid);
        console.log('Account Original UUID (for images):', result.account.original_uuid);
    } else if (accountDropdown && accountDropdown.getValue()) {
        // For complex dropdown, we need to get the pc_uuid differently
        const selectedValue = accountDropdown.getValue();
        const accountSelect = document.getElementById('accountSelect');
        const selectedOption = accountSelect?.querySelector(`option[value="${selectedValue}"]`);
        const pcUuid = selectedOption?.getAttribute('accuuid');
        
        result.account.uuid = selectedValue;
        result.account.pc_uuid = pcUuid;
        result.account.name = accountDropdown.getText() || selectedValue;
        
        console.log('Account from complex dropdown:', result.account);
        console.log('Complex dropdown selected option:', selectedOption);
        console.log('Complex dropdown PC UUID:', pcUuid);
    }
    
    // Cluster - THIS IS THE KEY PART
    const simpleClusterSelect = document.getElementById('simpleClusterSelect');
    if (simpleClusterSelect && simpleClusterSelect.value) {
        result.cluster.uuid = simpleClusterSelect.value;
        result.cluster.name = simpleClusterSelect.selectedOptions[0]?.textContent || simpleClusterSelect.value;
        console.log('Cluster from simple dropdown:', result.cluster);
        console.log('Cluster dropdown value:', simpleClusterSelect.value);
        console.log('Cluster dropdown text:', simpleClusterSelect.selectedOptions[0]?.textContent);
    } else if (clusterDropdown && clusterDropdown.getValue()) {
        result.cluster.uuid = clusterDropdown.getValue();
        result.cluster.name = clusterDropdown.getText() || clusterDropdown.getValue();
        console.log('Cluster from complex dropdown:', result.cluster);
    }
    
    // Environment
    const simpleEnvironmentSelect = document.getElementById('simpleEnvironmentSelect');
    if (simpleEnvironmentSelect && simpleEnvironmentSelect.value) {
        result.environment.uuid = simpleEnvironmentSelect.value;
        result.environment.name = simpleEnvironmentSelect.selectedOptions[0]?.textContent || simpleEnvironmentSelect.value;
    } else if (environmentDropdown && environmentDropdown.getValue()) {
        result.environment.uuid = environmentDropdown.getValue();
        result.environment.name = environmentDropdown.getText() || environmentDropdown.getValue();
    }
    
    // Network
    const simpleNetworkSelect = document.getElementById('simpleNetworkSelect');
    if (simpleNetworkSelect && simpleNetworkSelect.value) {
        result.network.uuid = simpleNetworkSelect.value;
        result.network.name = simpleNetworkSelect.selectedOptions[0]?.textContent || simpleNetworkSelect.value;
    } else if (networkDropdown && networkDropdown.getValue()) {
        result.network.uuid = networkDropdown.getValue();
        result.network.name = networkDropdown.getText() || networkDropdown.getValue();
    }
    
    // Subnet
    const simpleSubnetSelect = document.getElementById('simpleSubnetSelect');
    if (simpleSubnetSelect && simpleSubnetSelect.value) {
        result.subnet.uuid = simpleSubnetSelect.value;
        result.subnet.name = simpleSubnetSelect.selectedOptions[0]?.textContent || simpleSubnetSelect.value;
    } else if (subnetDropdown && subnetDropdown.getValue()) {
        result.subnet.uuid = subnetDropdown.getValue();
        result.subnet.name = subnetDropdown.getText() || subnetDropdown.getValue();
    }
    
    // Image
    const simpleImageSelect = document.getElementById('simpleImageSelect');
    if (simpleImageSelect && simpleImageSelect.value) {
        result.image.uuid = simpleImageSelect.value;
        result.image.name = simpleImageSelect.selectedOptions[0]?.textContent || simpleImageSelect.value;
    } else if (imageDropdown && imageDropdown.getValue()) {
        result.image.uuid = imageDropdown.getValue();
        result.image.name = imageDropdown.getText() || imageDropdown.getValue();
    }
    
    console.log('Final collected live UUIDs:', result);
    return result;
}

// NEW SIMPLIFIED PROJECT SELECTION FUNCTION
function populateSimpleProjectResources(project) {
    console.log('=== SIMPLE PROJECT RESOURCES POPULATION ===');
    console.log('Project:', project.name);
    console.log('Resources:', project.resources);
    console.log('Resources.cluster_details:', project.resources?.cluster_details);
    console.log('Resources.cluster_reference_list:', project.resources?.cluster_reference_list);
    
    // Show the simple resources section
    const simpleSection = document.getElementById('simpleProjectResourcesSection');
    if (simpleSection) {
        simpleSection.style.display = 'block';
        console.log('Simple project resources section shown');
        
        // Send log to backend
        fetch('/api/log-frontend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                level: 'INFO',
                message: `Frontend: SIMPLE resources section shown successfully`,
                data: { project_name: project.name }
            })
        }).catch(e => console.error('Failed to send log:', e));
    } else {
        console.error('Simple project resources section not found!');
        return;
    }
    
    // Update project name
    const projectNameSpan = document.getElementById('selectedProjectName');
    if (projectNameSpan) {
        projectNameSpan.textContent = project.name;
    }
    
    const resources = project.resources || {};
    
    // Populate accounts with details fetched from API
    const accountSelect = document.getElementById('simpleAccountSelect');
    const accountCount = document.getElementById('accountCount');
    const accounts = resources.account_reference_list || [];
    
    console.log('Account data for details fetching:', accounts);
    console.log('Account data length:', accounts.length);
    
    accountSelect.innerHTML = '<option value="">Select account...</option>';
    accountCount.textContent = accounts.length;
    
    if (accounts.length > 0) {
        console.log('Found accounts, starting details fetch process:', accounts);
        // Show loading state
        accountSelect.innerHTML = '<option value="">Loading account details...</option>';
        
        // Fetch account details using the new API
        console.log('Calling fetchAccountDetails...');
        fetchAccountDetails(accounts).then(accountDetails => {
            console.log('fetchAccountDetails resolved with:', accountDetails);
            accountSelect.innerHTML = '<option value="">Select account...</option>';
            accountDetails.forEach(account => {
                const option = document.createElement('option');
                option.value = account.uuid; // Use original account_uuid as the value
                option.textContent = account.name;
                option.title = `Account UUID: ${account.uuid} | PC UUID: ${account.pc_uuid} | Status: ${account.status}`;
                option.setAttribute('accuuid', account.pc_uuid);
                console.log(`Account option created: ${account.name} | UUID: ${account.uuid} | PC UUID: ${account.pc_uuid}`);
                accountSelect.appendChild(option);
            });
            console.log('Account select: mohan', accountSelect);
        }).catch(error => {
            console.error('Error fetching account details:', error);
            console.error('Full error details:', error);
            // Fallback to original UUIDs if API fails
            accountSelect.innerHTML = '<option value="">Select account...</option>';
            accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account.uuid;
                option.textContent = account.name || account.uuid;
                accountSelect.appendChild(option);
            });
        });
    } else {
        console.log('No accounts found in project resources');
    }
    
    // Add auto-fetch images when account is selected
    accountSelect.addEventListener('change', function() {
        if (this.value) {
            console.log('Account selected, auto-fetching images...');
            fetchImages();
        }
    });
    
    // Populate clusters with names fetched from API
    const clusterSelect = document.getElementById('simpleClusterSelect');
    const clusterCount = document.getElementById('clusterCount');
    const clusters = resources.cluster_details || resources.cluster_reference_list || [];
    
    console.log('Cluster data for name fetching:', clusters);
    console.log('Cluster data length:', clusters.length);
    console.log('Cluster data type:', typeof clusters);
    console.log('Is clusters an array?', Array.isArray(clusters));
    
    clusterSelect.innerHTML = '<option value="">Select cluster...</option>';
    clusterCount.textContent = clusters.length;
    
    if (clusters.length > 0) {
        console.log('Found clusters, starting name fetch process:', clusters);
        // Show loading state
        clusterSelect.innerHTML = '<option value="">Loading cluster names...</option>';
        
        // Fetch cluster names using the new API
        console.log('Calling fetchClusterNames...');
        fetchClusterNames(clusters).then(clusterNames => {
            console.log('fetchClusterNames resolved with:', clusterNames);
            clusterSelect.innerHTML = '<option value="">Select cluster...</option>';
            clusterNames.forEach(cluster => {
                const option = document.createElement('option');
                option.value = cluster.uuid;
                option.textContent = cluster.name;
                option.title = `UUID: ${cluster.uuid} | Status: ${cluster.status}`;
                clusterSelect.appendChild(option);
            });
        }).catch(error => {
            console.error('Error fetching cluster names:', error);
            console.error('Full error details:', error);
            // Fallback to UUIDs if API fails
            clusterSelect.innerHTML = '<option value="">Select cluster...</option>';
            clusters.forEach(cluster => {
                const option = document.createElement('option');
                option.value = cluster.uuid;
                option.textContent = cluster.name || cluster.uuid;
                clusterSelect.appendChild(option);
            });
        });
    }
    
    // Populate environments
    const environmentSelect = document.getElementById('simpleEnvironmentSelect');
    const environmentCount = document.getElementById('environmentCount');
    const environments = resources.environment_reference_list || [];
    
    environmentSelect.innerHTML = '<option value="">Select environment...</option>';
    environments.forEach(env => {
        const option = document.createElement('option');
        option.value = env.uuid;
        option.textContent = env.name || env.uuid;
        environmentSelect.appendChild(option);
    });
    environmentCount.textContent = environments.length;
    
    // Populate networks
    const networkSelect = document.getElementById('simpleNetworkSelect');
    const networkCount = document.getElementById('networkCount');
    const networks = resources.external_network_list || [];
    
    networkSelect.innerHTML = '<option value="">Select network...</option>';
    networks.forEach(network => {
        const option = document.createElement('option');
        option.value = network.uuid;
        option.textContent = network.name || network.uuid;
        networkSelect.appendChild(option);
    });
    networkCount.textContent = networks.length;
    
    // Populate subnets
    const subnetSelect = document.getElementById('simpleSubnetSelect');
    const subnetCount = document.getElementById('subnetCount');
    const subnets = resources.subnet_reference_list || [];
    
    subnetSelect.innerHTML = '<option value="">Select subnet...</option>';
    subnets.forEach(subnet => {
        const option = document.createElement('option');
        option.value = subnet.uuid;
        option.textContent = subnet.name || subnet.uuid;
        subnetSelect.appendChild(option);
    });
    subnetCount.textContent = subnets.length;
    
    // Enable fetch images button
    const fetchBtn = document.getElementById('simpleFetchImagesBtn');
    if (fetchBtn) {
        fetchBtn.disabled = false;
    }
    
    console.log('=== SIMPLE RESOURCES POPULATED SUCCESSFULLY ===');
    console.log(`Accounts: ${accounts.length}, Clusters: ${clusters.length}, Environments: ${environments.length}, Networks: ${networks.length}, Subnets: ${subnets.length}`);
    
    // Send success log to backend
    fetch('/api/log-frontend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            level: 'INFO',
            message: `Frontend: SIMPLE resources populated successfully`,
            data: { 
                project_name: project.name,
                resource_counts: {
                    accounts: accounts.length,
                    clusters: clusters.length,
                    environments: environments.length,
                    networks: networks.length,
                    subnets: subnets.length
                }
            }
        })
    }).catch(e => console.error('Failed to send log:', e));
}

function onProjectSelected(project = null) {
    console.log('onProjectSelected called with:', project);
    
    // Send log to backend
    fetch('/api/log-frontend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            level: 'INFO',
            message: `Frontend: onProjectSelected called`,
            data: { 
                project_name: project ? project.name : 'null',
                project_uuid: project ? project.uuid : 'null',
                has_resources: project ? !!project.resources : false,
                resource_counts: project && project.resources ? {
                    accounts: (project.resources.account_reference_list || []).length,
                    clusters: (project.resources.cluster_reference_list || []).length,
                    environments: (project.resources.environment_reference_list || []).length,
                    networks: (project.resources.external_network_list || []).length,
                    subnets: (project.resources.subnet_reference_list || []).length
                } : null
            }
        })
    }).catch(e => console.error('Failed to send log:', e));
    
    if (project) {
        selectedProject = project;
        console.log('Selected project:', selectedProject.name);
        console.log('Selected project resources:', selectedProject.resources);
        
        // USE NEW SIMPLE APPROACH FIRST
        populateSimpleProjectResources(project);
        
        // Also try the original approach (for debugging)
        populateProjectResources(selectedProject.resources || {});
        
        // Check if the project resources section exists and show it
        const projectsSection = document.getElementById('projectsSection');
        const projectResourcesSection = document.getElementById('projectResourcesSection');
        const fetchImagesBtn = document.getElementById('fetchImagesBtn');
        
        // Check parent container first
        if (projectsSection) {
            const projectsSectionStyle = window.getComputedStyle(projectsSection);
            console.log('Projects section display style:', projectsSectionStyle.display);
            
            // Send detailed DOM debugging to backend
            fetch('/api/log-frontend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    level: 'INFO',
                    message: `Frontend: DOM Debug - Projects section found`,
                    data: { 
                        display_style: projectsSectionStyle.display,
                        visibility: projectsSectionStyle.visibility,
                        opacity: projectsSectionStyle.opacity
                    }
                })
            }).catch(e => console.error('Failed to send log:', e));
            
            if (projectsSectionStyle.display === 'none') {
                console.error('Projects section is hidden! This will prevent project resources from showing.');
                projectsSection.style.display = 'block';
                console.log('Forced projects section to be visible');
                
                fetch('/api/log-frontend', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        level: 'WARN',
                        message: `Frontend: Projects section was hidden, forced to be visible`,
                        data: {}
                    })
                }).catch(e => console.error('Failed to send log:', e));
            }
        } else {
            console.error('Projects section element not found!');
            fetch('/api/log-frontend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    level: 'ERROR',
                    message: `Frontend: Projects section element not found in DOM`,
                    data: {}
                })
            }).catch(e => console.error('Failed to send log:', e));
        }
        
        if (projectResourcesSection) {
            projectResourcesSection.style.display = 'block';
            console.log('Project resources section shown');
            
            const resourcesSectionStyle = window.getComputedStyle(projectResourcesSection);
            fetch('/api/log-frontend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    level: 'INFO',
                    message: `Frontend: Project resources section shown`,
                    data: { 
                        display_style: resourcesSectionStyle.display,
                        visibility: resourcesSectionStyle.visibility,
                        opacity: resourcesSectionStyle.opacity
                    }
                })
            }).catch(e => console.error('Failed to send log:', e));
        } else {
            console.error('Project resources section element not found!');
            fetch('/api/log-frontend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    level: 'ERROR',
                    message: `Frontend: Project resources section element not found in DOM`,
                    data: {}
                })
            }).catch(e => console.error('Failed to send log:', e));
        }
        
        if (fetchImagesBtn) {
            fetchImagesBtn.disabled = false;
            console.log('Fetch images button enabled');
        } else {
            console.error('Fetch images button not found!');
        }
        
        // Check if resources have actual content
        const hasResources = selectedProject.resources && 
            (
                (selectedProject.resources.account_reference_list && selectedProject.resources.account_reference_list.length > 0) ||
                (selectedProject.resources.cluster_reference_list && selectedProject.resources.cluster_reference_list.length > 0) ||
                (selectedProject.resources.environment_reference_list && selectedProject.resources.environment_reference_list.length > 0) ||
                (selectedProject.resources.external_network_list && selectedProject.resources.external_network_list.length > 0) ||
                (selectedProject.resources.subnet_reference_list && selectedProject.resources.subnet_reference_list.length > 0)
            );
        
        if (hasResources) {
            console.log('Project resources populated for:', selectedProject.name);
        } else {
            console.warn('Project has no resources or empty resource lists:', selectedProject.name);
            showToast(`Project "${selectedProject.name}" has no resources configured`, 'warning');
        }
    } else {
        selectedProject = null;
        document.getElementById('projectResourcesSection').style.display = 'none';
        document.getElementById('simpleProjectResourcesSection').style.display = 'none';
        document.getElementById('fetchImagesBtn').disabled = true;
        document.getElementById('simpleFetchImagesBtn').disabled = true;
        console.log('Project selection cleared');
    }
}

// Initialize all resource dropdowns
let accountDropdown = null;
let clusterDropdown = null;
let environmentDropdown = null;
let networkDropdown = null;
let subnetDropdown = null;

// Runbook-specific dropdowns
let runbookAccountDropdown = null;
let runbookClusterDropdown = null;
let runbookEnvironmentDropdown = null;
let runbookNetworkDropdown = null;
let runbookSubnetDropdown = null;

function initializeResourceDropdowns() {
    console.log('Initializing resource dropdowns...');
    
    // Check if containers exist
    const containers = [
        'accountSelectContainer',
        'clusterSelectContainer', 
        'environmentSelectContainer',
        'networkSelectContainer',
        'subnetSelectContainer'
    ];
    
    let allContainersFound = true;
    containers.forEach(containerId => {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container ${containerId} not found in DOM`);
            allContainersFound = false;
        } else {
            console.log(`Container ${containerId} found`);
        }
    });
    
    if (!allContainersFound) {
        console.error('Some dropdown containers are missing - this may prevent resource dropdowns from working');
        fetch('/api/log-frontend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                level: 'ERROR',
                message: `Frontend: Some dropdown containers are missing from DOM`,
                data: { containers_checked: containers }
            })
        }).catch(e => console.error('Failed to send log:', e));
    } else {
        fetch('/api/log-frontend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                level: 'INFO',
                message: `Frontend: All dropdown containers found in DOM`,
                data: { containers_found: containers }
            })
        }).catch(e => console.error('Failed to send log:', e));
    }
    
    if (!accountDropdown) {
        const accountContainer = document.getElementById('accountSelectContainer');
        if (accountContainer) {
        accountDropdown = new SearchableDropdown('accountSelectContainer', {
            placeholder: 'Select account...',
            searchPlaceholder: 'Search accounts...',
            noResultsText: 'No accounts found'
        });
            console.log('Account dropdown initialized');
        } else {
            console.error('Account container not found, cannot initialize dropdown');
        }
    }
    
    if (!clusterDropdown) {
        const clusterContainer = document.getElementById('clusterSelectContainer');
        if (clusterContainer) {
        clusterDropdown = new SearchableDropdown('clusterSelectContainer', {
            placeholder: 'Select cluster...',
            searchPlaceholder: 'Search clusters...',
            noResultsText: 'No clusters found'
        });
            console.log('Cluster dropdown initialized');
        } else {
            console.error('Cluster container not found, cannot initialize dropdown');
        }
    }
    
    if (!environmentDropdown) {
        const environmentContainer = document.getElementById('environmentSelectContainer');
        if (environmentContainer) {
        environmentDropdown = new SearchableDropdown('environmentSelectContainer', {
            placeholder: 'Select environment...',
            searchPlaceholder: 'Search environments...',
            noResultsText: 'No environments found'
        });
            console.log('Environment dropdown initialized');
        } else {
            console.error('Environment container not found, cannot initialize dropdown');
        }
    }
    
    if (!networkDropdown) {
        const networkContainer = document.getElementById('networkSelectContainer');
        if (networkContainer) {
        networkDropdown = new SearchableDropdown('networkSelectContainer', {
            placeholder: 'Select network...',
            searchPlaceholder: 'Search networks...',
            noResultsText: 'No networks found'
        });
            console.log('Network dropdown initialized');
        } else {
            console.error('Network container not found, cannot initialize dropdown');
        }
    }
    
    if (!subnetDropdown) {
        const subnetContainer = document.getElementById('subnetSelectContainer');
        if (subnetContainer) {
        subnetDropdown = new SearchableDropdown('subnetSelectContainer', {
            placeholder: 'Select subnet...',
            searchPlaceholder: 'Search subnets...',
            noResultsText: 'No subnets found'
        });
            console.log('Subnet dropdown initialized');
        } else {
            console.error('Subnet container not found, cannot initialize dropdown');
        }
    }
}

function initializeRunbookResourceDropdowns() {
    if (!runbookAccountDropdown) {
        runbookAccountDropdown = new SearchableDropdown('runbookAccountSelectContainer', {
            placeholder: 'Select account...',
            searchPlaceholder: 'Search accounts...',
            noResultsText: 'No accounts found'
        });
    }
    
    if (!runbookClusterDropdown) {
        runbookClusterDropdown = new SearchableDropdown('runbookClusterSelectContainer', {
            placeholder: 'Select cluster...',
            searchPlaceholder: 'Search clusters...',
            noResultsText: 'No clusters found'
        });
    }
}

function populateProjectResources(resources) {
    console.log('populateProjectResources called with:', resources);
    
    // Ensure resources is an object
    if (!resources || typeof resources !== 'object') {
        console.warn('Resources is not a valid object, using empty object');
        resources = {};
    }
    
    // Send detailed log to backend
    const resourceCounts = {
        accounts: (resources.account_reference_list || []).length,
        clusters: (resources.cluster_reference_list || []).length,
        environments: (resources.environment_reference_list || []).length,
        networks: (resources.external_network_list || []).length,
        subnets: (resources.subnet_reference_list || []).length
    };
    
    console.log('Resource counts:', resourceCounts);
    
    fetch('/api/log-frontend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            level: 'INFO',
            message: `Frontend: populateProjectResources called`,
            data: { 
                resource_counts: resourceCounts,
                account_details: resources.account_reference_list || [],
                cluster_details: resources.cluster_reference_list || []
            }
        })
    }).catch(e => console.error('Failed to send log:', e));
    
    initializeResourceDropdowns();
    
    // Populate account dropdown
    const accountData = (resources.account_reference_list || []).map(account => ({
        value: account.uuid,
        text: account.name || account.uuid,
        subtext: account.uuid,
        data: account
    }));
    console.log('Account data:', accountData);
    if (accountDropdown) {
    accountDropdown.setData(accountData);
    } else {
        console.error('Account dropdown not initialized');
    }
    
    // Populate cluster dropdown
    const clusterData = (resources.cluster_reference_list || []).map(cluster => ({
        value: cluster.uuid,
        text: cluster.name || cluster.uuid,
        subtext: cluster.uuid,
        data: cluster
    }));
    console.log('Cluster data:', clusterData);
    if (clusterDropdown) {
    clusterDropdown.setData(clusterData);
    } else {
        console.error('Cluster dropdown not initialized');
    }
    
    // Populate environment dropdown
    const environmentData = (resources.environment_reference_list || []).map(env => ({
        value: env.uuid,
        text: env.name || env.uuid,
        subtext: env.uuid,
        data: env
    }));
    console.log('Environment data:', environmentData);
    if (environmentDropdown) {
    environmentDropdown.setData(environmentData);
    } else {
        console.error('Environment dropdown not initialized');
    }
    
    // Populate network dropdown
    const networkData = (resources.external_network_list || []).map(network => ({
        value: network.uuid,
        text: network.name || network.uuid,
        subtext: network.uuid,
        data: network
    }));
    console.log('Network data:', networkData);
    if (networkDropdown) {
    networkDropdown.setData(networkData);
    } else {
        console.error('Network dropdown not initialized');
    }
    
    // Populate subnet dropdown
    const subnetData = (resources.subnet_reference_list || []).map(subnet => ({
        value: subnet.uuid,
        text: subnet.name || subnet.uuid,
        subtext: subnet.uuid,
        data: subnet
    }));
    console.log('Subnet data:', subnetData);
    if (subnetDropdown) {
    subnetDropdown.setData(subnetData);
    } else {
        console.error('Subnet dropdown not initialized');
    }
    
    // Log completion
    fetch('/api/log-frontend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            level: 'INFO',
            message: `Frontend: Project resources populated successfully`,
            data: { resource_counts: resourceCounts }
        })
    }).catch(e => console.error('Failed to send log:', e));
    
    // Set default environment if available
    if (resources.default_environment_reference && resources.default_environment_reference.uuid) {
        environmentSelect.value = resources.default_environment_reference.uuid;
    }
    
    // Populate network dropdown
    const networkSelect = document.getElementById('networkSelect');
    networkSelect.innerHTML = '<option value="">Select network...</option>';
    (resources.external_network_list || []).forEach(network => {
        const option = document.createElement('option');
        option.value = network.uuid;
        option.textContent = network.name || network.uuid;
        networkSelect.appendChild(option);
    });
    
    // Populate subnet dropdown
    const subnetSelect = document.getElementById('subnetSelect');
    subnetSelect.innerHTML = '<option value="">Select subnet...</option>';
    (resources.subnet_reference_list || []).forEach(subnet => {
        const option = document.createElement('option');
        option.value = subnet.uuid;
        option.textContent = subnet.name || subnet.uuid;
        subnetSelect.appendChild(option);
    });
}

async function fetchImages() {
    const pcUrl = document.getElementById('pcUrlInput').value.trim();
    const username = document.getElementById('pcUsernameInput').value.trim() || 'admin';
    const password = document.getElementById('pcPasswordInput').value.trim() || 'Nutanix.123';
    
    // Try to get account UUID from new simple dropdown first, then fall back to old dropdown
    let accountUuid = '';
    const simpleAccountSelect = document.getElementById('simpleAccountSelect');
    if (simpleAccountSelect && simpleAccountSelect.value) {
        accountUuid = simpleAccountSelect.value;
    } else if (accountDropdown) {
        accountUuid = accountDropdown.getValue();
    }
    
    const projectUuid = selectedProject ? selectedProject.uuid : '';
    
    if (!pcUrl) {
        showToast('Please enter a PC URL', 'error');
        return;
    }
    
    if (!accountUuid) {
        showToast('Please select an account first', 'error');
        return;
    }
    
    // Try to get the simple fetch button first, then fall back to old one
    let fetchBtn = document.getElementById('simpleFetchImagesBtn');
    if (!fetchBtn) {
        fetchBtn = document.getElementById('fetchImagesBtn');
    }
    
    if (!fetchBtn) {
        console.error('No fetch images button found!');
        return;
    }
    
    const originalText = fetchBtn.innerHTML;
    fetchBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Fetching...';
    fetchBtn.disabled = true;
    
    try {
        const response = await fetch('/api/live-uuid/images', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                pc_url: pcUrl,
                username: username,
                password: password,
                account_uuid: accountUuid,  // accountUuid is the original account UUID from account details
                project_uuid: projectUuid
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            populateImageSelect(result.images);
            showToast(`Fetched ${result.images.length} images`, 'success');
        } else {
            showToast('Failed to fetch images: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Error fetching images: ' + error.message, 'error');
    } finally {
        fetchBtn.innerHTML = originalText;
        fetchBtn.disabled = false;
    }
}

// Initialize searchable dropdowns
let imageDropdown = null;
let runbookImageDropdown = null;
let projectDropdown = null;
let runbookProjectDropdown = null;

function initializeImageDropdowns() {
    if (!imageDropdown) {
        imageDropdown = new SearchableDropdown('imageSelectContainer', {
            placeholder: 'Select image...',
            searchPlaceholder: 'Search images...',
            noResultsText: 'No images found',
            onSelect: (value, text, data) => {
                console.log('Image selected:', data);
            }
        });
    }
    
    if (!runbookImageDropdown) {
        runbookImageDropdown = new SearchableDropdown('runbookImageSelectContainer', {
            placeholder: 'Select image...',
            searchPlaceholder: 'Search images...',
            noResultsText: 'No images found',
            onSelect: (value, text, data) => {
                console.log('Runbook image selected:', data);
            }
        });
    }
}

function initializeProjectDropdowns() {
    if (!projectDropdown) {
        projectDropdown = new SearchableDropdown('projectSelectContainer', {
            placeholder: 'Choose a project...',
            searchPlaceholder: 'Search projects...',
            noResultsText: 'No projects found',
            onSelect: (value, text, itemData) => {
                console.log('Project dropdown onSelect called:', { value, text, itemData });
                
                // Send log to backend
                fetch('/api/log-frontend', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        level: 'INFO',
                        message: `Frontend: Project dropdown onSelect triggered`,
                        data: { 
                            value: value,
                            text: text,
                            has_item_data: !!itemData,
                            has_project_data: !!(itemData && itemData.data)
                        }
                    })
                }).catch(e => console.error('Failed to send log:', e));
                
                if (itemData && itemData.data) {
                    onProjectSelected(itemData.data);
                } else {
                    console.error('Project data not found in dropdown selection');
                    
                    // Log error to backend
                    fetch('/api/log-frontend', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            level: 'ERROR',
                            message: `Frontend: Project data not found in dropdown selection`,
                            data: { value, text, itemData }
                        })
                    }).catch(e => console.error('Failed to send log:', e));
                }
            }
        });
    }
    
    if (!runbookProjectDropdown) {
        runbookProjectDropdown = new SearchableDropdown('runbookProjectSelectContainer', {
            placeholder: 'Choose a project...',
            searchPlaceholder: 'Search projects...',
            noResultsText: 'No projects found',
            onSelect: (value, text, itemData) => {
                console.log('Runbook project dropdown onSelect called:', { value, text, itemData });
                if (itemData && itemData.data) {
                    onRunbookProjectSelected(itemData.data);
                } else {
                    console.error('Runbook project data not found in dropdown selection');
                }
            }
        });
    }
}

// NEW SIMPLE IMAGE POPULATION FUNCTION
function populateSimpleImageSelect(images) {
    console.log('=== POPULATING SIMPLE IMAGE SELECT ===');
    console.log(`Received ${images.length} images`);
    
    const imageSelect = document.getElementById('simpleImageSelect');
    const imageCount = document.getElementById('imageCount');
    
    if (!imageSelect) {
        console.error('Simple image select element not found!');
        return;
    }
    
    // Clear existing options
    imageSelect.innerHTML = '<option value="">Select image...</option>';
    
    // Populate with images
    images.forEach((image, index) => {
        const option = document.createElement('option');
        option.value = image.uuid;
        option.textContent = image.name || `Unnamed Image ${index + 1}`;
        imageSelect.appendChild(option);
    });
    
    // Update count
    if (imageCount) {
        imageCount.textContent = images.length;
    }
    
    console.log(`Successfully populated ${images.length} images in simple dropdown`);
    
    // Send success log to backend
    fetch('/api/log-frontend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            level: 'INFO',
            message: `Frontend: SIMPLE images populated successfully`,
            data: { 
                image_count: images.length,
                first_few_images: images.slice(0, 5).map(img => ({
                    name: img.name,
                    uuid: img.uuid,
                    type: img.image_type
                }))
            }
        })
    }).catch(e => console.error('Failed to send log:', e));
}

function populateImageSelect(images) {
    // Use new simple approach first
    populateSimpleImageSelect(images);
    
    // Also populate old dropdown for backward compatibility
    if (!imageDropdown) {
        initializeImageDropdowns();
    }
    
    const dropdownData = images.map(image => ({
        value: image.uuid,
        text: image.name || 'Unnamed Image',
        subtext: `${image.image_type || 'DISK_IMAGE'} • ${formatFileSize(image.vmdisk_size)}`,
        data: image
    }));
    
    imageDropdown.setData(dropdownData);
}

function formatFileSize(bytes) {
    if (!bytes || bytes === '') return 'Unknown size';
    const size = parseInt(bytes);
    if (isNaN(size)) return 'Unknown size';
    
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let unitIndex = 0;
    let fileSize = size;
    
    while (fileSize >= 1024 && unitIndex < units.length - 1) {
        fileSize /= 1024;
        unitIndex++;
    }
    
    return `${fileSize.toFixed(1)} ${units[unitIndex]}`;
}


// ============================================================================
// RUNBOOK LIVE UUID FUNCTIONS
// ============================================================================

let currentRunbookProjects = [];
let selectedRunbookProject = null;

async function testRunbookPCConnection() {
    const pcUrl = document.getElementById('runbookPcUrlInput').value.trim();
    const username = document.getElementById('runbookPcUsernameInput').value.trim() || 'admin';
    const password = document.getElementById('runbookPcPasswordInput').value.trim() || 'Nutanix.123';
    
    if (!pcUrl) {
        showToast('Please enter a PC URL', 'error');
        return;
    }
    
    const testBtn = document.getElementById('runbookTestConnectionBtn');
    const originalText = testBtn.innerHTML;
    testBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Testing...';
    testBtn.disabled = true;
    
    try {
        const response = await fetch('/api/live-uuid/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                pc_url: pcUrl,
                username: username,
                password: password
            })
        });
        
        const result = await response.json();
        
        document.getElementById('runbookConnectionStatus').style.display = 'block';
        
        if (result.success) {
            document.getElementById('runbookConnectionSuccess').style.display = 'block';
            document.getElementById('runbookConnectionError').style.display = 'none';
            document.getElementById('runbookFetchProjectsBtn').disabled = false;
            showToast('Connection successful!', 'success');
        } else {
            document.getElementById('runbookConnectionSuccess').style.display = 'none';
            document.getElementById('runbookConnectionError').style.display = 'block';
            document.getElementById('runbookConnectionErrorText').textContent = result.message || result.error;
            document.getElementById('runbookFetchProjectsBtn').disabled = true;
            showToast('Connection failed: ' + (result.message || result.error), 'error');
        }
    } catch (error) {
        document.getElementById('runbookConnectionStatus').style.display = 'block';
        document.getElementById('runbookConnectionSuccess').style.display = 'none';
        document.getElementById('runbookConnectionError').style.display = 'block';
        document.getElementById('runbookConnectionErrorText').textContent = error.message;
        document.getElementById('runbookFetchProjectsBtn').disabled = true;
        showToast('Connection error: ' + error.message, 'error');
    } finally {
        testBtn.innerHTML = originalText;
        testBtn.disabled = false;
    }
}

async function fetchRunbookProjects() {
    const pcUrl = document.getElementById('runbookPcUrlInput').value.trim();
    const username = document.getElementById('runbookPcUsernameInput').value.trim() || 'admin';
    const password = document.getElementById('runbookPcPasswordInput').value.trim() || 'Nutanix.123';
    
    if (!pcUrl) {
        showToast('Please enter a PC URL', 'error');
        return;
    }
    
    const fetchBtn = document.getElementById('runbookFetchProjectsBtn');
    const originalText = fetchBtn.innerHTML;
    fetchBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Fetching...';
    fetchBtn.disabled = true;
    
    try {
        const response = await fetch('/api/live-uuid/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                pc_url: pcUrl,
                username: username,
                password: password
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentRunbookProjects = result.projects;
            populateRunbookProjectSelect(result.projects);
            document.getElementById('runbookProjectsSection').style.display = 'block';
            showToast(`Fetched ${result.projects.length} projects`, 'success');
        } else {
            showToast('Failed to fetch projects: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Error fetching projects: ' + error.message, 'error');
    } finally {
        fetchBtn.innerHTML = originalText;
        fetchBtn.disabled = false;
    }
}

function populateRunbookProjectSelect(projects) {
    if (!runbookProjectDropdown) {
        initializeProjectDropdowns();
    }
    
    const projectData = projects.map(project => ({
        value: project.uuid,
        text: project.name,
        subtext: project.uuid,
        data: project
    }));
    
    runbookProjectDropdown.setData(projectData);
}

function debouncedSearchRunbookProjects() {
    // Clear existing timeout
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }
    
    // Set new timeout to delay the search
    searchTimeout = setTimeout(searchRunbookProjects, 500); // 500ms delay
}

async function searchRunbookProjects() {
    const searchTerm = document.getElementById('runbookProjectSearchInput').value.trim();
    const searchInput = document.getElementById('runbookProjectSearchInput');
    
    // If search term is empty, fetch all projects
    if (!searchTerm) {
        await fetchRunbookProjects();
        return;
    }
    
    // Show loading state
    searchInput.style.opacity = '0.7';
    searchInput.disabled = true;
    
    // Make API call with search filter
    try {
        const pcUrl = document.getElementById('runbookPcUrl').value;
        const username = document.getElementById('runbookUsername').value;
        const password = document.getElementById('runbookPassword').value;
        
        if (!pcUrl || !username || !password) {
            showToast('Please fill in PC credentials first', 'error');
            return;
        }
        
        console.log(`Searching runbook projects with term: "${searchTerm}"`);
        
        const response = await fetch('/api/live-uuid/projects', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pc_url: pcUrl,
                username: username,
                password: password,
                search_term: searchTerm  // This will trigger the backend filter
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentRunbookProjects = result.projects;
            populateRunbookProjectSelect(result.projects);
            console.log(`Found ${result.projects.length} runbook projects matching "${searchTerm}"`);
            showToast(`Found ${result.projects.length} projects matching "${searchTerm}"`, 'success');
        } else {
            console.error('Runbook search failed:', result.error);
            showToast(`Search failed: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error searching runbook projects:', error);
        showToast('Error searching runbook projects', 'error');
    } finally {
        // Restore input state
        searchInput.style.opacity = '1';
        searchInput.disabled = false;
    }
}

function onRunbookProjectSelected(project = null) {
    if (project) {
        selectedRunbookProject = project;
        populateRunbookProjectResources(selectedRunbookProject.resources);
        document.getElementById('runbookProjectResourcesSection').style.display = 'block';
        document.getElementById('runbookFetchImagesBtn').disabled = false;
        console.log('Runbook project selected:', selectedRunbookProject.name);
    } else {
        selectedRunbookProject = null;
        document.getElementById('runbookProjectResourcesSection').style.display = 'none';
        document.getElementById('runbookFetchImagesBtn').disabled = true;
    }
}

function populateRunbookProjectResources(resources) {
    initializeRunbookResourceDropdowns();
    
    // Populate account dropdown
    const accountData = (resources.account_reference_list || []).map(account => ({
        value: account.uuid,
        text: account.name || account.uuid,
        subtext: account.uuid,
        data: account
    }));
    runbookAccountDropdown.setData(accountData);
    
    // Populate cluster dropdown
    const clusterData = (resources.cluster_reference_list || []).map(cluster => ({
        value: cluster.uuid,
        text: cluster.name || cluster.uuid,
        subtext: cluster.uuid,
        data: cluster
    }));
    runbookClusterDropdown.setData(clusterData);
    
    // Populate environment dropdown
    const environmentSelect = document.getElementById('runbookEnvironmentSelect');
    environmentSelect.innerHTML = '<option value="">Select environment...</option>';
    (resources.environment_reference_list || []).forEach(env => {
        const option = document.createElement('option');
        option.value = env.uuid;
        option.textContent = env.name || env.uuid;
        environmentSelect.appendChild(option);
    });
    
    // Set default environment if available
    if (resources.default_environment_reference && resources.default_environment_reference.uuid) {
        environmentSelect.value = resources.default_environment_reference.uuid;
    }
    
    // Populate network dropdown
    const networkSelect = document.getElementById('runbookNetworkSelect');
    networkSelect.innerHTML = '<option value="">Select network...</option>';
    (resources.external_network_list || []).forEach(network => {
        const option = document.createElement('option');
        option.value = network.uuid;
        option.textContent = network.name || network.uuid;
        networkSelect.appendChild(option);
    });
    
    // Populate subnet dropdown
    const subnetSelect = document.getElementById('runbookSubnetSelect');
    subnetSelect.innerHTML = '<option value="">Select subnet...</option>';
    (resources.subnet_reference_list || []).forEach(subnet => {
        const option = document.createElement('option');
        option.value = subnet.uuid;
        option.textContent = subnet.name || subnet.uuid;
        subnetSelect.appendChild(option);
    });
}

async function fetchRunbookImages() {
    const pcUrl = document.getElementById('runbookPcUrlInput').value.trim();
    const username = document.getElementById('runbookPcUsernameInput').value.trim() || 'admin';
    const password = document.getElementById('runbookPcPasswordInput').value.trim() || 'Nutanix.123';
    const accountUuid = runbookAccountDropdown ? runbookAccountDropdown.getValue() : '';
    const projectUuid = selectedRunbookProject ? selectedRunbookProject.uuid : '';
    
    if (!pcUrl) {
        showToast('Please enter a PC URL', 'error');
        return;
    }
    
    if (!accountUuid) {
        showToast('Please select an account first', 'error');
        return;
    }
    
    const fetchBtn = document.getElementById('runbookFetchImagesBtn');
    const originalText = fetchBtn.innerHTML;
    fetchBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Fetching...';
    fetchBtn.disabled = true;
    
    try {
        const response = await fetch('/api/live-uuid/images', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                pc_url: pcUrl,
                username: username,
                password: password,
                account_uuid: accountUuid,  // For runbooks, this should also be original account UUID
                project_uuid: projectUuid
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            populateRunbookImageSelect(result.images);
            showToast(`Fetched ${result.images.length} images`, 'success');
        } else {
            showToast('Failed to fetch images: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Error fetching images: ' + error.message, 'error');
    } finally {
        fetchBtn.innerHTML = originalText;
        fetchBtn.disabled = false;
    }
}

function populateRunbookImageSelect(images) {
    if (!runbookImageDropdown) {
        initializeImageDropdowns();
    }
    
    const dropdownData = images.map(image => ({
        value: image.uuid,
        text: image.name || 'Unnamed Image',
        subtext: `${image.image_type || 'DISK_IMAGE'} • ${formatFileSize(image.vmdisk_size)}`,
        data: image
    }));
    
    runbookImageDropdown.setData(dropdownData);
}

// Helper function to get selected UUIDs for runbook use in payload generation
function getSelectedRunbookLiveUUIDs() {
    return {
        project: {
            uuid: selectedRunbookProject ? selectedRunbookProject.uuid : '',
            name: selectedRunbookProject ? selectedRunbookProject.name : ''
        },
        account: {
            uuid: runbookAccountDropdown ? runbookAccountDropdown.getValue() : '',
            name: runbookAccountDropdown ? runbookAccountDropdown.getText() : ''
        },
        cluster: {
            uuid: runbookClusterDropdown ? runbookClusterDropdown.getValue() : '',
            name: runbookClusterDropdown ? runbookClusterDropdown.getText() : ''
        },
        environment: {
            uuid: document.getElementById('runbookEnvironmentSelect').value,
            name: document.getElementById('runbookEnvironmentSelect').selectedOptions[0]?.textContent || ''
        },
        network: {
            uuid: document.getElementById('runbookNetworkSelect').value,
            name: document.getElementById('runbookNetworkSelect').selectedOptions[0]?.textContent || ''
        },
        subnet: {
            uuid: document.getElementById('runbookSubnetSelect').value,
            name: document.getElementById('runbookSubnetSelect').selectedOptions[0]?.textContent || ''
        },
        image: {
            uuid: runbookImageDropdown ? runbookImageDropdown.getValue() : '',
            name: runbookImageDropdown ? runbookImageDropdown.getText() : ''
        }
    };
}

async function analyzePayloadForRules() {
    const payload = document.getElementById('rulesPayloadInput').value.trim();
    const apiType = document.getElementById('apiTypeSelect').value;
    
    if (!payload) {
        showToast('Please enter a JSON payload', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        // Always use "blueprint" as entity name for blueprint type
        if (apiType === 'blueprint') {
            rulesEntityName = 'blueprint';
        } else {
        rulesEntityName = generateEntityName(payload, apiType);
        }
        rulesExistingEntity = null;
        
        const response = await fetch('/api/rules/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ payload, api_url: rulesEntityName, api_type: apiType })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error);
        
        rulesOriginalPayload = data.original_payload;
        rulesEntities = data.entities;
        
        // Update dropdown if API type was auto-detected from payload
        const detectedType = data.detected_api_type;
        if (detectedType && detectedType !== apiType) {
            document.getElementById('apiTypeSelect').value = detectedType;
            // Always use "blueprint" for blueprint type
            if (detectedType === 'blueprint') {
                rulesEntityName = 'blueprint';
            } else {
            rulesEntityName = generateEntityName(payload, detectedType);
            }
            showToast(`Auto-detected entity type: ${detectedType}`, 'info');
        }
        
        // Check if entity already exists
        await checkExistingEntity(rulesEntityName);
        
        // Initialize temp counts
        rulesTempCounts = {};
        rulesEntities.forEach(e => rulesTempCounts[e.path] = e.current_count);
        
        // Load default rules for detected type
        await loadDefaultRules(detectedType || apiType);
        
        // Render UI
        renderRulesEntities();
        renderRulesRulesList();
        
        // Go to step 2
        goToRulesStep(2);
        
        showLoading(false);
    } catch (e) {
        showLoading(false);
        showToast(e.message, 'error');
    }
}

async function checkExistingEntity(entityName) {
    try {
        const response = await fetch(`/api/rules/${encodeURIComponent(entityName)}?include_template=true`);
        if (response.ok) {
            rulesExistingEntity = await response.json();
            
            // Load existing rules and merge with any new ones
            if (rulesExistingEntity.rules && rulesExistingEntity.rules.length > 0) {
                // Mark existing rules
                const existingRules = rulesExistingEntity.rules.map(r => ({
                    ...r,
                    isExisting: true
                }));
                
                // Merge: existing rules + new custom rules (avoid duplicates)
                const newRulesJson = rulesCustomRules.map(r => JSON.stringify(r));
                const mergedRules = [...existingRules];
                
                rulesCustomRules.forEach(newRule => {
                    const newRuleJson = JSON.stringify({...newRule, isExisting: undefined});
                    const isDuplicate = existingRules.some(existing => {
                        const existingJson = JSON.stringify({...existing, isExisting: undefined});
                        return existingJson === newRuleJson;
                    });
                    if (!isDuplicate) {
                        mergedRules.push({...newRule, isNew: true});
                    }
                });
                
                rulesCustomRules = mergedRules;
                showToast(`Loaded ${existingRules.length} existing rules for "${entityName}"`, 'info');
            }
        }
    } catch (e) {
        // Entity doesn't exist, that's fine
        rulesExistingEntity = null;
    }
}

function renderRulesEntities() {
    const activeEntities = rulesEntities.filter(e => rulesTempCounts[e.path] > 0);
    const tree = buildEntityTree(activeEntities);
    const container = document.getElementById('rulesEntitiesTree');
    
    let html = '';
    Object.values(tree.children).forEach(node => {
        html += renderTreeNode(node, 0, 'rules');
    });
    container.innerHTML = html || '<p style="color: var(--text-secondary)">No active entities</p>';
    
    // Update entity count badge
    document.getElementById('rulesEntitiesBadge').textContent = activeEntities.length;
    
    renderRulesExcluded();
}

function renderRulesExcluded() {
    const excluded = rulesEntities.filter(e => rulesTempCounts[e.path] === 0);
    const section = document.getElementById('rulesExcludedSection');
    const list = document.getElementById('rulesExcludedList');
    const badge = document.getElementById('rulesExcludedBadge');
    
    if (excluded.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    badge.textContent = excluded.length;
    
    list.innerHTML = excluded.map(e => `
        <div class="excluded-item">
            <span class="excluded-path">${e.path}</span>
            <button class="restore-btn" onclick="restoreRulesEntity('${e.path}')">
                <i class="bi bi-plus-circle me-1"></i> Restore
            </button>
                </div>
    `).join('');
}

function updateRulesTempCount(path, value) {
    rulesTempCounts[path] = parseInt(value) || 0;
    if (rulesTempCounts[path] === 0) {
        // Just update the excluded list, don't re-render entire tree
        updateRulesEntityVisibility(path, false);
    }
    // Update the badge count display
    const nodeId = `rules_${path.replace(/\./g, '_')}`;
    const badge = document.querySelector(`#toggle_${nodeId}`)?.closest('.tree-node-header')?.querySelector('.entity-count-badge');
    if (badge) {
        badge.textContent = `${rulesTempCounts[path]} items`;
    }
}

function updateRulesEntityVisibility(path, visible) {
    const nodeId = `rules_${path.replace(/\./g, '_')}`;
    const node = document.getElementById(`toggle_${nodeId}`)?.closest('.tree-node');
    
    if (!visible && node) {
        // Hide the node
        node.style.display = 'none';
    } else if (visible && node) {
        node.style.display = 'block';
    }
    
    // Re-render excluded list only
    renderRulesExcluded();
}

function excludeRulesEntity(path) {
    rulesTempCounts[path] = 0;
    updateRulesEntityVisibility(path, false);
}

function restoreRulesEntity(path) {
    rulesTempCounts[path] = 1;
    // Show the node again
    const nodeId = `rules_${path.replace(/\./g, '_')}`;
    const node = document.getElementById(`toggle_${nodeId}`)?.closest('.tree-node');
    
    if (node) {
        node.style.display = 'block';
        renderRulesExcluded();
    } else {
        // Node doesn't exist, need to re-render
        renderRulesEntities();
    }
}

function renderRulesRulesList() {
    const container = document.getElementById('rulesRulesList');
    const allRules = [
        ...rulesDefaultRules.map(r => ({...r, isDefault: true})),
        ...rulesCustomRules
    ];
    
    // Count by type
    const defaultCount = rulesDefaultRules.length;
    const existingCount = rulesCustomRules.filter(r => r.isExisting).length;
    const newCount = rulesCustomRules.filter(r => r.isNew).length;
    const customCount = rulesCustomRules.filter(r => !r.isExisting && !r.isNew).length;
    
    document.getElementById('rulesRulesBadge').textContent = allRules.length;
    
    if (allRules.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary)">No rules defined</p>';
        return;
    }

    // Add summary header if there are existing rules
    let summaryHtml = '';
    if (existingCount > 0 || newCount > 0) {
        summaryHtml = `
            <div class="rules-summary">
                ${existingCount > 0 ? `<span class="rules-summary-item existing"><i class="bi bi-database"></i> ${existingCount} existing</span>` : ''}
                ${newCount > 0 ? `<span class="rules-summary-item new"><i class="bi bi-plus-circle"></i> ${newCount} new</span>` : ''}
                ${customCount > 0 ? `<span class="rules-summary-item custom"><i class="bi bi-pencil"></i> ${customCount} custom</span>` : ''}
                ${defaultCount > 0 ? `<span class="rules-summary-item default"><i class="bi bi-shield"></i> ${defaultCount} default</span>` : ''}
            </div>
        `;
    }

    container.innerHTML = summaryHtml + allRules.map((rule, idx) => {
        const isDefault = rule.isDefault;
        const isExisting = rule.isExisting;
        const isNew = rule.isNew;
        
        let badgeClass = 'bg-primary';
        let badgeText = 'CUSTOM';
        let itemClass = '';
        
        if (isDefault) {
            badgeClass = 'bg-secondary';
            badgeText = 'DEFAULT';
            itemClass = 'default-rule';
        } else if (isExisting) {
            badgeClass = 'bg-info';
            badgeText = 'EXISTING';
            itemClass = 'existing-rule';
        } else if (isNew) {
            badgeClass = 'bg-success';
            badgeText = 'NEW';
            itemClass = 'new-rule';
        }
        
        const customIdx = idx - rulesDefaultRules.length;
        const canDelete = !isDefault; // Can delete existing, new, and custom rules
        
        return `
            <div class="rule-item ${itemClass}">
                ${canDelete ? `<button class="rule-delete-btn" onclick="deleteRulesRule(${customIdx})" title="Delete rule"><i class="bi bi-trash"></i></button>` : ''}
                <span class="badge ${badgeClass} me-2">${badgeText}</span>
                <span class="rule-type-badge" style="background:${getRuleColor(rule.type)}">${rule.type.toUpperCase().replace('_', ' ')}</span>
                ${getRuleDescription(rule)}
            </div>
        `;
    }).join('');
}

function deleteRulesRule(idx) {
    if (idx >= 0 && idx < rulesCustomRules.length) {
        const deletedRule = rulesCustomRules[idx];
        rulesCustomRules.splice(idx, 1);
        renderRulesRulesList();
        
        // Show toast with rule type info
        const ruleType = deletedRule.isExisting ? 'existing' : (deletedRule.isNew ? 'new' : 'custom');
        showToast(`Deleted ${ruleType} rule`, 'info');
    }
}

async function previewRulesPayload() {
    showLoading(true);
    
    try {
        const allRules = [...rulesDefaultRules, ...rulesCustomRules];
        const apiType = document.getElementById('apiTypeSelect').value;
        // Task execution is set when saving rules, use 'parallel' for preview in Section 1
        const taskExecution = document.getElementById('rulesTaskExecutionSelect')?.value || 'parallel';
        
        // Read profile options for blueprints
        const profileOptions = {
            action_list: parseInt(document.getElementById('rulesProfileActionCount')?.value) || 0,
            snapshot_config_list: parseInt(document.getElementById('rulesSnapshotConfigCount')?.value) || 0,
            restore_config_list: parseInt(document.getElementById('rulesRestoreConfigCount')?.value) || 0,
            patch_list: parseInt(document.getElementById('rulesPatchListCount')?.value) || 0
        };
        
        const response = await fetch('/api/rules/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                original_payload: rulesOriginalPayload,
                entity_counts: rulesTempCounts,
                rules: allRules,
                api_type: apiType,
                task_execution: taskExecution,
                profile_options: profileOptions
            })
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.error);
        
        rulesPreviewData = data.preview_payload;
        document.getElementById('rulesPreviewPayload').textContent = data.formatted_payload;
        
        goToRulesStep(3);
        showLoading(false);
    } catch (e) {
        showLoading(false);
        showToast(e.message, 'error');
    }
}

async function acceptAndSaveRules() {
    const apiType = document.getElementById('apiTypeSelect').value;
    const taskExecution = document.getElementById('rulesTaskExecutionSelect')?.value || 'parallel';
    
    // If entity exists, show diff modal first
    if (rulesExistingEntity) {
        showEntityDiffModal();
        return;
    }
    
    await saveEntityRules();
}

async function saveEntityRules() {
    const apiType = document.getElementById('apiTypeSelect').value;
    const taskExecution = document.getElementById('rulesTaskExecutionSelect')?.value || 'parallel';
    
    showLoading(true);
    
    try {
        // Clean rules - remove isExisting, isNew flags before saving
        const cleanedRules = rulesCustomRules.map(rule => {
            const { isExisting, isNew, ...cleanRule } = rule;
            return cleanRule;
        });
        
        const response = await fetch('/api/rules/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_url: rulesEntityName,
                api_type: apiType,
                rules: cleanedRules,  // Merged rules (existing + new), not defaults
                payload_template: rulesOriginalPayload,
                scalable_entities: rulesEntities.map(e => e.path),
                task_execution: taskExecution,  // For runbooks: 'parallel' or 'series'
                save_history: !!rulesExistingEntity  // Save history if updating existing entity
            })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error);
        
        showLoading(false);
        
        const existingCount = rulesCustomRules.filter(r => r.isExisting).length;
        const newCount = rulesCustomRules.filter(r => r.isNew).length;
        
        if (rulesExistingEntity) {
            showToast(`Entity "${rulesEntityName}" updated! (${existingCount} existing + ${newCount} new rules)`);
        } else {
            showToast(`Entity "${rulesEntityName}" saved!`);
        }
        
        // Reload API list and go to welcome
        loadAllApis();
        showSection('welcome');
    } catch (e) {
        showLoading(false);
        showToast(e.message, 'error');
    }
}

function showEntityDiffModal() {
    // Count rules by type
    const existingCount = rulesCustomRules.filter(r => r.isExisting).length;
    const newCount = rulesCustomRules.filter(r => r.isNew).length;
    const deletedCount = (rulesExistingEntity.rules || []).length - existingCount;
    
    // Create the diff modal content
    const oldData = rulesExistingEntity;
    const newData = {
        rules: rulesCustomRules,
        scalable_entities: rulesEntities.map(e => e.path),
        payload_template: rulesOriginalPayload
    };
    
    const diffHtml = generateDiffHtml(oldData, newData);
    
    const modal = document.createElement('div');
    modal.className = 'diff-modal-overlay';
    modal.id = 'diffModal';
    modal.innerHTML = `
        <div class="diff-modal">
            <div class="diff-modal-header">
                <h4><i class="bi bi-git me-2"></i>Entity Already Exists: ${rulesEntityName}</h4>
                <button class="btn-close-modal" onclick="closeDiffModal()">&times;</button>
            </div>
            <div class="diff-modal-body">
                <div class="diff-info-box" style="background: rgba(16, 185, 129, 0.1); border-color: rgba(16, 185, 129, 0.3);">
                    <i class="bi bi-check-circle" style="color: var(--accent-green);"></i>
                    <span>Rules have been merged! Existing rules are preserved. You can delete any rule from the rules list.</span>
                </div>
                <div class="rules-merge-summary">
                    <div class="merge-stat">
                        <span class="merge-stat-value" style="color: #0dcaf0;">${existingCount}</span>
                        <span class="merge-stat-label">Existing Rules Kept</span>
                    </div>
                    <div class="merge-stat">
                        <span class="merge-stat-value" style="color: var(--accent-green);">${newCount}</span>
                        <span class="merge-stat-label">New Rules Added</span>
                    </div>
                    <div class="merge-stat">
                        <span class="merge-stat-value">${existingCount + newCount}</span>
                        <span class="merge-stat-label">Total Rules</span>
                    </div>
                </div>
                <div class="diff-container">
                    ${diffHtml}
                </div>
            </div>
            <div class="diff-modal-footer">
                <button class="btn btn-outline-secondary" onclick="closeDiffModal()">
                    <i class="bi bi-x me-2"></i>Cancel
                </button>
                <button class="btn btn-outline-primary" onclick="closeDiffModal(); goToRulesStep(2);">
                    <i class="bi bi-pencil me-2"></i>Edit Rules
                </button>
                <button class="btn btn-primary" onclick="viewEntityHistory()">
                    <i class="bi bi-clock-history me-2"></i>View History
                </button>
                <button class="btn btn-success" onclick="confirmSaveWithHistory()">
                    <i class="bi bi-check me-2"></i>Save & Update
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

function generateDiffHtml(oldData, newData) {
    let html = '';
    
    // Compare rules
    const oldRules = JSON.stringify(oldData.rules || [], null, 2);
    const newRules = JSON.stringify(newData.rules || [], null, 2);
    
    if (oldRules !== newRules) {
        html += `
            <div class="diff-section">
                <h6><i class="bi bi-sliders text-warning"></i> Rules Changed</h6>
                <div class="diff-comparison">
                    <div class="diff-old">
                        <span class="diff-label">Previous (${(oldData.rules || []).length} rules)</span>
                        <pre>${escapeHtml(oldRules)}</pre>
                    </div>
                    <div class="diff-arrow"><i class="bi bi-arrow-right"></i></div>
                    <div class="diff-new">
                        <span class="diff-label">New (${(newData.rules || []).length} rules)</span>
                        <pre>${escapeHtml(newRules)}</pre>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Compare scalable entities
    const oldEntities = (oldData.scalable_entities || []).sort();
    const newEntities = (newData.scalable_entities || []).sort();
    
    if (JSON.stringify(oldEntities) !== JSON.stringify(newEntities)) {
        const added = newEntities.filter(e => !oldEntities.includes(e));
        const removed = oldEntities.filter(e => !newEntities.includes(e));
        
        html += `
            <div class="diff-section">
                <h6><i class="bi bi-diagram-2 text-primary"></i> Scalable Entities Changed</h6>
                <div class="entity-changes">
                    ${added.length > 0 ? `<div class="added-entities"><span class="badge bg-success">+${added.length} Added</span> ${added.map(e => `<code>${e}</code>`).join(', ')}</div>` : ''}
                    ${removed.length > 0 ? `<div class="removed-entities"><span class="badge bg-danger">-${removed.length} Removed</span> ${removed.map(e => `<code>${e}</code>`).join(', ')}</div>` : ''}
                </div>
            </div>
        `;
    }
    
    // If no changes detected
    if (!html) {
        html = `
            <div class="diff-section">
                <div class="no-changes">
                    <i class="bi bi-check-circle text-success"></i>
                    <span>No significant changes detected. Payload template will be updated.</span>
                </div>
            </div>
        `;
    }
    
    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function closeDiffModal() {
    const modal = document.getElementById('diffModal');
    if (modal) modal.remove();
}

async function confirmSaveWithHistory() {
    closeDiffModal();
    showLoading(true);
    
    try {
        // Save with history (backend will handle versioning)
        const apiType = document.getElementById('apiTypeSelect').value;
        const taskExecution = document.getElementById('rulesTaskExecutionSelect')?.value || 'parallel';
        
        // Clean rules - remove isExisting, isNew flags before saving
        const cleanedRules = rulesCustomRules.map(rule => {
            const { isExisting, isNew, ...cleanRule } = rule;
            return cleanRule;
        });
        
        const response = await fetch('/api/rules/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_url: rulesEntityName,
                api_type: apiType,
                rules: cleanedRules,  // Merged rules (existing + new)
                payload_template: rulesOriginalPayload,
                scalable_entities: rulesEntities.map(e => e.path),
                task_execution: taskExecution,
                save_history: true  // Flag to save previous version to history
            })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error);
        
        showLoading(false);
        
        const existingCount = rulesCustomRules.filter(r => r.isExisting).length;
        const newCount = rulesCustomRules.filter(r => r.isNew).length;
        showToast(`Entity "${rulesEntityName}" updated! (${existingCount} existing + ${newCount} new rules). Previous version saved to history.`);
        
        loadAllApis();
        showSection('welcome');
    } catch (e) {
        showLoading(false);
        showToast(e.message, 'error');
    }
}

async function viewEntityHistory() {
    closeDiffModal();
    showHistoryModal(rulesEntityName);
}

async function showHistoryModal(entityName) {
    showLoading(true);
    
    try {
        const response = await fetch(`/api/rules/${encodeURIComponent(entityName)}/history`);
        const data = await response.json();
        
        showLoading(false);
        
        const historyItems = data.history || [];
        
        let historyHtml = '';
        if (historyItems.length === 0) {
            historyHtml = `
                <div class="history-empty">
                    <i class="bi bi-clock"></i>
                    <div>No history available</div>
                    <small>Changes will be recorded when you update this entity</small>
                </div>
            `;
        } else {
            historyHtml = `
                <div class="history-list">
                    ${historyItems.map((item, idx) => `
                        <div class="history-item">
                            <div class="history-item-info">
                                <div class="history-item-date">
                                    <i class="bi bi-clock-history me-2"></i>
                                    ${new Date(item.timestamp).toLocaleString()}
                                </div>
                                <div class="history-item-meta">
                                    <span><i class="bi bi-sliders"></i> ${item.rules_count} rules</span>
                                    <span><i class="bi bi-diagram-2"></i> ${item.entities_count} entities</span>
                                    ${item.version ? `<span>v${item.version}</span>` : ''}
                                </div>
                            </div>
                            <div class="history-item-actions">
                                <button class="btn btn-sm btn-outline-secondary" onclick="previewHistoryVersion('${entityName}', ${idx})">
                                    <i class="bi bi-eye"></i> Preview
                                </button>
                                <button class="btn btn-sm btn-primary" onclick="restoreHistoryVersion('${entityName}', ${idx})">
                                    <i class="bi bi-arrow-counterclockwise"></i> Restore
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        const modal = document.createElement('div');
        modal.className = 'diff-modal-overlay';
        modal.id = 'historyModal';
        modal.innerHTML = `
            <div class="history-modal">
                <div class="diff-modal-header">
                    <h4><i class="bi bi-clock-history me-2"></i>History: ${entityName}</h4>
                    <button class="btn-close-modal" onclick="closeHistoryModal()">&times;</button>
                </div>
                <div class="diff-modal-body">
                    ${historyHtml}
                </div>
                <div class="diff-modal-footer">
                    <button class="btn btn-outline-secondary" onclick="closeHistoryModal()">
                        <i class="bi bi-x me-2"></i>Close
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
    } catch (e) {
        showLoading(false);
        showToast('Failed to load history: ' + e.message, 'error');
    }
}

function closeHistoryModal() {
    const modal = document.getElementById('historyModal');
    if (modal) modal.remove();
}

async function previewHistoryVersion(entityName, versionIndex) {
    showLoading(true);
    
    try {
        const response = await fetch(`/api/rules/${encodeURIComponent(entityName)}/history/${versionIndex}`);
        const data = await response.json();
        
        showLoading(false);
        
        if (!response.ok) throw new Error(data.error);
        
        // Show preview in a simple modal
        const previewModal = document.createElement('div');
        previewModal.className = 'diff-modal-overlay';
        previewModal.id = 'previewModal';
        previewModal.innerHTML = `
            <div class="diff-modal">
                <div class="diff-modal-header">
                    <h4><i class="bi bi-eye me-2"></i>Version Preview</h4>
                    <button class="btn-close-modal" onclick="document.getElementById('previewModal').remove()">&times;</button>
                </div>
                <div class="diff-modal-body">
                    <pre style="font-size: 12px; font-family: 'JetBrains Mono', monospace; color: var(--text-primary); max-height: 400px; overflow: auto;">${JSON.stringify(data.version_data, null, 2)}</pre>
                </div>
                <div class="diff-modal-footer">
                    <button class="btn btn-outline-secondary" onclick="document.getElementById('previewModal').remove()">Close</button>
                </div>
            </div>
        `;
        document.body.appendChild(previewModal);
        
    } catch (e) {
        showLoading(false);
        showToast(e.message, 'error');
    }
}

async function restoreHistoryVersion(entityName, versionIndex) {
    if (!confirm('Restore this version? Current version will be saved to history.')) return;
    
    showLoading(true);
    
    try {
        const response = await fetch(`/api/rules/${encodeURIComponent(entityName)}/restore/${versionIndex}`, {
            method: 'POST'
        });
        const data = await response.json();
        
        showLoading(false);
        
        if (!response.ok) throw new Error(data.error);
        
        closeHistoryModal();
        showToast(`Version restored for "${entityName}"!`);
        loadAllApis();
        
    } catch (e) {
        showLoading(false);
        showToast(e.message, 'error');
    }
}

function copyPreviewPayload() {
    navigator.clipboard.writeText(document.getElementById('rulesPreviewPayload').textContent)
        .then(() => showToast('Copied!'))
        .catch(() => showToast('Failed to copy', 'error'));
}

function downloadPreviewPayload() {
    if (!rulesPreviewData) return;
    const blob = new Blob([JSON.stringify(rulesPreviewData, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'preview_payload.json';
    link.click();
}

// ============================================================================
// SECTION 2: CREATE ENTITIES
// ============================================================================

// ============================================================================
// APP SWITCHER & HIERARCHY BUILDER
// ============================================================================

let currentAppType = 'blueprint';
let selectedBlueprintEntity = null;
let selectedRunbookEntity = null;
let blueprintType = 'multi_vm';
let taskExecution = 'parallel';
let blueprintEntityCounts = {
    app_profile_list: 1,
    deployment_create_list: 1,
    service_definition_list: 1,
    substrate_definition_list: 1,  // Calculated: app_profiles × deployments
    package_definition_list: 1,    // Calculated: app_profiles × deployments
    credential_definition_list: 1
};
// App Profile optional features (0 = exclude from payload)
let blueprintProfileOptions = {
    action_list: 0,
    snapshot_config_list: 0,
    restore_config_list: 0,
    patch_list: 0
};
let runbookEntityCounts = {
    task_definition_list: 1,
    endpoint_definition_list: 1,
    credential_definition_list: 1
};

function switchAppType(type) {
    currentAppType = type;
    
    // Update tab buttons
    document.querySelectorAll('.app-switcher-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.type === type);
    });
    
    // Show/hide panels
    document.getElementById('blueprintConfigPanel').classList.toggle('section-hidden', type !== 'blueprint');
    document.getElementById('runbookConfigPanel').classList.toggle('section-hidden', type !== 'runbook');
    
    // Load appropriate entity list
    if (type === 'blueprint') {
        loadBlueprintEntityList();
    } else {
        loadRunbookEntityList();
    }
}

function loadBlueprintEntityList() {
    // Auto-select blueprint entity
    selectedBlueprintEntity = 'blueprint';
    document.getElementById('blueprintHierarchyBuilder').classList.remove('section-hidden');
    document.getElementById('selectedBlueprintName').textContent = 'blueprint';
    console.log('Auto-selected blueprint entity');
}

function loadRunbookEntityList() {
    // Auto-select runbook entity if available
    const runbooks = allApis.filter(api => api.api_type === 'runbook');
    if (runbooks.length > 0) {
        selectedRunbookEntity = runbooks[0].api_url;
        document.getElementById('runbookHierarchyBuilder').classList.remove('section-hidden');
        document.getElementById('selectedRunbookName').textContent = runbooks[0].api_url;
        console.log('Auto-selected runbook entity:', runbooks[0].api_url);
    }
}

// Modal functions for showing rules and entities
function showBlueprintRulesModal() {
    fetch('/api/rules')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const blueprint = data.apis.find(api => api.api_url === 'blueprint');
                if (blueprint) {
                    showRulesModal('Blueprint', blueprint);
                } else {
                    showToast('Blueprint configuration not found', 'error');
                }
            }
        })
        .catch(error => {
            console.error('Error loading blueprint rules:', error);
            showToast('Error loading blueprint rules', 'error');
        });
}

function showRunbookRulesModal() {
    fetch('/api/rules')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const runbooks = data.apis.filter(api => api.api_type === 'runbook');
                if (runbooks.length > 0) {
                    showRulesModal('Runbook', runbooks[0]);
                } else {
                    showToast('No runbook configurations found', 'error');
                }
            }
        })
        .catch(error => {
            console.error('Error loading runbook rules:', error);
            showToast('Error loading runbook rules', 'error');
        });
}

function showRulesModal(type, config) {
    const modal = document.createElement('div');
    modal.className = 'modal fade show';
    modal.style.display = 'block';
    modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content" style="background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border-color);">
                <div class="modal-header" style="border-bottom: 1px solid var(--border-color);">
                    <h5 class="modal-title">
                        <i class="bi bi-${type === 'Blueprint' ? 'diagram-3' : 'play-circle'}"></i>
                        ${type} Configuration: ${config.api_url}
                    </h5>
                    <button type="button" class="btn-close" onclick="closeRulesModal()" style="filter: invert(1);"></button>
            </div>
                <div class="modal-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h6><i class="bi bi-sliders"></i> Rules (${config.rules_count || 0})</h6>
                            <div class="rules-list" style="max-height: 300px; overflow-y: auto;">
                                ${config.rules_count > 0 ? 
                                    '<div class="alert alert-success"><i class="bi bi-check-circle"></i> Custom transformation rules configured</div>' :
                                    '<div class="alert alert-info"><i class="bi bi-info-circle"></i> Using default rules only</div>'
                                }
            </div>
        </div>
                        <div class="col-md-6">
                            <h6><i class="bi bi-diagram-2"></i> Scalable Entities (${config.scalable_entities_count || 0})</h6>
                            <div class="entities-list" style="max-height: 300px; overflow-y: auto;">
                                ${(config.scalable_entities || []).map(entity => 
                                    `<div class="entity-item" style="padding: 8px; margin: 4px 0; background: var(--bg-sidebar); border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 12px;">
                                        ${entity}
                                    </div>`
                                ).join('') || '<div class="alert alert-warning">No scalable entities found</div>'}
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer" style="border-top: 1px solid var(--border-color);">
                    <button type="button" class="btn btn-secondary" onclick="closeRulesModal()">Close</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

function closeRulesModal() {
    const modal = document.querySelector('.modal.show');
    if (modal) {
        modal.remove();
    }
}

async function selectBlueprintEntity(encodedUrl) {
    const apiUrl = decodeURIComponent(encodedUrl);
    selectedBlueprintEntity = apiUrl;
    
    // Show hierarchy builder
    document.getElementById('blueprintHierarchyBuilder').classList.remove('section-hidden');
    document.getElementById('selectedBlueprintName').textContent = apiUrl;
    
    // Mark card as selected
    document.querySelectorAll('#blueprintEntityList .entity-select-card').forEach(card => {
        card.classList.remove('selected');
    });
    if (event?.currentTarget) {
        event.currentTarget.classList.add('selected');
    }
    
    // Reset counts to defaults - NEW HIERARCHY
    blueprintEntityCounts = {
        app_profile_list: 1,
        deployment_create_list: 1,
        service_definition_list: 1,
        substrate_definition_list: 1,
        package_definition_list: 1,
        credential_definition_list: 1
    };
    
    // Reset profile options to defaults (0 = exclude)
    blueprintProfileOptions = {
        action_list: 0,
        snapshot_config_list: 0,
        restore_config_list: 0,
        patch_list: 0
    };
    
    // Reset UI inputs
    const appProfileInput = document.getElementById('appProfileCountInput');
    const deploymentInput = document.getElementById('deploymentCountInput');
    const serviceInput = document.getElementById('serviceCountInput');
    const credentialInput = document.querySelector('#blueprintHierarchyBuilder input[data-entity="credential_definition_list"]');
    
    if (appProfileInput) appProfileInput.value = 1;
    if (deploymentInput) deploymentInput.value = 1;
    if (serviceInput) serviceInput.value = 1;
    if (credentialInput) credentialInput.value = 1;
    
    // Reset profile option inputs
    const profileActionInput = document.getElementById('profileActionCount');
    const snapshotConfigInput = document.getElementById('snapshotConfigCount');
    const restoreConfigInput = document.getElementById('restoreConfigCount');
    const patchListInput = document.getElementById('patchListCount');
    
    if (profileActionInput) profileActionInput.value = 0;
    if (snapshotConfigInput) snapshotConfigInput.value = 0;
    if (restoreConfigInput) restoreConfigInput.value = 0;
    if (patchListInput) patchListInput.value = 0;
    
    // Reset blueprint type to multi_vm and enable all controls
    setBlueprintType('multi_vm');
    
    // Update calculated counts display
    updateCalculatedCounts();
}

async function selectRunbookEntity(encodedUrl) {
    const apiUrl = decodeURIComponent(encodedUrl);
    selectedRunbookEntity = apiUrl;
    
    // Show hierarchy builder
    document.getElementById('runbookHierarchyBuilder').classList.remove('section-hidden');
    document.getElementById('selectedRunbookName').textContent = apiUrl;
    
    // Mark card as selected
    document.querySelectorAll('#runbookEntityList .entity-select-card').forEach(card => {
        card.classList.remove('selected');
    });
    event.currentTarget.classList.add('selected');
}

function backToBlueprintSelection() {
    document.getElementById('blueprintHierarchyBuilder').classList.add('section-hidden');
    selectedBlueprintEntity = null;
    document.querySelectorAll('#blueprintEntityList .entity-select-card').forEach(card => {
        card.classList.remove('selected');
    });
}

function backToRunbookSelection() {
    document.getElementById('runbookHierarchyBuilder').classList.add('section-hidden');
    selectedRunbookEntity = null;
    document.querySelectorAll('#runbookEntityList .entity-select-card').forEach(card => {
        card.classList.remove('selected');
    });
}

function setBlueprintType(type) {
    blueprintType = type;
    document.querySelectorAll('#blueprintHierarchyBuilder .bp-type-btn[data-bptype]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.bptype === type);
    });
    
    const appProfileInput = document.getElementById('appProfileCountInput');
    const deploymentInput = document.getElementById('deploymentCountInput');
    const serviceInput = document.getElementById('serviceCountInput');
    
    const appProfileContainer = appProfileInput?.closest('.hierarchy-entity-input');
    const deploymentContainer = deploymentInput?.closest('.hierarchy-entity-input');
    const serviceContainer = serviceInput?.closest('.sub-entity-count');
    
    // If single_vm, set all to 1 and disable
    if (type === 'single_vm') {
        // Set all counts to 1
        blueprintEntityCounts.app_profile_list = 1;
        blueprintEntityCounts.deployment_create_list = 1;
        blueprintEntityCounts.service_definition_list = 1;
        
        // Update inputs
        if (appProfileInput) {
            appProfileInput.value = 1;
            appProfileInput.disabled = true;
        }
        if (deploymentInput) {
            deploymentInput.value = 1;
            deploymentInput.disabled = true;
        }
        if (serviceInput) {
            serviceInput.value = 1;
            serviceInput.disabled = true;
        }
        
        // Disable +/- buttons
        if (appProfileContainer) {
            appProfileContainer.querySelectorAll('.count-btn').forEach(btn => btn.disabled = true);
            appProfileContainer.classList.add('disabled-input');
        }
        if (deploymentContainer) {
            deploymentContainer.querySelectorAll('.count-btn').forEach(btn => btn.disabled = true);
            deploymentContainer.classList.add('disabled-input');
        }
        
        // Update calculated counts
        updateCalculatedCounts();
    } else {
        // Enable all inputs
        if (appProfileInput) appProfileInput.disabled = false;
        if (deploymentInput) deploymentInput.disabled = false;
        if (serviceInput) serviceInput.disabled = false;
        
        // Enable +/- buttons
        if (appProfileContainer) {
            appProfileContainer.querySelectorAll('.count-btn').forEach(btn => btn.disabled = false);
            appProfileContainer.classList.remove('disabled-input');
        }
        if (deploymentContainer) {
            deploymentContainer.querySelectorAll('.count-btn').forEach(btn => btn.disabled = false);
            deploymentContainer.classList.remove('disabled-input');
        }
    }
}

function setTaskExecution(type) {
    taskExecution = type;
    document.querySelectorAll('.bp-type-btn[data-exectype]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.exectype === type);
    });
}

// ===== SECTION 2: App Profile & Deployment Count Functions =====
function adjustAppProfileCount(delta) {
    const input = document.getElementById('appProfileCountInput');
    let value = parseInt(input.value) || 1;
    value = Math.max(1, Math.min(10, value + delta));
    input.value = value;
    onAppProfileCountChange(value);
}

function onAppProfileCountChange(value) {
    const count = parseInt(value) || 1;
    blueprintEntityCounts.app_profile_list = count;
    updateCalculatedCounts();
}

function adjustDeploymentCount(delta) {
    const input = document.getElementById('deploymentCountInput');
    let value = parseInt(input.value) || 1;
    value = Math.max(1, Math.min(50, value + delta));
    input.value = value;
    onDeploymentCountChange(value);
}

function onDeploymentCountChange(value) {
    const count = parseInt(value) || 1;
    blueprintEntityCounts.deployment_create_list = count;
    updateCalculatedCounts();
}

function updateCalculatedCounts() {
    const appProfiles = parseInt(document.getElementById('appProfileCountInput')?.value) || 1;
    const deploymentsPerProfile = parseInt(document.getElementById('deploymentCountInput')?.value) || 1;
    const totalDeployments = appProfiles * deploymentsPerProfile;
    
    // Update UI badges to show calculated values (for display only)
    // NOTE: Do NOT store these in blueprintEntityCounts - let backend calculate them
    const substrateCalc = document.querySelector('#substrateCalc span');
    const packageCalc = document.querySelector('#packageCalc span');
    if (substrateCalc) substrateCalc.textContent = totalDeployments;
    if (packageCalc) packageCalc.textContent = totalDeployments;
}

// Legacy function for backward compatibility
function adjustServiceCount(delta) {
    const input = document.getElementById('serviceCountInput');
    if (!input) return;
    let value = parseInt(input.value) || 1;
    value = Math.max(1, Math.min(100, value + delta));
    input.value = value;
    onServiceCountChange(value);
}

function onServiceCountChange(value) {
    const count = parseInt(value) || 1;
    blueprintEntityCounts.service_definition_list = count;
}

function updateSubEntityCount(entity, value) {
    blueprintEntityCounts[entity] = parseInt(value) || 0;
}

function updateRunbookEntityCount(entity, value) {
    runbookEntityCounts[entity] = parseInt(value) || 0;
}

// App Profile Options handlers (Section 2)
function updateProfileOption(option, value) {
    blueprintProfileOptions[option] = parseInt(value) || 0;
}

// App Profile Options handlers (Section 1 - Rules)
function updateRulesProfileOption(option, value) {
    rulesProfileOptions[option] = parseInt(value) || 0;
}

async function generateBlueprintPayload() {
    if (!selectedBlueprintEntity) {
        showToast('Please select a blueprint entity first', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        // Read counts from input fields - NEW HIERARCHY
        const appProfileCount = parseInt(document.getElementById('appProfileCountInput')?.value) || 1;
        const deploymentsPerProfile = parseInt(document.getElementById('deploymentCountInput')?.value) || 1;
        const serviceCount = parseInt(document.getElementById('serviceCountInput')?.value) || 1;
        const credentialCount = parseInt(document.querySelector('#blueprintHierarchyBuilder input[data-entity="credential_definition_list"]')?.value) || 1;
        
        // Read profile options
        const profileActionCount = parseInt(document.getElementById('profileActionCount')?.value) || 0;
        const snapshotConfigCount = parseInt(document.getElementById('snapshotConfigCount')?.value) || 0;
        const restoreConfigCount = parseInt(document.getElementById('restoreConfigCount')?.value) || 0;
        const patchListCount = parseInt(document.getElementById('patchListCount')?.value) || 0;
        
        // Read nested entity counts
        const serviceActionCount = parseInt(document.getElementById('serviceActionCount')?.value) || 0;
        const serviceActionTaskCount = parseInt(document.getElementById('serviceActionTaskCount')?.value) || 1;
        const serviceActionVariableCount = parseInt(document.getElementById('serviceActionVariableCount')?.value) || 0;
        
        const substrateActionCount = parseInt(document.getElementById('substrateActionCount')?.value) || 0;
        const substrateActionTaskCount = parseInt(document.getElementById('substrateActionTaskCount')?.value) || 1;
        const substrateActionVariableCount = parseInt(document.getElementById('substrateActionVariableCount')?.value) || 0;
        
        const packageInstallTaskCount = parseInt(document.getElementById('packageInstallTaskCount')?.value) || 1;
        const packageInstallVariableCount = parseInt(document.getElementById('packageInstallVariableCount')?.value) || 0;
        const packageUninstallTaskCount = parseInt(document.getElementById('packageUninstallTaskCount')?.value) || 1;
        const packageUninstallVariableCount = parseInt(document.getElementById('packageUninstallVariableCount')?.value) || 0;
        
        // Read guest customization toggle
        const includeGuestCustomization = document.getElementById('guestCustomizationToggle')?.checked || false;
        
        // Calculate total deployments (substrates & packages)
        const totalDeployments = appProfileCount * deploymentsPerProfile;
        
        // Build entity counts for the API
        // NOTE: substrate_definition_list and package_definition_list are calculated by backend hardcoded rules
        // Do NOT send them in the payload to allow proper backend calculation
        const entityCounts = {
            'spec.resources.app_profile_list': appProfileCount,
            'spec.resources.app_profile_list.deployment_create_list': deploymentsPerProfile,
            'spec.resources.service_definition_list': serviceCount,
            'spec.resources.credential_definition_list': credentialCount
        };
        
        // Add nested entity counts if they are > 0
        if (serviceActionCount > 0) {
            entityCounts['spec.resources.service_definition_list.action_list'] = serviceActionCount;
            entityCounts['spec.resources.service_definition_list.action_list.runbook.task_definition_list'] = serviceActionTaskCount;
            if (serviceActionVariableCount > 0) {
                entityCounts['spec.resources.service_definition_list.action_list.runbook.variable_list'] = serviceActionVariableCount;
            }
        }
        
        if (substrateActionCount > 0) {
            entityCounts['spec.resources.substrate_definition_list.action_list'] = substrateActionCount;
            entityCounts['spec.resources.substrate_definition_list.action_list.runbook.task_definition_list'] = substrateActionTaskCount;
            if (substrateActionVariableCount > 0) {
                entityCounts['spec.resources.substrate_definition_list.action_list.runbook.variable_list'] = substrateActionVariableCount;
            }
        }
        
        // Package runbook counts - use relative paths that will be matched when scaling within each package
        entityCounts['options.install_runbook.task_definition_list'] = packageInstallTaskCount;
        if (packageInstallVariableCount > 0) {
            entityCounts['options.install_runbook.variable_list'] = packageInstallVariableCount;
        }
        entityCounts['options.uninstall_runbook.task_definition_list'] = packageUninstallTaskCount;
        if (packageUninstallVariableCount > 0) {
            entityCounts['options.uninstall_runbook.variable_list'] = packageUninstallVariableCount;
        }
        
        // Build profile options
        const profileOptions = {
            action_list: profileActionCount,
            snapshot_config_list: snapshotConfigCount,
            restore_config_list: restoreConfigCount,
            patch_list: patchListCount
        };
        
        // Get live UUIDs if available
        const liveUUIDs = getSelectedLiveUUIDs();
        const hasLiveData = liveUUIDs.project.uuid || liveUUIDs.account.uuid || liveUUIDs.cluster.uuid;
        
        console.log('Generating blueprint with counts:', entityCounts);
        console.log('Profile options:', profileOptions);
        console.log('Live UUIDs:', liveUUIDs);
        console.log(`App Profiles: ${appProfileCount}, Deployments/Profile: ${deploymentsPerProfile}, Total Substrates/Packages: ${totalDeployments}`);
        
        // Get blueprint name from input field
        const blueprintNameInput = document.getElementById('blueprintNameInput');
        const blueprintName = blueprintNameInput ? blueprintNameInput.value.trim() : '';
        
        const requestBody = {
            api_url: selectedBlueprintEntity,
            entity_counts: entityCounts,
            blueprint_type: blueprintType,
            profile_options: profileOptions,
            include_guest_customization: includeGuestCustomization
        };
        
        // Add blueprint name if provided
        if (blueprintName) {
            requestBody.blueprint_name = blueprintName;
        }
        
        // Add live UUIDs if available
        if (hasLiveData) {
            requestBody.live_uuids = liveUUIDs;
        }
        
        const response = await fetch('/api/payload/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        console.log('Generate response:', data);
        
        if (!response.ok) throw new Error(data.error || 'Failed to generate payload');
        
        // Show result - backend returns scaled_payload
        const payload = data.scaled_payload || data.payload;
        const payloadText = JSON.stringify(payload, null, 2);
        document.getElementById('entityGeneratedPayload').textContent = payloadText;
        document.getElementById('entityResult').classList.remove('section-hidden');
        entityGeneratedData = payload;
        
        // Scroll to result
        document.getElementById('entityResult').scrollIntoView({ behavior: 'smooth' });
        
        showLoading(false);
        showToast('Blueprint payload generated!');
    } catch (e) {
        showLoading(false);
        console.error('Generate error:', e);
        showToast(e.message, 'error');
    }
}

async function generateRunbookPayload() {
    if (!selectedRunbookEntity) {
        showToast('Please select a runbook entity first', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        // Read counts from input fields
        const taskCount = parseInt(document.querySelector('#runbookHierarchyBuilder input[data-entity="task_definition_list"]')?.value) || 1;
        const endpointCount = parseInt(document.querySelector('#runbookHierarchyBuilder input[data-entity="endpoint_definition_list"]')?.value) || 1;
        const credentialCount = parseInt(document.querySelector('#runbookHierarchyBuilder input[data-entity="credential_definition_list"]')?.value) || 1;
        
        const entityCounts = {
            'spec.resources.runbook.task_definition_list': taskCount,
            'spec.resources.endpoint_definition_list': endpointCount,
            'spec.resources.credential_definition_list': credentialCount
        };
        
        // Get live UUIDs if available
        const liveUUIDs = getSelectedRunbookLiveUUIDs();
        const hasLiveData = liveUUIDs.project.uuid || liveUUIDs.account.uuid || liveUUIDs.cluster.uuid;
        
        console.log('Generating runbook with counts:', entityCounts);
        console.log('Live UUIDs:', liveUUIDs);
        
        const requestBody = {
            api_url: selectedRunbookEntity,
            entity_counts: entityCounts,
            task_execution: taskExecution
        };
        
        // Add live UUIDs if available
        if (hasLiveData) {
            requestBody.live_uuids = liveUUIDs;
        }
        
        const response = await fetch('/api/payload/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        console.log('Generate response:', data);
        
        if (!response.ok) throw new Error(data.error || 'Failed to generate payload');
        
        // Show result - backend returns scaled_payload
        const payload = data.scaled_payload || data.payload;
        const payloadText = JSON.stringify(payload, null, 2);
        document.getElementById('entityGeneratedPayload').textContent = payloadText;
        document.getElementById('entityResult').classList.remove('section-hidden');
        entityGeneratedData = payload;
        
        // Scroll to result
        document.getElementById('entityResult').scrollIntoView({ behavior: 'smooth' });
        
        showLoading(false);
        showToast('Runbook payload generated!');
    } catch (e) {
        showLoading(false);
        console.error('Generate error:', e);
        showToast(e.message, 'error');
    }
}

// ============================================================================
// LEGACY ENTITY API LIST (kept for compatibility)
// ============================================================================

function loadEntityApiList() {
    const container = document.getElementById('entityApiList');
    
    if (allApis.length === 0) {
        container.innerHTML = `
            <div class="no-apis">
                <i class="bi bi-inbox"></i>
                <div>No saved entities</div>
                <small>Go to "Generate New Payload Rules" to create rules first</small>
            </div>
        `;
        return;
    }
    
    container.innerHTML = allApis.map(api => `
        <div class="api-item" onclick="selectApiForEntities('${encodeURIComponent(api.api_url)}')">
            <div class="api-name">${api.api_url}</div>
            <div class="api-meta">
                <span><i class="bi bi-tag"></i> ${api.api_type}</span>
                ${api.api_type === 'runbook' ? `<span><i class="bi bi-diagram-3"></i> ${api.task_execution || 'parallel'}</span>` : ''}
                <span><i class="bi bi-sliders"></i> ${api.rules_count} rules</span>
                <span><i class="bi bi-diagram-2"></i> ${api.scalable_entities_count} entities</span>
            </div>
        </div>
    `).join('');
    
    // Reset view
    document.getElementById('entityApiSelection').classList.remove('section-hidden');
    document.getElementById('entityConfiguration').classList.add('section-hidden');
    document.getElementById('entityResult').classList.add('section-hidden');
}

let entitySelectedApiType = 'blueprint';
let entityTaskExecution = 'parallel';
let entityBlueprintType = 'multi_vm';  // 'single_vm' or 'multi_vm'

async function selectApiForEntities(encodedUrl) {
    const apiUrl = decodeURIComponent(encodedUrl);
    
    // First, switch to the Create Entities section
    switchSection('createEntities');
    
    // Determine entity type by checking allApis
    const entityInfo = allApis.find(api => api.api_url === apiUrl);
    const entityType = entityInfo?.api_type || 'blueprint';
    
    // Switch to the correct app type tab
    switchAppType(entityType);
    
    // Wait a tick for DOM to update, then select the entity
    setTimeout(() => {
        if (entityType === 'blueprint') {
            selectedBlueprintEntity = apiUrl;
            document.getElementById('blueprintHierarchyBuilder').classList.remove('section-hidden');
            document.getElementById('selectedBlueprintName').textContent = apiUrl;
            
            // Mark card as selected in the list
            document.querySelectorAll('#blueprintEntityList .entity-select-card').forEach(card => {
                card.classList.toggle('selected', card.textContent.includes(apiUrl));
            });
            
            // Reset counts to defaults
            if (document.getElementById('serviceCountInput')) {
                document.getElementById('serviceCountInput').value = 1;
            }
        } else {
            selectedRunbookEntity = apiUrl;
            document.getElementById('runbookHierarchyBuilder').classList.remove('section-hidden');
            document.getElementById('selectedRunbookName').textContent = apiUrl;
            
            // Mark card as selected in the list
            document.querySelectorAll('#runbookEntityList .entity-select-card').forEach(card => {
                card.classList.toggle('selected', card.textContent.includes(apiUrl));
            });
        }
        
        // Scroll to the hierarchy builder
        const builder = document.getElementById(entityType === 'blueprint' ? 'blueprintHierarchyBuilder' : 'runbookHierarchyBuilder');
        if (builder) {
            builder.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, 100);
}

function backToApiSelection() {
    document.getElementById('entityApiSelection').classList.remove('section-hidden');
    document.getElementById('entityConfiguration').classList.add('section-hidden');
    document.getElementById('entityResult').classList.add('section-hidden');
    entitySelectedApi = null;
}

function updateEntityTaskExecution() {
    const select = document.getElementById('entityTaskExecutionSelect');
    if (select) {
        entityTaskExecution = select.value;
    }
}

function updateEntityBlueprintType() {
    const select = document.getElementById('entityBlueprintTypeSelect');
    if (select) {
        entityBlueprintType = select.value;
        
        // For single_vm, force service count to 1
        const servicePath = 'spec.resources.service_definition_list';
        if (entityBlueprintType === 'single_vm') {
            entityCounts[servicePath] = 1;
        }
        
        // Re-render the entity tree to reflect the new state (disabled/enabled inputs)
        renderEntityEntities();
    }
}

function renderEntityEntities() {
    const activeEntities = entityEntities.filter(e => entityCounts[e.path] > 0);
    const tree = buildEntityTree(activeEntities);
    const container = document.getElementById('entityEntitiesTree');
    
    let html = '';
    Object.values(tree.children).forEach(node => {
        html += renderTreeNode(node, 0, 'entity');
    });
    container.innerHTML = html || '<p style="color: var(--text-secondary)">No active entities</p>';
    
    // Update entity count badge
    document.getElementById('entityEntitiesBadge').textContent = activeEntities.length;
    
    renderEntityExcluded();
}

function renderEntityExcluded() {
    const excluded = entityEntities.filter(e => entityCounts[e.path] === 0);
    const section = document.getElementById('entityExcludedSection');
    const list = document.getElementById('entityExcludedList');
    const badge = document.getElementById('entityExcludedBadge');
    
    if (excluded.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    badge.textContent = excluded.length;
    
    list.innerHTML = excluded.map(e => `
        <div class="excluded-item">
            <span class="excluded-path">${e.path}</span>
            <button class="restore-btn" onclick="restoreEntityEntity('${e.path}')">
                <i class="bi bi-plus-circle me-1"></i> Restore
            </button>
        </div>
    `).join('');
}

function updateEntityCount(path, value) {
    entityCounts[path] = parseInt(value) || 0;
    if (entityCounts[path] === 0) {
        updateEntityVisibility(path, false);
    }
    // Update the badge count display
    const nodeId = `entity_${path.replace(/\./g, '_')}`;
    const badge = document.querySelector(`#toggle_${nodeId}`)?.closest('.tree-node-header')?.querySelector('.entity-count-badge');
    if (badge) {
        badge.textContent = `${entityCounts[path]} items`;
    }
}

function updateEntityVisibility(path, visible) {
    const nodeId = `entity_${path.replace(/\./g, '_')}`;
    const node = document.getElementById(`toggle_${nodeId}`)?.closest('.tree-node');
    
    if (!visible && node) {
        node.style.display = 'none';
    } else if (visible && node) {
        node.style.display = 'block';
    }
    
    renderEntityExcluded();
}

function excludeEntityEntity(path) {
    entityCounts[path] = 0;
    updateEntityVisibility(path, false);
}

function restoreEntityEntity(path) {
    entityCounts[path] = 1;
    const nodeId = `entity_${path.replace(/\./g, '_')}`;
    const node = document.getElementById(`toggle_${nodeId}`)?.closest('.tree-node');
    
    if (node) {
        node.style.display = 'block';
        renderEntityExcluded();
    } else {
        renderEntityEntities();
    }
}

async function generateEntityPayload() {
    if (!entitySelectedApi) {
        showToast('No API selected', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch('/api/payload/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_url: entitySelectedApi,
                entity_counts: entityCounts,
                task_execution: entityTaskExecution,  // For runbooks
                blueprint_type: entityBlueprintType   // For blueprints: 'single_vm' or 'multi_vm'
            })
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.error);
        
        entityGeneratedData = data.scaled_payload;
        document.getElementById('entityGeneratedPayload').textContent = data.formatted_payload;
        document.getElementById('entityResult').classList.remove('section-hidden');
        
        showLoading(false);
    } catch (e) {
        showLoading(false);
        showToast(e.message, 'error');
    }
}

function copyEntityPayload() {
    navigator.clipboard.writeText(document.getElementById('entityGeneratedPayload').textContent)
        .then(() => showToast('Copied!'))
        .catch(() => showToast('Failed to copy', 'error'));
}

function downloadEntityPayload() {
    if (!entityGeneratedData) return;
    const blob = new Blob([JSON.stringify(entityGeneratedData, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'generated_payload.json';
    link.click();
}

// ============================================================================
// SHARED UI COMPONENTS
// ============================================================================

function buildEntityTree(entitiesList) {
    const tree = { children: {} };
    entitiesList.sort((a, b) => a.path.split('.').length - b.path.split('.').length);
    
    entitiesList.forEach(entity => {
        const parts = entity.path.split('.');
        let current = tree;
        let currentPath = '';
        
        parts.forEach((part, idx) => {
            currentPath = currentPath ? `${currentPath}.${part}` : part;
            if (!current.children[part]) {
                current.children[part] = { name: part, path: currentPath, children: {}, entity: null };
            }
            if (idx === parts.length - 1) {
                current.children[part].entity = entity;
            }
            current = current.children[part];
        });
    });
    return tree;
}

// Auto-linked entities that scale with service count (hidden from main UI)
const AUTO_LINKED_ENTITY_NAMES = [
    'substrate_definition_list',
    'package_definition_list',
    'deployment_create_list',
    'credential_definition_list',
    'app_profile_list'
];

// Check if entity is auto-linked to service count (scales automatically)
function isAutoLinkedToService(path) {
    // Auto-linked entities that scale with service_definition_list
    const autoLinkedPaths = [
        'spec.resources.substrate_definition_list',
        'spec.resources.package_definition_list',
        'spec.resources.app_profile_list.deployment_create_list'
    ];
    
    return autoLinkedPaths.includes(path);
}

// For backward compatibility
function shouldHideEntity(path) {
    return isAutoLinkedToService(path);
}

function renderTreeNode(node, level, prefix) {
    const hasChildren = Object.keys(node.children).length > 0;
    const entity = node.entity;
    const nodeId = `${prefix}_${node.path.replace(/\./g, '_')}`;
    
    // Check if this entity is auto-linked (scales with service count)
    const isAutoLinkedEntity = entity && shouldHideEntity(entity.path);
    
    // Get count based on which section we're in
    let count = 0;
    if (prefix === 'rules' && entity) {
        count = rulesTempCounts[entity.path] || 0;
        // For auto-linked entities, use service count
        if (isAutoLinkedEntity) {
            count = rulesTempCounts['spec.resources.service_definition_list'] || 1;
        }
    } else if (prefix === 'entity' && entity) {
        count = entityCounts[entity.path] || 0;
        // For auto-linked entities, use service count
        if (isAutoLinkedEntity) {
            count = entityCounts['spec.resources.service_definition_list'] || 1;
        }
    }
    
    let html = `<div class="tree-node" data-level="${level}">`;
    html += `<div class="tree-node-header" onclick="toggleTreeNode('${nodeId}')">`;
    html += `<span class="tree-toggle" id="toggle_${nodeId}"><i class="bi bi-chevron-right"></i></span>`;
    html += `<span class="entity-name">${node.name}</span>`;
    if (entity) {
        html += `<span class="entity-count-badge">${count} items</span>`;
        const excludeFn = prefix === 'rules' ? 'excludeRulesEntity' : 'excludeEntityEntity';
        html += `<button class="btn btn-outline-danger btn-sm exclude-btn" onclick="event.stopPropagation(); ${excludeFn}('${entity.path}')" title="Exclude this entity">
            <i class="bi bi-eye-slash"></i>
        </button>`;
    }
    html += `</div>`;
    
    if (entity) {
        const updateFn = prefix === 'rules' ? 'updateRulesTempCount' : 'updateEntityCount';
        
        html += `<div class="entity-details" id="details_${nodeId}" style="display:none;">`;
        
        if (isAutoLinkedEntity) {
            // Show linked badge instead of input for auto-linked entities
            html += `<div class="d-flex align-items-center gap-3">
                <span class="badge bg-info" style="font-size: 12px;">
                    <i class="bi bi-link-45deg"></i> Linked to service_definition_list count
                </span>
                <span style="color: var(--text-secondary); font-size: 13px;">
                    (Will scale to ${count} automatically)
                </span>
            </div>`;
        } else {
            // Check if this is service_definition_list in single_vm mode (should be disabled)
            const isServiceEntity = entity.path === 'spec.resources.service_definition_list';
            const isSingleVmMode = prefix === 'entity' && entityBlueprintType === 'single_vm';
            const isDisabled = isServiceEntity && isSingleVmMode;
            
            // Normal editable input (disabled for service count in single_vm mode)
            html += `<div class="d-flex align-items-center gap-3">
                <label class="mb-0" style="color: var(--text-secondary); font-size: 13px;">Count:</label>
                <input type="number" class="form-control" style="width:100px" value="${isDisabled ? 1 : count}" min="0" 
                       ${isDisabled ? 'disabled title="Single VM mode allows only 1 service"' : ''}
                       onchange="${updateFn}('${entity.path}', this.value)">
                ${isDisabled ? '<span class="badge bg-secondary ms-2">Single VM</span>' : ''}
            </div>`;
        }
        html += `</div>`;
    }
    
    if (hasChildren) {
        html += `<div class="tree-children" id="children_${nodeId}">`;
        Object.values(node.children).forEach(child => {
            html += renderTreeNode(child, level + 1, prefix);
        });
        html += `</div>`;
    }
    
    html += `</div>`;
    return html;
}

function toggleTreeNode(nodeId) {
    const toggle = document.getElementById(`toggle_${nodeId}`);
    const details = document.getElementById(`details_${nodeId}`);
    const children = document.getElementById(`children_${nodeId}`);
    const header = toggle.closest('.tree-node-header');
    
    const isExpanded = toggle.classList.contains('expanded');
    
    if (isExpanded) {
        toggle.classList.remove('expanded');
        header.classList.remove('expanded');
        if (details) details.style.display = 'none';
        if (children) children.classList.remove('show');
    } else {
        toggle.classList.add('expanded');
        header.classList.add('expanded');
        if (details) details.style.display = 'block';
        if (children) children.classList.add('show');
    }
}

function getRuleColor(type) {
    const colors = {
        'use_single': '#0ea5e9', 'reference_mapping': '#8b5cf6', 'filter': '#10b981',
        'clone': '#f59e0b', 'keep_first': '#14b8a6', 'set_value': '#ec4899', 'remove_field': '#ef4444'
    };
    return colors[type] || '#6b7280';
}

function getRuleDescription(rule) {
    switch (rule.type) {
        case 'use_single': return `Use only first item from: <code>${rule.source_entity}</code>`;
        case 'reference_mapping': return `<code>${rule.source_path}</code> → <code>${rule.target_path}</code>`;
        case 'filter': return `Filter <code>${rule.target_path}</code> by <code>${rule.filter_field}</code>`;
        case 'clone': return `Clone <code>${rule.source_value}</code> in <code>${rule.target_path}</code>`;
        case 'keep_first': return `Keep first ${rule.keep_count} in <code>${rule.target_path}</code>`;
        case 'set_value': return `Set <code>${rule.target_path}</code> = "${rule.new_value}"`;
        case 'remove_field': return `Remove <code>${rule.field_to_remove}</code> from <code>${rule.target_path}</code>`;
        default: return JSON.stringify(rule);
    }
}

// ============================================================================
// RULE FORM
// ============================================================================

function showAddRuleForm(prefix) {
    const form = document.getElementById(`${prefix}AddRuleForm`);
    form.style.display = 'block';
    form.innerHTML = `
        <div class="card-dark" style="margin: 0; background: rgba(0,0,0,0.2);">
            <h6 style="color: var(--text-primary); margin-bottom: 16px;"><i class="bi bi-plus-circle me-2"></i>Add New Rule</h6>
            <div class="row g-3">
                <div class="col-md-3">
                    <label class="form-label">Rule Type</label>
                    <select class="form-select" id="${prefix}RuleTypeSelect" onchange="updateRuleFormFields('${prefix}')">
                        <option value="filter">Filter</option>
                        <option value="clone">Clone</option>
                        <option value="use_single">Use Single</option>
                        <option value="reference_mapping">Reference Mapping</option>
                        <option value="keep_first">Keep First N</option>
                        <option value="set_value">Set Value</option>
                        <option value="remove_field">Remove Field</option>
                    </select>
                </div>
                <div class="col-md-9" id="${prefix}RuleFormFields"></div>
            </div>
            <div class="mt-3 d-flex gap-2">
                <button class="btn btn-success btn-sm" onclick="addRule('${prefix}')">
                    <i class="bi bi-check me-1"></i> Add Rule
                </button>
                <button class="btn btn-outline-secondary btn-sm" onclick="hideAddRuleForm('${prefix}')">Cancel</button>
            </div>
        </div>
    `;
    updateRuleFormFields(prefix);
}

function hideAddRuleForm(prefix) {
    document.getElementById(`${prefix}AddRuleForm`).style.display = 'none';
}

function updateRuleFormFields(prefix) {
    const type = document.getElementById(`${prefix}RuleTypeSelect`).value;
    const container = document.getElementById(`${prefix}RuleFormFields`);
    
    const fields = {
        filter: `
            <label class="form-label">Target Path</label>
            <input class="form-control mb-2" id="${prefix}_rf_target" placeholder="e.g., spec.resources.service_definition_list.action_list">
            <div class="row">
                <div class="col-md-4">
                    <label class="form-label">Filter Field</label>
                    <input class="form-control" id="${prefix}_rf_field" placeholder="name" value="name">
                </div>
                <div class="col-md-8">
                    <label class="form-label">Allowed Values (comma-separated)</label>
                    <input class="form-control" id="${prefix}_rf_values" placeholder="action_create, action_delete">
                </div>
            </div>`,
        clone: `
            <label class="form-label">Target Path</label>
            <input class="form-control mb-2" id="${prefix}_rf_target" placeholder="e.g., spec.resources.service_definition_list.action_list">
            <div class="row">
                <div class="col-md-3">
                    <label class="form-label">Source Field</label>
                    <input class="form-control" id="${prefix}_rf_srcfield" placeholder="name" value="name">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Source Value</label>
                    <input class="form-control" id="${prefix}_rf_srcvalue" placeholder="Value to clone">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Clone Values (comma-separated)</label>
                    <input class="form-control" id="${prefix}_rf_clonevalues" placeholder="new_action1, new_action2">
                </div>
            </div>`,
        use_single: `
            <label class="form-label">Source Entity Path</label>
            <input class="form-control" id="${prefix}_rf_source" placeholder="e.g., spec.resources.app_profile_list">`,
        reference_mapping: `
            <div class="row">
                <div class="col-md-5">
                    <label class="form-label">Source Path</label>
                    <input class="form-control" id="${prefix}_rf_srcpath" placeholder="e.g., substrate_definition_list.uuid">
                </div>
                <div class="col-md-5">
                    <label class="form-label">Target Path</label>
                    <input class="form-control" id="${prefix}_rf_tgtpath" placeholder="e.g., deployment_create_list.substrate_local_reference.uuid">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Type</label>
                    <select class="form-select" id="${prefix}_rf_maptype">
                        <option value="first_only">First Only</option>
                        <option value="one_to_one">One to One</option>
                        <option value="round_robin">Round Robin</option>
                    </select>
                </div>
            </div>`,
        keep_first: `
            <div class="row">
                <div class="col-md-8">
                    <label class="form-label">Target Path</label>
                    <input class="form-control" id="${prefix}_rf_target" placeholder="e.g., spec.resources.service_definition_list">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Keep Count</label>
                    <input class="form-control" id="${prefix}_rf_count" type="number" value="1" min="1">
                </div>
            </div>`,
        set_value: `
            <div class="row">
                <div class="col-md-6">
                    <label class="form-label">Target Path</label>
                    <input class="form-control" id="${prefix}_rf_target" placeholder="e.g., spec.name">
                </div>
                <div class="col-md-6">
                    <label class="form-label">New Value</label>
                    <input class="form-control" id="${prefix}_rf_newvalue" placeholder="New value to set">
                </div>
            </div>`,
        remove_field: `
            <div class="row">
                <div class="col-md-6">
                    <label class="form-label">Target Path</label>
                    <input class="form-control" id="${prefix}_rf_target" placeholder="e.g., spec.resources.service_definition_list">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Field to Remove</label>
                    <input class="form-control" id="${prefix}_rf_fieldname" placeholder="Field name to remove">
                </div>
            </div>`
    };
    
    container.innerHTML = fields[type] || '';
}

function addRule(prefix) {
    const type = document.getElementById(`${prefix}RuleTypeSelect`).value;
    let rule = { type };
    
    try {
        switch (type) {
            case 'filter':
                rule.target_path = document.getElementById(`${prefix}_rf_target`).value;
                rule.filter_field = document.getElementById(`${prefix}_rf_field`).value || 'name';
                rule.allowed_values = document.getElementById(`${prefix}_rf_values`).value.split(',').map(v => v.trim()).filter(v => v);
                break;
            case 'clone':
                rule.target_path = document.getElementById(`${prefix}_rf_target`).value;
                rule.source_field = document.getElementById(`${prefix}_rf_srcfield`).value || 'name';
                rule.source_value = document.getElementById(`${prefix}_rf_srcvalue`).value;
                rule.clone_values = document.getElementById(`${prefix}_rf_clonevalues`).value.split(',').map(v => v.trim()).filter(v => v);
                break;
            case 'use_single':
                rule.source_entity = document.getElementById(`${prefix}_rf_source`).value;
                break;
            case 'reference_mapping':
                rule.source_path = document.getElementById(`${prefix}_rf_srcpath`).value;
                rule.target_path = document.getElementById(`${prefix}_rf_tgtpath`).value;
                rule.mapping_type = document.getElementById(`${prefix}_rf_maptype`).value;
                break;
            case 'keep_first':
                rule.target_path = document.getElementById(`${prefix}_rf_target`).value;
                rule.keep_count = parseInt(document.getElementById(`${prefix}_rf_count`).value) || 1;
                break;
            case 'set_value':
                rule.target_path = document.getElementById(`${prefix}_rf_target`).value;
                rule.new_value = document.getElementById(`${prefix}_rf_newvalue`).value;
                break;
            case 'remove_field':
                rule.target_path = document.getElementById(`${prefix}_rf_target`).value;
                rule.field_to_remove = document.getElementById(`${prefix}_rf_fieldname`).value;
                break;
        }
        
        if (prefix === 'rules') {
            rulesCustomRules.push(rule);
            renderRulesRulesList();
        }
        
        hideAddRuleForm(prefix);
        showToast('Rule added');
    } catch (e) {
        showToast('Error adding rule: ' + e.message, 'error');
    }
}

// ============================================================================
// PERFORMANCE TESTER - BroadcastChannel Based
// ============================================================================

// BroadcastChannel for cross-tab communication
const perfChannel = new BroadcastChannel('perf-tester-sync');

// Performance Tester State
let perfState = {
    isRunning: false,
    isParent: true,  // This is the parent controller
    targetUrl: '',
    childTabs: [],   // References to opened tabs
    connectedTabs: {},  // Tab ID -> last ping time
    metrics: {
        latencies: [],
        pageLoads: [],
        fcpTimes: [],
        lcpTimes: [],
        errors: 0,
        messagesSent: 0
    },
    eventLog: []
};

// Initialize performance tester when section is shown
function initPerfTester() {
    setupBroadcastListener();
    logPerfEvent('INIT', 'BroadcastChannel tester ready. Channel: perf-tester-sync');
}

// Setup listener for messages from child tabs
function setupBroadcastListener() {
    perfChannel.onmessage = (event) => {
        const msg = event.data;
        
        switch (msg.type) {
            case 'child-connected':
                handleChildConnected(msg);
                break;
            case 'child-disconnected':
                handleChildDisconnected(msg);
                break;
            case 'pong':
                handlePong(msg);
                break;
            case 'metrics-report':
                handleMetricsReport(msg);
                break;
            case 'action-ack':
                handleActionAck(msg);
                break;
            case 'error':
                handleChildError(msg);
                break;
        }
    };
}

function handleChildConnected(msg) {
    perfState.connectedTabs[msg.tabId] = {
        id: msg.tabId,
        connectedAt: Date.now(),
        lastPing: Date.now(),
        url: msg.url || 'unknown',
        metrics: {}
    };
    updateTabsUI();
    updateConnectedCount();
    logPerfEvent('CONNECT', `Tab ${msg.tabId} connected from ${msg.url || 'unknown'}`);
}

function handleChildDisconnected(msg) {
    delete perfState.connectedTabs[msg.tabId];
    updateTabsUI();
    updateConnectedCount();
    logPerfEvent('DISCONNECT', `Tab ${msg.tabId} disconnected`);
}

function handlePong(msg) {
    if (perfState.connectedTabs[msg.tabId]) {
        const latency = Date.now() - msg.pingTime;
        perfState.connectedTabs[msg.tabId].lastPing = Date.now();
        perfState.connectedTabs[msg.tabId].latency = latency;
        perfState.metrics.latencies.push(latency);
        updateTabsUI();
        updateMetricsUI();
    }
}

function handleMetricsReport(msg) {
    if (perfState.connectedTabs[msg.tabId]) {
        perfState.connectedTabs[msg.tabId].metrics = msg.metrics;
        
        if (msg.metrics.pageLoad) perfState.metrics.pageLoads.push(msg.metrics.pageLoad);
        if (msg.metrics.fcp) perfState.metrics.fcpTimes.push(msg.metrics.fcp);
        if (msg.metrics.lcp) perfState.metrics.lcpTimes.push(msg.metrics.lcp);
        
        updateTabsUI();
        updateMetricsUI();
        logPerfEvent('METRICS', `Tab ${msg.tabId}: Load=${msg.metrics.pageLoad}ms, FCP=${msg.metrics.fcp}ms`);
    }
}

function handleActionAck(msg) {
    const latency = Date.now() - msg.sentTime;
    perfState.metrics.latencies.push(latency);
    if (perfState.connectedTabs[msg.tabId]) {
        perfState.connectedTabs[msg.tabId].latency = latency;
    }
    updateMetricsUI();
}

function handleChildError(msg) {
    perfState.metrics.errors++;
    updateMetricsUI();
    logPerfEvent('ERROR', `Tab ${msg.tabId}: ${msg.error}`);
}

// ============================================================================
// Tab Management Functions
// ============================================================================

function openChildTabs() {
    const count = parseInt(document.getElementById('perfTabCount').value);
    const targetUrl = document.getElementById('perfTargetUrl').value.trim();
    
    if (!targetUrl) {
        showToast('Please enter a target URL first', 'error');
        return;
    }
    
    // Add protocol if missing
    let url = targetUrl;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = 'https://' + url;
        document.getElementById('perfTargetUrl').value = url;
    }
    
    perfState.targetUrl = url;
    
    // Open child tabs with the child script
    for (let i = 0; i < count; i++) {
        const childUrl = `/perf-child?url=${encodeURIComponent(url)}&tabId=${i + 1}`;
        const tab = window.open(childUrl, `perf_child_${i + 1}`);
        if (tab) {
            perfState.childTabs.push(tab);
        }
    }
    
    logPerfEvent('TABS', `Opened ${count} child tabs for ${url}`);
    showToast(`Opening ${count} child tabs...`, 'info');
    
    // Ping tabs after a delay to check connection
    setTimeout(() => pingAllTabs(), 2000);
}

function closeChildTabs() {
    perfState.childTabs.forEach(tab => {
        try {
            if (tab && !tab.closed) {
                tab.close();
            }
        } catch (e) {}
    });
    
    perfState.childTabs = [];
    perfState.connectedTabs = {};
    updateTabsUI();
    updateConnectedCount();
    logPerfEvent('TABS', 'All child tabs closed');
    showToast('Child tabs closed', 'info');
}

function pingAllTabs() {
    const pingTime = Date.now();
    perfChannel.postMessage({
        type: 'ping',
        pingTime: pingTime
    });
    perfState.metrics.messagesSent++;
    updateMetricsUI();
    logPerfEvent('PING', 'Ping sent to all tabs');
}

function broadcastNavigate() {
    const url = document.getElementById('perfTargetUrl').value.trim();
    if (!url) {
        showToast('Please enter a target URL', 'error');
        return;
    }
    
    perfChannel.postMessage({
        type: 'navigate',
        url: url,
        sentTime: Date.now()
    });
    perfState.metrics.messagesSent++;
    updateMetricsUI();
    logPerfEvent('NAV', `Navigate command sent: ${url}`);
}

function broadcastClick(selector) {
    perfChannel.postMessage({
        type: 'click',
        selector: selector,
        sentTime: Date.now()
    });
    perfState.metrics.messagesSent++;
    updateMetricsUI();
}

function broadcastScroll(deltaY) {
    perfChannel.postMessage({
        type: 'scroll',
        deltaY: deltaY,
        sentTime: Date.now()
    });
    perfState.metrics.messagesSent++;
}

function broadcastType(selector, text) {
    perfChannel.postMessage({
        type: 'type',
        selector: selector,
        text: text,
        sentTime: Date.now()
    });
    perfState.metrics.messagesSent++;
    updateMetricsUI();
}

// ============================================================================
// UI Update Functions
// ============================================================================

function updateTabsUI() {
    const grid = document.getElementById('perfTabsGrid');
    const tabs = Object.values(perfState.connectedTabs);
    
    if (tabs.length === 0) {
        grid.innerHTML = `
            <div class="text-secondary text-center py-4">
                <i class="bi bi-window-plus" style="font-size: 2rem;"></i>
                <p class="mt-2 mb-0">No child tabs connected. Click "Open Child Tabs" to start.</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    tabs.forEach(tab => {
        const isOnline = (Date.now() - tab.lastPing) < 10000;
        const statusClass = isOnline ? 'connected' : 'disconnected';
        const statusBadge = isOnline ? 'online' : 'offline';
        
        html += `
            <div class="perf-tab-card ${statusClass}">
                <div class="perf-tab-header">
                    <span class="perf-tab-id"><i class="bi bi-window"></i> Tab ${tab.id}</span>
                    <span class="perf-tab-status ${statusBadge}">${isOnline ? 'Online' : 'Offline'}</span>
                </div>
                <div class="perf-tab-metrics">
                    <div class="perf-tab-metric">
                        <div class="perf-tab-metric-value">${tab.latency || 0}ms</div>
                        <div class="perf-tab-metric-label">Latency</div>
                    </div>
                    <div class="perf-tab-metric">
                        <div class="perf-tab-metric-value">${tab.metrics?.pageLoad || 0}ms</div>
                        <div class="perf-tab-metric-label">Load</div>
                    </div>
                    <div class="perf-tab-metric">
                        <div class="perf-tab-metric-value">${tab.metrics?.fcp || 0}ms</div>
                        <div class="perf-tab-metric-label">FCP</div>
                    </div>
                </div>
                <div style="font-size: 10px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    ${tab.url || 'unknown'}
                </div>
            </div>
        `;
    });
    
    grid.innerHTML = html;
}

function updateConnectedCount() {
    const count = Object.keys(perfState.connectedTabs).length;
    document.getElementById('perfConnectedCount').textContent = `${count} connected`;
    document.getElementById('metricConnectedTabs').querySelector('.perf-metric-value').textContent = count;
    
    const indicator = document.getElementById('perfSyncIndicator');
    const status = document.getElementById('perfSyncStatus');
    
    if (count > 0) {
        indicator.classList.add('syncing');
        status.textContent = 'Connected';
    } else {
        indicator.classList.remove('syncing');
        status.textContent = 'Ready';
    }
}

function updateMetricsUI() {
    const m = perfState.metrics;
    
    document.getElementById('metricAvgLatency').querySelector('.perf-metric-value').textContent = 
        calculateAvg(m.latencies) + 'ms';
    document.getElementById('metricP95Latency').querySelector('.perf-metric-value').textContent = 
        calculateP95(m.latencies) + 'ms';
    document.getElementById('metricPageLoad').querySelector('.perf-metric-value').textContent = 
        calculateAvg(m.pageLoads) + 'ms';
    document.getElementById('metricFCP').querySelector('.perf-metric-value').textContent = 
        calculateAvg(m.fcpTimes) + 'ms';
    document.getElementById('metricLCP').querySelector('.perf-metric-value').textContent = 
        calculateAvg(m.lcpTimes) + 'ms';
    document.getElementById('metricMessagesSent').querySelector('.perf-metric-value').textContent = 
        m.messagesSent;
    document.getElementById('metricErrors').querySelector('.perf-metric-value').textContent = 
        m.errors;
}

// ============================================================================
// Test Control Functions
// ============================================================================

function startBroadcastTest() {
    const connectedCount = Object.keys(perfState.connectedTabs).length;
    if (connectedCount === 0) {
        showToast('No child tabs connected. Open child tabs first.', 'error');
        return;
    }
    
    perfState.isRunning = true;
    
    // Update UI
    document.getElementById('perfStartBtn').disabled = true;
    document.getElementById('perfStopBtn').disabled = false;
    
    // Reset metrics but keep connected tabs
    perfState.metrics = {
        latencies: [],
        pageLoads: [],
        fcpTimes: [],
        lcpTimes: [],
        errors: 0,
        messagesSent: 0
    };
    
    // Tell children to start recording
    perfChannel.postMessage({
        type: 'start-recording',
        sentTime: Date.now()
    });
    perfState.metrics.messagesSent++;
    
    logPerfEvent('START', 'Recording started');
    showToast('Recording started - metrics collection active', 'success');
    updateMetricsUI();
}

function stopBroadcastTest() {
    perfState.isRunning = false;
    
    // Update UI
    document.getElementById('perfStartBtn').disabled = false;
    document.getElementById('perfStopBtn').disabled = true;
    
    // Tell children to stop recording
    perfChannel.postMessage({
        type: 'stop-recording',
        sentTime: Date.now()
    });
    perfState.metrics.messagesSent++;
    
    logPerfEvent('STOP', 'Recording stopped');
    showToast('Recording stopped', 'info');
    updateMetricsUI();
}

function resetPerfTest() {
    stopBroadcastTest();
    
    // Reset metrics
    perfState.metrics = {
        latencies: [],
        pageLoads: [],
        fcpTimes: [],
        lcpTimes: [],
        errors: 0,
        messagesSent: 0
    };
    
    // Clear tabs UI but keep connections
    updateMetricsUI();
    updateTabsUI();
    
    document.getElementById('perfSyncStatus').textContent = 'Ready';
    logPerfEvent('RESET', 'Metrics reset');
}

// ============================================================================
// Logging Functions
// ============================================================================

function logPerfEvent(type, detail) {
    const now = new Date();
    const time = now.toTimeString().split(' ')[0];
    
    const event = { time, type, detail };
    perfState.eventLog.unshift(event);
    
    // Keep only last 100 events
    if (perfState.eventLog.length > 100) {
        perfState.eventLog.pop();
    }
    
    // Update UI
    const logContainer = document.getElementById('perfEventLog');
    const eventHtml = `
        <div class="perf-event-item">
            <span class="perf-event-time">${time}</span>
            <span class="perf-event-type">${type}</span>
            <span class="perf-event-detail">${detail}</span>
        </div>
    `;
    
    logContainer.insertAdjacentHTML('afterbegin', eventHtml);
    
    // Limit displayed events
    const items = logContainer.querySelectorAll('.perf-event-item');
    if (items.length > 50) {
        items[items.length - 1].remove();
    }
}

function clearPerfEventLog() {
    perfState.eventLog = [];
    document.getElementById('perfEventLog').innerHTML = '';
    logPerfEvent('CLEAR', 'Event log cleared');
}

function exportPerfResults() {
    const results = {
        timestamp: new Date().toISOString(),
        config: {
            targetUrl: perfState.targetUrl,
            tabCount: Object.keys(perfState.connectedTabs).length
        },
        metrics: {
            avgLatency: calculateAvg(perfState.metrics.latencies),
            p95Latency: calculateP95(perfState.metrics.latencies),
            avgPageLoad: calculateAvg(perfState.metrics.pageLoads),
            avgFCP: calculateAvg(perfState.metrics.fcpTimes),
            avgLCP: calculateAvg(perfState.metrics.lcpTimes),
            messagesSent: perfState.metrics.messagesSent,
            totalErrors: perfState.metrics.errors
        },
        tabs: Object.values(perfState.connectedTabs).map(tab => ({
            id: tab.id,
            latency: tab.latency,
            metrics: tab.metrics,
            url: tab.url
        })),
        eventLog: perfState.eventLog.slice(0, 50)
    };
    
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `perf-results-${Date.now()}.json`;
    link.click();
    
    showToast('Results exported!');
    logPerfEvent('EXPORT', 'Results exported to JSON');
}

function calculateAvg(arr) {
    if (arr.length === 0) return 0;
    return Math.round(arr.reduce((a, b) => a + b, 0) / arr.length);
}

function calculateP95(arr) {
    if (arr.length === 0) return 0;
    const sorted = [...arr].sort((a, b) => a - b);
    const p95Index = Math.floor(sorted.length * 0.95);
    return sorted[p95Index] || 0;
}

// ============================================================================
// MIRROR MODE - Main browser + mirrored child browsers
// ============================================================================

let mirrorState = {
    isRunning: false,
    pollInterval: null
};

function startMirrorMode() {
    const url = document.getElementById('mirrorTargetUrl').value.trim();
    if (!url) {
        showToast('Please enter a target URL', 'error');
        return;
    }
    
    const config = {
        url: url,
        num_children: parseInt(document.getElementById('mirrorChildCount').value),
        headless_children: document.getElementById('mirrorHeadlessChildren').checked,
        ignore_ssl: document.getElementById('mirrorIgnoreSSL').checked
    };
    
    // Update UI
    document.getElementById('mirrorStartBtn').disabled = true;
    document.getElementById('mirrorStopBtn').disabled = false;
    document.getElementById('mirrorStatusBar').style.display = 'block';
    document.getElementById('mirrorStatusText').textContent = `Starting 1 main + ${config.num_children} child browsers...`;
    
    mirrorState.isRunning = true;
    
    // Clear previous log
    document.getElementById('mirrorEventLog').innerHTML = '';
    logMirrorEvent('START', `Starting mirror mode with ${config.num_children} child browsers`);
    
    // Start mirror mode
    fetch('/api/mirror/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            showToast(data.error, 'error');
            resetMirrorUI();
            return;
        }
        
        showToast('Mirror mode starting - a browser window will open', 'success');
        
        // Start polling for status
        mirrorState.pollInterval = setInterval(pollMirrorStatus, 1000);
    })
    .catch(err => {
        showToast('Error starting mirror mode: ' + err.message, 'error');
        resetMirrorUI();
    });
}

function stopMirrorMode() {
    fetch('/api/mirror/stop', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
        document.getElementById('mirrorStatusText').textContent = 'Stopping...';
        logMirrorEvent('STOP', 'Stop requested');
    });
}

function pollMirrorStatus() {
    fetch('/api/mirror/status')
    .then(r => r.json())
    .then(data => {
        // Update metrics
        document.getElementById('mirrorMetricChildren').querySelector('.perf-metric-value').textContent = 
            data.num_children;
        document.getElementById('mirrorMetricActions').querySelector('.perf-metric-value').textContent = 
            data.metrics.actions_mirrored;
        document.getElementById('mirrorMetricLatency').querySelector('.perf-metric-value').textContent = 
            data.metrics.avg_latency + 'ms';
        document.getElementById('mirrorMetricErrors').querySelector('.perf-metric-value').textContent = 
            data.metrics.errors;
        
        // Update status text
        if (data.is_running) {
            document.getElementById('mirrorStatusText').textContent = 
                `Running: ${data.num_children} children mirroring, ${data.metrics.actions_mirrored} actions`;
        } else {
            document.getElementById('mirrorStatusText').textContent = 'Stopped';
        }
        
        // Update log
        updateMirrorLog(data.log);
        
        // If stopped, update UI
        if (!data.is_running && mirrorState.isRunning) {
            mirrorState.isRunning = false;
            clearInterval(mirrorState.pollInterval);
            resetMirrorUI();
            logMirrorEvent('STOPPED', 'Mirror mode ended');
        }
    })
    .catch(err => {
        console.log('Poll error:', err);
    });
}

function updateMirrorLog(log) {
    const container = document.getElementById('mirrorEventLog');
    
    // Get existing event count
    const existingEvents = container.querySelectorAll('.perf-event-item').length;
    
    // Add new events (log is already in reverse chronological order)
    const newEvents = log.slice(0, Math.max(0, log.length - existingEvents));
    
    newEvents.reverse().forEach(event => {
        const eventHtml = `
            <div class="perf-event-item">
                <span class="perf-event-time">${event.time}</span>
                <span class="perf-event-type">${event.type}</span>
                <span class="perf-event-detail">${event.message}${event.session_id ? ` [C${event.session_id}]` : ''}</span>
            </div>
        `;
        container.insertAdjacentHTML('afterbegin', eventHtml);
    });
    
    // Limit displayed events
    const items = container.querySelectorAll('.perf-event-item');
    if (items.length > 100) {
        for (let i = 100; i < items.length; i++) {
            items[i].remove();
        }
    }
}

function resetMirrorUI() {
    document.getElementById('mirrorStartBtn').disabled = false;
    document.getElementById('mirrorStopBtn').disabled = true;
    document.getElementById('mirrorStatusBar').style.display = 'none';
    
    if (mirrorState.pollInterval) {
        clearInterval(mirrorState.pollInterval);
        mirrorState.pollInterval = null;
    }
}

function logMirrorEvent(type, detail) {
    const now = new Date();
    const time = now.toTimeString().split(' ')[0];
    
    const logContainer = document.getElementById('mirrorEventLog');
    const eventHtml = `
        <div class="perf-event-item">
            <span class="perf-event-time">${time}</span>
            <span class="perf-event-type">${type}</span>
            <span class="perf-event-detail">${detail}</span>
        </div>
    `;
    
    logContainer.insertAdjacentHTML('afterbegin', eventHtml);
}

function clearMirrorLog() {
    document.getElementById('mirrorEventLog').innerHTML = '';
    logMirrorEvent('CLEAR', 'Log cleared');
}

// Initialize the page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing Create Entities section...');
    
    // Since Create Entities is now the default section, we need to initialize it
    // Show the blueprint hierarchy builder by default
    try {
        const hierarchyBuilder = document.getElementById('blueprintHierarchyBuilder');
        if (hierarchyBuilder) {
            hierarchyBuilder.classList.remove('section-hidden');
            console.log('Blueprint hierarchy builder shown');
        }
        
        // Load default blueprint rules
        fetch('/api/default-rules/blueprint')
            .then(response => response.json())
            .then(data => {
                console.log('Default blueprint rules loaded:', data);
            })
            .catch(error => {
                console.error('Error loading default blueprint rules:', error);
            });
        
        // Load saved rules
        fetch('/api/rules')
            .then(response => response.json())
            .then(data => {
                console.log('Saved rules loaded:', data);
            })
            .catch(error => {
                console.error('Error loading saved rules:', error);
            });
            
    } catch (error) {
        console.error('Error during initialization:', error);
    }
});

// Service count adjustment functions
function adjustServiceCount(delta) {
    const input = document.getElementById('serviceCountInput');
    if (input) {
        const currentValue = parseInt(input.value) || 1;
        const newValue = Math.max(1, Math.min(50, currentValue + delta));
        input.value = newValue;
        onServiceCountChange(newValue);
    }
}

function onServiceCountChange(value) {
    const serviceCount = parseInt(value) || 1;
    console.log('Service count changed to:', serviceCount);
    
    // Update any related calculations or UI elements
    // This function can be expanded to handle service count changes
}

function adjustRulesServiceCount(delta) {
    const input = document.getElementById('rulesServiceCountInput');
    if (input) {
        const currentValue = parseInt(input.value) || 1;
        const newValue = Math.max(1, Math.min(50, currentValue + delta));
        input.value = newValue;
        onRulesServiceCountChange(newValue);
    }
}

function onRulesServiceCountChange(value) {
    const serviceCount = parseInt(value) || 1;
    console.log('Rules service count changed to:', serviceCount);
    
    // Update any related calculations or UI elements
    // This function can be expanded to handle rules service count changes
}

// ============================================================================
// ANALYZER FUNCTIONS
// ============================================================================

let analyzerState = {
    isConnected: false,
    applications: [],
    selectedApp: null,
    flowData: null
};

function initAnalyzer() {
    console.log('Initializing Analyzer...');
    resetAnalyzerUI();
    setupClusterTypeToggle();
}

function setupClusterTypeToggle() {
    // Add event listeners for cluster type toggle
    document.querySelectorAll('input[name="clusterType"]').forEach(radio => {
        radio.addEventListener('change', updateClusterTypeUI);
    });
    
    // Initialize UI based on default selection
    updateClusterTypeUI();
}

function updateClusterTypeUI() {
    const selectedType = document.querySelector('input[name="clusterType"]:checked').value;
    const ipLabel = document.getElementById('ipAddressLabel');
    const ipHelp = document.getElementById('ipAddressHelp');
    const namespaceSection = document.getElementById('namespaceSection');
    
    if (selectedType === 'pc') {
        ipLabel.textContent = 'PC IP Address';
        ipHelp.textContent = 'IP address of the Prism Central cluster';
        namespaceSection.style.display = 'none';
    } else {
        ipLabel.textContent = 'NCM IP Address';
        ipHelp.textContent = 'IP address of the Nutanix Cloud Manager';
        namespaceSection.style.display = 'block';
    }
}

function resetAnalyzerUI() {
    // Reset all progress steps
    const steps = ['sshStep', 'kubeconfigStep', 'podDiscoveryStep', 'logCollectionStep', 'logAnalysisStep'];
    steps.forEach(stepId => {
        const step = document.getElementById(stepId);
        step.className = 'progress-step';
        step.querySelector('.progress-status').textContent = 'Waiting...';
        step.querySelector('.spinner-border').style.display = 'none';
        step.querySelector('.bi-check-circle-fill').style.display = 'none';
        step.querySelector('.bi-x-circle-fill').style.display = 'none';
    });
    
    // Hide sections
    document.getElementById('analyzerProgressSection').style.display = 'none';
    document.getElementById('analyzerAppSelectorSection').style.display = 'none';
    document.getElementById('analyzerFlowSection').style.display = 'none';
    document.getElementById('analyzerDetailsSection').style.display = 'none';
    
    // Reset state
    analyzerState.isConnected = false;
    analyzerState.applications = [];
    analyzerState.selectedApp = null;
    analyzerState.flowData = null;
}

function updateProgressStep(stepId, status, message) {
    const step = document.getElementById(stepId);
    if (!step) {
        console.warn(`Progress step element not found: ${stepId}`);
        return;
    }
    
    const statusEl = step.querySelector('.progress-status');
    const spinner = step.querySelector('.spinner-border');
    const successIcon = step.querySelector('.bi-check-circle-fill');
    const errorIcon = step.querySelector('.bi-x-circle-fill');
    const progressIcon = step.querySelector('.progress-icon');
    
    if (!statusEl) {
        console.warn(`Progress status element not found in step: ${stepId}`);
        return;
    }
    
    // Check if we need to add a skipped icon
    let skipIcon = step.querySelector('.bi-dash-circle-fill');
    if (!skipIcon && progressIcon) {
        // Create skip icon if it doesn't exist
        skipIcon = document.createElement('i');
        skipIcon.className = 'bi bi-dash-circle-fill';
        skipIcon.style.display = 'none';
        progressIcon.appendChild(skipIcon);
    }
    
    // Reset all indicators (with null checks)
    if (spinner) spinner.style.display = 'none';
    if (successIcon) successIcon.style.display = 'none';
    if (errorIcon) errorIcon.style.display = 'none';
    if (skipIcon) skipIcon.style.display = 'none';
    
    // Update status
    statusEl.textContent = message;
    step.className = `progress-step ${status}`;
    
    if (status === 'active' && spinner) {
        spinner.style.display = 'block';
    } else if (status === 'success' && successIcon) {
        successIcon.style.display = 'block';
    } else if (status === 'error' && errorIcon) {
        errorIcon.style.display = 'block';
    } else if (status === 'skipped' && skipIcon) {
        skipIcon.style.display = 'block';
    }
}

async function connectToCluster(forceRefresh = false) {
    const pcIp = document.getElementById('analyzerPcIp').value.trim();
    const namespace = document.getElementById('analyzerNamespace').value.trim() || 'ntnx-ncm-selfservice';
    const clusterType = document.querySelector('input[name="clusterType"]:checked').value;
    
    if (!pcIp) {
        showToast('Please enter an IP address', 'error');
        return;
    }
    
    // Validate IP format
    const ipRegex = /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/;
    if (!ipRegex.test(pcIp)) {
        showToast('Please enter a valid IP address', 'error');
        return;
    }
    
    // Reset state
    analyzerState.isConnected = false;
    analyzerState.applications = [];
    analyzerState.selectedApp = null;
    
    // Hide existing logs section initially
    document.getElementById('analyzerExistingLogsSection').style.display = 'none';
    
    // If not forcing refresh, check for existing logs first
    if (!forceRefresh) {
        try {
            console.log('Checking for existing logs...');
            
            // Show a temporary checking message
            showToast('Checking for existing logs...', 'info', 2000);
            
            const existingLogsCheck = await analyzerApiCall('/api/analyzer/check-existing-logs', { 
                pc_ip: pcIp, 
                cluster_type: clusterType 
            });
            
            console.log('Existing logs check result:', existingLogsCheck);
            
            if (existingLogsCheck && existingLogsCheck.exists) {
                // Show existing logs notification
                const collectionTime = existingLogsCheck.collection_time ? 
                    new Date(existingLogsCheck.collection_time).toLocaleString() : 'Unknown';
                
                document.getElementById('existingLogsInfo').innerHTML = `
                    <strong>Collection Time:</strong> ${collectionTime}<br>
                    <strong>Services:</strong> ${existingLogsCheck.services_count || 0} | <strong>Files:</strong> ${existingLogsCheck.files_count || 0}
                `;
                document.getElementById('analyzerExistingLogsSection').style.display = 'block';
                
                // Hide progress section initially
                document.getElementById('analyzerProgressSection').style.display = 'none';
                
                // Show success message
                showToast('Found existing logs! Choose an option below.', 'success');
                
                console.log('Showing existing logs dialog');
                return; // Stop here and let user choose
            } else {
                console.log('No existing logs found, proceeding with fresh collection');
                showToast('No existing logs found, collecting fresh logs...', 'info');
            }
        } catch (error) {
            console.log('Error checking existing logs:', error);
            console.log('Proceeding with fresh collection');
            showToast('Error checking existing logs, collecting fresh logs...', 'warning');
        }
    }
    
    // Show progress section
    document.getElementById('analyzerProgressSection').style.display = 'block';
    document.getElementById('analyzerConnectBtn').disabled = true;
    
    try {
        // Step 1: SSH Connection
        updateProgressStep('sshStep', 'active', 'Establishing SSH connection...');
        await analyzerApiCall('/api/analyzer/ssh-connect', { pc_ip: pcIp, cluster_type: clusterType });
        updateProgressStep('sshStep', 'success', 'SSH connection established');
        
        // Step 2: Configuration Setup (Kubeconfig for NCM, Docker validation for PC)
        const configLabel = clusterType === 'pc' ? 'Docker setup' : 'Kubeconfig setup';
        updateProgressStep('kubeconfigStep', 'active', `Setting up ${configLabel}...`);
        await analyzerApiCall('/api/analyzer/kubeconfig-setup', { pc_ip: pcIp, cluster_type: clusterType });
        updateProgressStep('kubeconfigStep', 'success', `${configLabel} completed`);
        
        // Step 3: Service Discovery (Containers for PC, Pods for NCM)
        const discoveryLabel = clusterType === 'pc' ? 'containers' : 'pods';
        updateProgressStep('podDiscoveryStep', 'active', `Discovering ${discoveryLabel}...`);
        const serviceData = await analyzerApiCall('/api/analyzer/discover-pods', { 
            pc_ip: pcIp, 
            cluster_type: clusterType,
            namespace: clusterType === 'ncm' ? namespace : undefined 
        });
        updateProgressStep('podDiscoveryStep', 'success', `Found ${serviceData.pod_count} ${discoveryLabel}`);
        
        // Step 4: Log Collection
        updateProgressStep('logCollectionStep', 'active', 'Collecting logs...');
        const logData = await analyzerApiCall('/api/analyzer/collect-logs', { 
            pc_ip: pcIp,
            cluster_type: clusterType,
            namespace: clusterType === 'ncm' ? namespace : undefined,
            pods: serviceData.pods,
            force_refresh: forceRefresh
        });
        
        if (logData.using_existing) {
            updateProgressStep('logCollectionStep', 'success', `Using existing logs (${logData.files_count} files)`);
        } else {
            updateProgressStep('logCollectionStep', 'success', `Collected ${logData.log_count || logData.files_count} log files`);
        }
        
        // Step 5: Log Analysis
        updateProgressStep('logAnalysisStep', 'active', 'Analyzing logs...');
        const analysisData = await analyzerApiCall('/api/analyzer/analyze-logs', { pc_ip: pcIp, cluster_type: clusterType });
        updateProgressStep('logAnalysisStep', 'success', `Found ${analysisData.application_count} applications`);
        
        // Update state and show application selector
        analyzerState.isConnected = true;
        analyzerState.applications = analysisData.applications;
        populateApplicationSelector(analysisData.applications);
        
        // Show application selector section
        document.getElementById('analyzerAppSelectorSection').style.display = 'block';
        
        showToast('Analysis completed successfully!', 'success');
        
    } catch (error) {
        console.error('Analyzer error:', error);
        
        // Find which step failed and mark it as error
        const steps = ['sshStep', 'kubeconfigStep', 'podDiscoveryStep', 'logCollectionStep', 'logAnalysisStep'];
        for (const stepId of steps) {
            const step = document.getElementById(stepId);
            if (step.classList.contains('active')) {
                updateProgressStep(stepId, 'error', error.message || 'Operation failed');
                break;
            }
        }
        
        showToast(`Analysis failed: ${error.message}`, 'error');
    } finally {
        document.getElementById('analyzerConnectBtn').disabled = false;
    }
}

async function useExistingLogs() {
    const pcIpElement = document.getElementById('analyzerPcIp');
    const clusterTypeElement = document.querySelector('input[name="clusterType"]:checked');
    
    if (!pcIpElement || !clusterTypeElement) {
        console.error('Required form elements not found');
        showToast('Form elements not found. Please refresh the page.', 'error');
        return;
    }
    
    const pcIp = pcIpElement.value.trim();
    const clusterType = clusterTypeElement.value;
    
    // Hide existing logs section
    const existingLogsSection = document.getElementById('analyzerExistingLogsSection');
    if (existingLogsSection) {
        existingLogsSection.style.display = 'none';
    }
    
    try {
        // Show progress section
        const progressSection = document.getElementById('analyzerProgressSection');
        const connectBtn = document.getElementById('analyzerConnectBtn');
        
        if (progressSection) {
            progressSection.style.display = 'block';
        }
        if (connectBtn) {
            connectBtn.disabled = true;
        }
        
        // Mark initial steps as skipped since we're using existing logs
        updateProgressStep('sshStep', 'skipped', 'SSH connection skipped (using existing logs)');
        updateProgressStep('kubeconfigStep', 'skipped', 'Setup skipped (using existing logs)');
        updateProgressStep('podDiscoveryStep', 'skipped', 'Discovery skipped (using existing logs)');
        updateProgressStep('logCollectionStep', 'skipped', 'Collection skipped (using existing logs)');
        
        // Skip to analysis step
        updateProgressStep('logAnalysisStep', 'active', 'Analyzing existing logs...');
        const analysisData = await analyzerApiCall('/api/analyzer/analyze-logs', { pc_ip: pcIp, cluster_type: clusterType });
        updateProgressStep('logAnalysisStep', 'success', `Found ${analysisData.application_count} applications`);
        
        // Update state and show application selector
        analyzerState.isConnected = true;
        analyzerState.applications = analysisData.applications;
        populateApplicationSelector(analysisData.applications);
        
        // Show application selector section
        const appSelectorSection = document.getElementById('analyzerAppSelectorSection');
        if (appSelectorSection) {
            appSelectorSection.style.display = 'block';
        }
        
        showToast('Analysis completed using existing logs!', 'success');
        
    } catch (error) {
        console.error('Analysis error:', error);
        updateProgressStep('logAnalysisStep', 'error', error.message || 'Analysis failed');
        showToast(`Analysis failed: ${error.message}`, 'error');
    } finally {
        const connectBtn = document.getElementById('analyzerConnectBtn');
        if (connectBtn) {
            connectBtn.disabled = false;
        }
    }
}

async function fetchLatestLogs() {
    // Hide existing logs section
    document.getElementById('analyzerExistingLogsSection').style.display = 'none';
    
    // Reset all progress steps to waiting state
    resetProgressSteps();
    
    // Force refresh by calling connectToCluster with forceRefresh = true
    await connectToCluster(true);
}

function resetProgressSteps() {
    updateProgressStep('sshStep', 'waiting', 'Waiting...');
    updateProgressStep('kubeconfigStep', 'waiting', 'Waiting...');
    updateProgressStep('podDiscoveryStep', 'waiting', 'Waiting...');
    updateProgressStep('logCollectionStep', 'waiting', 'Waiting...');
    updateProgressStep('logAnalysisStep', 'waiting', 'Waiting...');
}

async function analyzerApiCall(endpoint, data) {
    const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
    }
    
    return await response.json();
}

function populateApplicationSelector(applications) {
    const selector = document.getElementById('analyzerAppSelector');
    selector.innerHTML = '<option value="">Choose an application...</option>';
    
    applications.forEach(app => {
        const option = document.createElement('option');
        option.value = app.uuid;
        option.textContent = `${app.uuid} (${app.service_count} services)`;
        selector.appendChild(option);
    });
    
    // Update stats
    document.getElementById('totalAppsCount').textContent = applications.length;
    const totalServices = applications.reduce((sum, app) => sum + app.service_count, 0);
    document.getElementById('totalServicesCount').textContent = totalServices;
}

async function loadApplicationFlow() {
    console.log('loadApplicationFlow called');
    const selectedUuid = document.getElementById('analyzerAppSelector').value;
    console.log('Selected UUID:', selectedUuid);
    
    if (!selectedUuid) {
        document.getElementById('analyzerFlowSection').style.display = 'none';
        document.getElementById('analyzerDetailsSection').style.display = 'none';
        return;
    }
    
    try {
        showLoading(true);
        
        // Get flow data for selected application
        const flowData = await analyzerApiCall('/api/analyzer/get-flow', { 
            pc_ip: document.getElementById('analyzerPcIp').value.trim(),
            cluster_type: document.querySelector('input[name="clusterType"]:checked').value,
            application_uuid: selectedUuid 
        });
        
        analyzerState.selectedApp = selectedUuid;
        analyzerState.flowData = flowData;
        analyzerState.currentFlowData = flowData;
                
                console.log('Flow data keys:', Object.keys(flowData));
                console.log('Timeline analysis available:', !!flowData.timeline_analysis);
        
        // Render flow diagram
        renderFlowDiagram(flowData);
        
        // Show flow section
        document.getElementById('analyzerFlowSection').style.display = 'block';
        
        // Force show timeline analysis section for debugging
        const timelineSection = document.getElementById('timeline-analysis-section');
        if (timelineSection) {
            timelineSection.style.display = 'block';
            console.log('Timeline section forced to show');
        }
        
        // Render timeline analysis if available
        if (flowData.timeline_analysis) {
            console.log('Timeline analysis data found, rendering...');
            renderTimelineAnalysis(flowData.timeline_analysis);
        } else {
            console.log('No timeline analysis data found in flowData');
            // Even if no data, show the section with empty state
            if (timelineSection) {
                timelineSection.innerHTML = `
                    <div class="text-center p-4">
                        <h5>Timeline Analysis</h5>
                        <p>No timeline data available. Please run analysis first.</p>
                        <button class="btn btn-primary" onclick="testTimelineSection()">Test Timeline</button>
                    </div>
                `;
            }
        }
        
        // Start live visualization after a short delay
        setTimeout(() => {
            startLiveFlowVisualization();
        }, 2000);
        
        showToast('Flow diagram loaded successfully!', 'success');
        
    } catch (error) {
        console.error('Flow loading error:', error);
        showToast(`Failed to load flow: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

function renderFlowDiagram(flowData) {
    const diagramContainer = document.getElementById('analyzerFlowDiagram');
    
    // Create comprehensive timeline-based flow diagram
    let diagramHtml = `
        <div style="padding: 20px; color: var(--text-primary); font-family: 'Courier New', monospace;">
            <h5 style="color: var(--accent-blue); margin-bottom: 20px;">
                📊 Application Flow Analysis: ${flowData.application_uuid}
            </h5>
            
            <!-- Summary Section -->
            <div style="background: var(--bg-secondary); padding: 15px; border-radius: 8px; margin-bottom: 25px;">
                <h6 style="color: var(--accent-green); margin-bottom: 10px;">📈 Analysis Summary</h6>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                    <div><strong>Total Events:</strong> ${flowData.summary?.total_events || 0}</div>
                    <div><strong>Services Involved:</strong> ${flowData.summary?.services_involved || 0}</div>
                    <div><strong>Total Duration:</strong> ${(flowData.summary?.total_duration_ms || 0).toFixed(2)}ms</div>
                    <div><strong>Service Count:</strong> ${flowData.service_count || 0}</div>
                </div>
            </div>
    `;
    
    // Timeline Phases Section
    if (flowData.timeline_phases && Array.isArray(flowData.timeline_phases) && flowData.timeline_phases.length > 0) {
        diagramHtml += `
            <div style="margin-bottom: 30px;">
                <h6 style="color: var(--accent-orange); margin-bottom: 15px;">⏱️ Timeline and Service Interactions</h6>
        `;
        
        flowData.timeline_phases.forEach((phase, phaseIndex) => {
            const phaseColor = phaseIndex === 0 ? 'var(--accent-purple)' : 
                             phaseIndex === 1 ? 'var(--accent-blue)' : 
                             phaseIndex === 2 ? 'var(--accent-green)' : 'var(--accent-red)';
            
            diagramHtml += `
                <div style="margin-bottom: 25px; border-left: 4px solid ${phaseColor}; padding-left: 20px;">
                    <h6 style="color: ${phaseColor}; margin-bottom: 10px;">
                        ${phase.name === 'Execution Flow Sequence' ? '🔄' : `Phase ${phaseIndex}`}: ${phase.name}
                    </h6>
                    <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 15px;">
                        ${phase.start_time ? new Date(phase.start_time).toLocaleString() : 'Unknown'} - 
                        Duration: ~${(phase.duration_ms || 0).toFixed(0)}ms
                    </div>
                    
                    <div style="margin-left: 20px;">
            `;
            
            // Special rendering for execution flow sequence
            if (phase.name === 'Execution Flow Sequence' && phase.execution_flow && Array.isArray(phase.execution_flow)) {
                diagramHtml += `
                    <div style="background: linear-gradient(135deg, ${phaseColor}20, ${phaseColor}10); border: 2px solid ${phaseColor}; padding: 20px; border-radius: 12px; margin-bottom: 20px;">
                        <div style="font-weight: bold; color: ${phaseColor}; margin-bottom: 15px; font-size: 16px; text-align: center;">
                            🔗 Service Execution Flow
                        </div>
                        <div style="font-family: monospace; font-size: 16px; color: var(--text-primary); margin-bottom: 15px; text-align: center; font-weight: bold;">
                            ${phase.execution_flow.map(step => step.service_instance).join(' → ')}
                        </div>
                        <div style="display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 10px; margin-top: 15px;">
                `;
                
                phase.execution_flow.forEach((step, stepIndex) => {
                    const stepColor = stepIndex === 0 ? 'var(--accent-green)' : 
                                    stepIndex === phase.execution_flow.length - 1 ? 'var(--accent-red)' : 'var(--accent-blue)';
                    
                    diagramHtml += `
                        <div class="flow-step-animated" data-step="${stepIndex}" data-service-name="${step.service_instance}" data-duration="${step.duration_from_start || 0}" style="
                            background: ${stepColor}30; 
                            border: 2px solid ${stepColor}; 
                            border-radius: 8px; 
                            padding: 12px 16px; 
                            text-align: center;
                            cursor: pointer;
                            transition: all 0.3s ease;
                            animation: flowStepAppear 0.5s ease ${stepIndex * 0.15}s both;
                            min-width: 90px;
                            box-shadow: 0 2px 8px ${stepColor}30;
                        " onclick="highlightFlowStep('${step.service_instance}', ${step.duration_from_start || 0})" 
                           onmouseover="this.style.transform='scale(1.1)'; this.style.boxShadow='0 4px 16px ${stepColor}50'" 
                           onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 2px 8px ${stepColor}30'">
                            <div style="font-weight: bold; color: ${stepColor}; font-size: 13px; margin-bottom: 4px;">
                                ${step.service_instance}
                            </div>
                            <div style="color: var(--text-secondary); font-size: 10px; margin-bottom: 2px;">
                                ${step.timestamp ? new Date(step.timestamp).toLocaleTimeString() : ''}
                            </div>
                            <div style="color: var(--text-tertiary); font-size: 9px; font-weight: bold;">
                                +${(step.duration_from_start || 0).toFixed(0)}ms
                            </div>
                        </div>
                    `;
                    
                    if (stepIndex < phase.execution_flow.length - 1) {
                        diagramHtml += `<div class="flow-arrow" style="
                            color: ${phaseColor}; 
                            font-size: 20px;
                            font-weight: bold;
                            animation: flowArrowPulse 2s ease-in-out infinite;
                        ">→</div>`;
                    }
                });
                
                diagramHtml += `
                        </div>
                    </div>
                `;
            }
            
            // Render services in this phase
            if (phase.services && Array.isArray(phase.services) && phase.services.length > 0) {
                phase.services.forEach(service => {
                    diagramHtml += `
                        <div style="margin-bottom: 15px; background: var(--bg-tertiary); padding: 12px; border-radius: 6px;">
                            <div style="font-weight: bold; color: ${phaseColor}; margin-bottom: 8px;">
                                🔧 ${service.name} (${getServiceDescription(service.name)})
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 8px;">
                                Start: ${service.start_time ? new Date(service.start_time).toLocaleTimeString() : 'Unknown'} | 
                                End: ${service.end_time ? new Date(service.end_time).toLocaleTimeString() : 'Unknown'} | 
                                Duration: ~${(service.duration_ms || 0).toFixed(0)}ms
                            </div>
                            <div style="margin-left: 15px;">
                                <div style="color: var(--text-secondary); font-size: 11px; margin-bottom: 5px;">Actions:</div>
                    `;
                    
                    // Show actions for this service
                    if (service.actions && Array.isArray(service.actions) && service.actions.length > 0) {
                        service.actions.slice(0, 5).forEach(action => {
                            diagramHtml += `
                                <div style="margin-left: 10px; font-size: 10px; color: var(--text-tertiary); margin-bottom: 2px;">
                                    ├── ${action.name || action.type}
                                </div>
                            `;
                        });
                        
                        if (service.actions.length > 5) {
                            diagramHtml += `
                                <div style="margin-left: 10px; font-size: 10px; color: var(--text-tertiary);">
                                    └── ... and ${service.actions.length - 5} more actions
                                </div>
                            `;
                        }
                    }
                    
                    diagramHtml += `
                            </div>
                        </div>
                    `;
                });
            }
            
            diagramHtml += `
                    </div>
                </div>
            `;
        });
        
        diagramHtml += `</div>`;
    }
    
    // Service-by-Service Execution Flow
    if (flowData.execution_flow_sequence && Array.isArray(flowData.execution_flow_sequence) && flowData.execution_flow_sequence.length > 0) {
        diagramHtml += `
            <div style="margin-bottom: 30px;">
                <h6 style="color: var(--accent-blue); margin-bottom: 15px;">🔄 Service Execution Flow</h6>
                <div style="background: var(--bg-secondary); padding: 20px; border-radius: 8px;">
                    <div style="display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 10px;">
        `;
        
        flowData.execution_flow_sequence.forEach((step, index) => {
            const stepColor = index === 0 ? 'var(--accent-green)' : 
                            index === flowData.execution_flow_sequence.length - 1 ? 'var(--accent-red)' : 'var(--accent-blue)';
            
            diagramHtml += `
                <div class="flow-step-animated" data-service-name="${step.service_instance}" data-duration="${step.duration_from_start || 0}" style="
                    background: ${stepColor}20; 
                    border: 2px solid ${stepColor}; 
                    border-radius: 8px; 
                    padding: 12px 16px; 
                    text-align: center;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    animation: flowStepAppear 0.5s ease ${index * 0.2}s both;
                    min-width: 100px;
                " onclick="highlightFlowStep('${step.service_instance}', ${step.duration_from_start || 0})" 
                   onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 4px 12px ${stepColor}40'" 
                   onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='none'">
                    <div style="font-weight: bold; color: ${stepColor}; font-size: 13px; margin-bottom: 4px;">
                        ${step.service_instance}
                    </div>
                    <div style="color: var(--text-secondary); font-size: 10px;">
                        ${step.timestamp ? new Date(step.timestamp).toLocaleTimeString() : ''}
                    </div>
                    <div style="color: var(--text-tertiary); font-size: 9px; margin-top: 2px;">
                        +${(step.duration_from_start || 0).toFixed(0)}ms
                    </div>
                </div>
            `;
            
            // Add arrow between steps
            if (index < flowData.execution_flow_sequence.length - 1) {
                diagramHtml += `
                    <div class="flow-arrow" style="
                        color: var(--accent-blue); 
                        font-size: 18px; 
                        animation: flowArrowPulse 2s ease-in-out infinite;
                        margin: 0 5px;
                    ">→</div>
                `;
            }
        });
        
        diagramHtml += `
                    </div>
                    
                    <!-- Flow Summary -->
                    <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid var(--border-color); text-align: center;">
                        <div style="color: var(--text-secondary); font-size: 12px;">
                            <strong>Total Steps:</strong> ${flowData.execution_flow_sequence.length} | 
                            <strong>Duration:</strong> ${(flowData.execution_flow_sequence[flowData.execution_flow_sequence.length - 1]?.duration_from_start || 0).toFixed(0)}ms |
                            <strong>Flow:</strong> ${flowData.execution_flow_sequence.map(s => s.service_instance).join(' → ')}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Key Identifiers Section
    if (flowData.key_identifiers && typeof flowData.key_identifiers === 'object' && Object.keys(flowData.key_identifiers).length > 0) {
        diagramHtml += `
            <div style="margin-bottom: 20px;">
                <h6 style="color: var(--accent-yellow); margin-bottom: 10px;">🔑 Key Identifiers</h6>
                <div style="background: var(--bg-secondary); padding: 15px; border-radius: 8px;">
        `;
        
        Object.entries(flowData.key_identifiers).forEach(([key, values]) => {
            if (values && values.length > 0) {
                diagramHtml += `
                    <div style="margin-bottom: 8px;">
                        <strong style="color: var(--accent-yellow);">${key.replace('_', ' ').toUpperCase()}:</strong>
                        <span style="color: var(--text-secondary); font-family: monospace; font-size: 11px;">
                            ${values.slice(0, 2).join(', ')}${values.length > 2 ? '...' : ''}
                        </span>
                    </div>
                `;
            }
        });
        
        diagramHtml += `
                </div>
            </div>
        `;
    }
    
    // ASCII Flow Diagram Section
    if (flowData.ascii_flow_diagram) {
        diagramHtml += `
            <div style="margin-bottom: 30px;">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 style="color: var(--accent-purple); margin-bottom: 0;">🎯 ASCII Flow Diagram</h6>
                    <button class="btn btn-sm btn-outline-primary" onclick="copyAsciiDiagram()" title="Copy ASCII diagram to clipboard">
                        <i class="bi bi-clipboard"></i> Copy ASCII
                    </button>
                </div>
                <div id="asciiFlowDiagram" style="
                    background: var(--bg-tertiary); 
                    border: 1px solid var(--border-color); 
                    border-radius: 8px; 
                    padding: 20px; 
                    font-family: 'Courier New', 'Monaco', monospace; 
                    font-size: 12px; 
                    line-height: 1.4; 
                    white-space: pre-wrap; 
                    overflow-x: auto;
                    color: var(--text-primary);
                    max-height: 600px;
                    overflow-y: auto;
                ">${flowData.ascii_flow_diagram}</div>
            </div>
        `;
    }
    
    // Timeline Analysis Section
    if (flowData.timeline_analysis && flowData.timeline_analysis.timeline_events) {
        diagramHtml += `
            <div style="margin-top: 30px; padding: 20px; background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 12px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px;">
                    <h6 style="color: var(--accent-blue); margin-bottom: 0;">📊 Complete Timeline Analysis</h6>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-sm btn-outline-primary" onclick="exportTimelineReport()">
                            <i class="bi bi-download"></i> Export Report
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="copyTimelineData()">
                            <i class="bi bi-clipboard"></i> Copy
                        </button>
                    </div>
                </div>
                
                <!-- Timeline Header Info -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
                    <div style="background: rgba(16, 185, 129, 0.1); padding: 12px; border-radius: 8px; border-left: 3px solid var(--accent-green);">
                        <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 4px;">App UUID</div>
                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; word-break: break-all;">${flowData.timeline_analysis.app_uuid || 'N/A'}</div>
                    </div>
                    <div style="background: rgba(245, 158, 11, 0.1); padding: 12px; border-radius: 8px; border-left: 3px solid var(--accent-orange);">
                        <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 4px;">Total Events</div>
                        <div style="font-size: 1.2rem; font-weight: 600;">${flowData.timeline_analysis.total_events || 0}</div>
                    </div>
                    <div style="background: rgba(139, 92, 246, 0.1); padding: 12px; border-radius: 8px; border-left: 3px solid var(--accent-purple);">
                        <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 4px;">Services Involved</div>
                        <div style="font-size: 1.2rem; font-weight: 600;">${flowData.timeline_analysis.services_involved || 0}</div>
                    </div>
                    <div style="background: rgba(239, 68, 68, 0.1); padding: 12px; border-radius: 8px; border-left: 3px solid var(--accent-red);">
                        <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 4px;">Status</div>
                        <div style="font-size: 1rem; font-weight: 600; color: ${flowData.timeline_analysis.performance_metrics?.status === 'SUCCESS' ? 'var(--accent-green)' : 'var(--accent-orange)'};">
                            ${flowData.timeline_analysis.performance_metrics?.status === 'SUCCESS' ? '✅ SUCCESS' : '⚠️ INCOMPLETE'}
                        </div>
                    </div>
                </div>
                
                <!-- Reference IDs -->
                ${flowData.timeline_analysis.reference_ids && Object.keys(flowData.timeline_analysis.reference_ids).length > 0 ? `
                <div style="margin-bottom: 20px;">
                    <h6 style="color: var(--accent-purple); margin-bottom: 10px;">🔗 Reference IDs</h6>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px;">
                        ${Object.entries(flowData.timeline_analysis.reference_ids).map(([key, value]) => `
                            <div style="background: rgba(30, 41, 59, 0.5); padding: 10px; border-radius: 6px; font-family: 'JetBrains Mono', monospace;">
                                <span style="color: var(--accent-blue); font-weight: 600;">${key.toUpperCase()}:</span>
                                <span style="color: var(--text-primary); font-size: 0.85rem; word-break: break-all;">${value}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
                
                <!-- Timeline Events Table -->
                <div style="margin-bottom: 20px;">
                    <h6 style="color: var(--accent-blue); margin-bottom: 10px;">🔄 Timeline Events</h6>
                    <div style="max-height: 400px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: 8px;">
                        <table style="width: 100%; font-size: 0.85rem; border-collapse: collapse;">
                            <thead style="background: rgba(30, 41, 59, 0.8); position: sticky; top: 0;">
                                <tr>
                                    <th style="padding: 12px 8px; text-align: left; color: var(--accent-blue); border-bottom: 1px solid var(--border-color);">Time</th>
                                    <th style="padding: 12px 8px; text-align: left; color: var(--accent-blue); border-bottom: 1px solid var(--border-color);">Service</th>
                                    <th style="padding: 12px 8px; text-align: left; color: var(--accent-blue); border-bottom: 1px solid var(--border-color);">Operation</th>
                                    <th style="padding: 12px 8px; text-align: left; color: var(--accent-blue); border-bottom: 1px solid var(--border-color);">Target Service</th>
                                    <th style="padding: 12px 8px; text-align: left; color: var(--accent-blue); border-bottom: 1px solid var(--border-color);">Details</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${flowData.timeline_analysis.timeline_events.map((event, index) => `
                                    <tr style="border-bottom: 1px solid var(--border-color); ${index % 2 === 0 ? 'background: rgba(30, 41, 59, 0.2);' : ''}">
                                        <td style="padding: 10px 8px; font-family: 'JetBrains Mono', monospace; color: var(--accent-green);">
                                            ${event.timestamp ? event.timestamp.substring(11, 23) : 'N/A'}
                                        </td>
                                        <td style="padding: 10px 8px; font-weight: 600; color: var(--accent-purple);">
                                            ${event.service || 'N/A'}
                                        </td>
                                        <td style="padding: 10px 8px; color: var(--text-primary);">
                                            ${event.operation || 'N/A'}
                                        </td>
                                        <td style="padding: 10px 8px; color: var(--accent-orange);">
                                            ${event.target_service || 'N/A'}
                                        </td>
                                        <td style="padding: 10px 8px; color: var(--text-secondary); font-size: 0.8rem;">
                                            ${event.details || ''}
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Performance Analysis -->
                ${flowData.timeline_analysis.performance_metrics ? `
                <div>
                    <h6 style="color: var(--accent-orange); margin-bottom: 15px;">📊 Performance Analysis</h6>
                    
                    <!-- Overall Metrics -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
                        <div style="background: rgba(16, 185, 129, 0.1); padding: 12px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 4px;">Total Duration</div>
                            <div style="font-size: 1.1rem; font-weight: 600; color: var(--accent-green);">
                                ${flowData.timeline_analysis.performance_metrics.total_duration_ms ? 
                                    (flowData.timeline_analysis.performance_metrics.total_duration_ms / 1000).toFixed(2) + 's' : 'N/A'}
                            </div>
                        </div>
                        ${Object.entries(flowData.timeline_analysis.performance_metrics.service_counts || {}).map(([service, count]) => `
                            <div style="background: rgba(59, 130, 246, 0.1); padding: 12px; border-radius: 8px; text-align: center;">
                                <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 4px;">${service}</div>
                                <div style="font-size: 1.1rem; font-weight: 600; color: var(--accent-blue);">${count} ops</div>
                            </div>
                        `).join('')}
                    </div>
                    
                    <!-- Bottlenecks -->
                    ${flowData.timeline_analysis.performance_metrics.bottlenecks && flowData.timeline_analysis.performance_metrics.bottlenecks.length > 0 ? `
                    <div>
                        <h6 style="color: var(--accent-red); margin-bottom: 10px;">⚠️ Bottlenecks Identified (>100ms)</h6>
                        <div style="max-height: 200px; overflow-y: auto;">
                            ${flowData.timeline_analysis.performance_metrics.bottlenecks.map(bottleneck => `
                                <div style="background: rgba(239, 68, 68, 0.1); padding: 10px; margin-bottom: 8px; border-radius: 6px; border-left: 3px solid var(--accent-red);">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <div>
                                            <span style="font-weight: 600; color: var(--accent-red);">${bottleneck.service}</span>
                                            <span style="color: var(--text-secondary); margin-left: 8px;">${bottleneck.operation}</span>
                                        </div>
                                        <div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-orange); font-weight: 600;">
                                            ${bottleneck.duration_ms}ms
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : `
                    <div style="background: rgba(16, 185, 129, 0.1); padding: 15px; border-radius: 8px; border-left: 3px solid var(--accent-green);">
                        <div style="color: var(--accent-green); font-weight: 600;">✅ No significant bottlenecks detected</div>
                        <div style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 4px;">All operations completed in under 100ms</div>
                    </div>
                    `}
                </div>
                ` : ''}
                
                <!-- Simple Sequence Diagram Section -->
                ${flowData.timeline_analysis && flowData.timeline_analysis.sequence_diagram ? `
                <div style="margin-top: 20px; padding: 15px; background: rgba(139, 92, 246, 0.1); border-radius: 8px; border-left: 3px solid var(--accent-purple);">
                    <h6 style="color: var(--accent-purple); margin-bottom: 10px;">
                        <i class="bi bi-diagram-3"></i> Service Interaction Flow
                    </h6>
                    <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 15px;">
                        Visual sequence diagram showing service interactions during the application flow.
                    </p>
                    <button class="btn btn-sm btn-outline-primary" onclick="openSequenceDiagram()">
                        <i class="bi bi-box-arrow-up-right"></i> View Sequence Diagram
                    </button>
                </div>
                ` : ''}
                
            </div>
        `;
    }
    
    diagramHtml += `
        </div>
    `;
    
    diagramContainer.innerHTML = diagramHtml;
}

function getServiceDescription(serviceName) {
    const descriptions = {
        'STYX': 'NuCalm Service',
        'JOVE': 'Execution Engine', 
        'IRIS': 'Runlog Manager',
        'HELIOS': 'Query Service',
        'GOZAFFI': 'Entity Service',
        'NARAD': 'Policy Engine',
        'HERCULES': 'Task Manager',
        'EPSILON': 'Container Host'
    };
    return descriptions[serviceName] || 'Unknown Service';
}

function exportTimelineReport() {
    if (!analyzerState.currentFlowData || !analyzerState.currentFlowData.timeline_analysis) {
        showToast('No timeline data available to export', 'error');
        return;
    }
    
    const timelineData = analyzerState.currentFlowData.timeline_analysis;
    
    // Generate markdown report similar to del.txt
    let markdown = `# Complete App-Create Flow Timeline\n`;
    markdown += `**Generated for App UUID:** ${timelineData.app_uuid}\n`;
    markdown += `**Analysis Date:** ${new Date().toLocaleString()}\n\n`;
    
    // Reference IDs
    if (timelineData.reference_ids && Object.keys(timelineData.reference_ids).length > 0) {
        markdown += `## Reference IDs\n`;
        Object.entries(timelineData.reference_ids).forEach(([key, value]) => {
            markdown += `- **${key.toUpperCase()}:** \`${value}\`\n`;
        });
        markdown += `\n---\n\n`;
    }
    
    // Timeline Events
    markdown += `## 🔄 COMPLETE FLOW TIMELINE\n\n`;
    markdown += `| Time | Service | Operation | Target Service | Details |\n`;
    markdown += `|------|---------|-----------|----------------|---------|\n`;
    
    timelineData.timeline_events.forEach(event => {
        const time = event.timestamp ? event.timestamp.substring(11, 23) : 'N/A';
        markdown += `| **${time}** | **${event.service}** | ${event.operation} | **${event.target_service}** | ${event.details || ''} |\n`;
    });
    
    // Performance Analysis
    if (timelineData.performance_metrics) {
        markdown += `\n---\n\n## 📊 PERFORMANCE ANALYSIS\n\n`;
        markdown += `### Overall Metrics\n`;
        markdown += `- **Total Flow Duration:** ${timelineData.performance_metrics.total_duration_ms ? (timelineData.performance_metrics.total_duration_ms / 1000).toFixed(2) + 's' : 'N/A'}\n`;
        markdown += `- **Number of Operations:** ${timelineData.total_events}\n`;
        markdown += `- **Services Involved:** ${timelineData.services_involved}\n\n`;
        
        // Bottlenecks
        markdown += `### Bottlenecks Identified\n`;
        if (timelineData.performance_metrics.bottlenecks && timelineData.performance_metrics.bottlenecks.length > 0) {
            timelineData.performance_metrics.bottlenecks.forEach(bottleneck => {
                markdown += `- **${bottleneck.service}** - ${bottleneck.operation}: ${bottleneck.duration_ms}ms ⚠️\n`;
            });
        } else {
            markdown += `- No significant bottlenecks detected (all operations < 100ms) ✅\n`;
        }
        
        // Service Performance
        if (timelineData.performance_metrics.service_counts) {
            markdown += `\n### Service Performance\n`;
            Object.entries(timelineData.performance_metrics.service_counts).forEach(([service, count]) => {
                markdown += `- **${service}:** ${count} operations\n`;
            });
        }
        
        markdown += `\n---\n\n## 🎯 ANALYSIS SUMMARY\n\n`;
        markdown += `**Status:** ${timelineData.performance_metrics.status === 'SUCCESS' ? '✅ SUCCESS' : '❌ INCOMPLETE'}\n`;
        markdown += `**Critical Path:** STYX → JOVE → HERCULES → External Services\n\n`;
        markdown += `---\n\n*Generated by Scalar Project Timeline Analyzer*\n`;
    }
    
    // Download the markdown file
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `timeline_analysis_${timelineData.app_uuid ? timelineData.app_uuid.substring(0, 8) : 'unknown'}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast('Timeline report exported successfully!', 'success');
}

function copyTimelineData() {
    if (!analyzerState.currentFlowData || !analyzerState.currentFlowData.timeline_analysis) {
        showToast('No timeline data available to copy', 'error');
        return;
    }
    
    const timelineData = analyzerState.currentFlowData.timeline_analysis;
    let text = `Timeline Analysis for ${timelineData.app_uuid}\n`;
    text += `Total Events: ${timelineData.total_events}, Services: ${timelineData.services_involved}\n\n`;
    
    timelineData.timeline_events.forEach(event => {
        const time = event.timestamp ? event.timestamp.substring(11, 23) : 'N/A';
        text += `${time} | ${event.service} | ${event.operation} | ${event.target_service} | ${event.details || ''}\n`;
    });
    
    navigator.clipboard.writeText(text).then(() => {
        showToast('Timeline data copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy timeline data', 'error');
    });
}

function openSequenceDiagram() {
    if (!analyzerState.currentFlowData || !analyzerState.currentFlowData.timeline_analysis || !analyzerState.currentFlowData.timeline_analysis.sequence_diagram) {
        showToast('No sequence diagram available', 'error');
        return;
    }
    
    try {
        const diagram = analyzerState.currentFlowData.timeline_analysis.sequence_diagram;
        const cleanDiagram = diagram.replace(/```mermaid\n?/g, '').replace(/```\n?$/g, '').trim();
        
        const win = window.open('', '_blank');
        const doc = win.document;
        
        doc.open();
        doc.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Service Interaction Flow - Sequence Diagram</title>
                <style>
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background: #f8f9fa;
                        color: #333;
                    }
                    .container {
                        max-width: 1000px;
                        margin: 0 auto;
                        background: white;
                        padding: 30px;
                        border-radius: 12px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    }
                    h1 {
                        text-align: center;
                        color: #2c3e50;
                        margin-bottom: 10px;
                        font-size: 28px;
                    }
                    .subtitle {
                        text-align: center;
                        color: #7f8c8d;
                        margin-bottom: 30px;
                        font-size: 16px;
                    }
                    .usage-info {
                        background: #e8f4fd;
                        border: 1px solid #bee5eb;
                        border-radius: 8px;
                        padding: 20px;
                        margin-bottom: 25px;
                    }
                    .usage-info h3 {
                        color: #0c5460;
                        margin-top: 0;
                        margin-bottom: 15px;
                        font-size: 18px;
                    }
                    .usage-info p {
                        margin: 10px 0;
                        line-height: 1.6;
                    }
                    .usage-info a {
                        color: #007bff;
                        text-decoration: none;
                        font-weight: 600;
                        font-size: 16px;
                    }
                    .usage-info a:hover {
                        text-decoration: underline;
                    }
                    .code-container {
                        background: #2d3748;
                        color: #e2e8f0;
                        padding: 20px;
                        border-radius: 8px;
                        font-family: 'Courier New', monospace;
                        font-size: 14px;
                        line-height: 1.5;
                        overflow-x: auto;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                    }
                    .copy-btn {
                        background: #007bff;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 6px;
                        cursor: pointer;
                        font-size: 14px;
                        margin-top: 15px;
                        transition: background-color 0.2s;
                    }
                    .copy-btn:hover {
                        background: #0056b3;
                    }
                    .footer {
                        text-align: center;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #dee2e6;
                        color: #6c757d;
                        font-size: 14px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🔄 Service Interaction Flow</h1>
                    <p class="subtitle">Sequence Diagram Code</p>
                    
                    <div class="usage-info">
                        <h3>📊 How to Use This Diagram</h3>
                        <p><strong>Option 1:</strong> Copy the code below and paste it into <a href="https://sequencediagram.org/" target="_blank">https://sequencediagram.org/</a></p>
                        <p><strong>Option 2:</strong> Use any Mermaid-compatible editor or documentation tool</p>
                        <p><strong>Option 3:</strong> Integrate into your documentation using Mermaid syntax</p>
                    </div>
                    
                    <div class="code-container" id="diagramCode">${cleanDiagram}</div>
                    
                    <button class="copy-btn" onclick="copyToClipboard()">📋 Copy Diagram Code</button>
                    
                    <div class="footer">
                        <p>Generated by Payload Scaler - Log Analyzer</p>
                        <p>For best results, use <a href="https://sequencediagram.org/" target="_blank">sequencediagram.org</a> to visualize this diagram</p>
                    </div>
                </div>
                
                <script>
                    function copyToClipboard() {
                        const code = document.getElementById('diagramCode').textContent;
                        navigator.clipboard.writeText(code).then(function() {
                            const btn = document.querySelector('.copy-btn');
                            const originalText = btn.textContent;
                            btn.textContent = '✅ Copied!';
                            btn.style.background = '#28a745';
                            setTimeout(function() {
                                btn.textContent = originalText;
                                btn.style.background = '#007bff';
                            }, 2000);
                        }).catch(function(err) {
                            alert('Failed to copy to clipboard. Please select and copy manually.');
                        });
                    }
                </script>
            </body>
            </html>
        `);
        doc.close();
        
        showToast('Sequence diagram code opened in new tab!', 'success');
    } catch (error) {
        console.error('Error opening sequence diagram:', error);
        showToast('Failed to open sequence diagram', 'error');
    }
}

function copyAsciiDiagram() {
    const asciiElement = document.getElementById('asciiFlowDiagram');
    if (asciiElement) {
        const text = asciiElement.textContent;
        navigator.clipboard.writeText(text).then(() => {
            showToast('ASCII diagram copied to clipboard!', 'success');
        }).catch(err => {
            console.error('Failed to copy ASCII diagram:', err);
            showToast('Failed to copy ASCII diagram', 'error');
        });
    }
}

function highlightFlowStep(stepIndex) {
    // Remove previous highlights
    document.querySelectorAll('.flow-step').forEach(step => {
        step.classList.remove('highlighted');
    });
    
    // Add highlight to clicked step
    const clickedStep = document.querySelector(`[data-step="${stepIndex}"]`);
    if (clickedStep) {
        clickedStep.classList.add('highlighted');
        
        // Show step details in a toast
        const serviceName = clickedStep.querySelector('div').textContent;
        const timing = clickedStep.querySelector('div:last-child').textContent;
        showToast(`Step ${stepIndex + 1}: ${serviceName} ${timing}`, 'info', 3000);
    }
}

function startLiveFlowVisualization() {
    // Simulate live updates to the flow diagram
    const flowSteps = document.querySelectorAll('.flow-step');
    let currentStep = 0;
    
    const animateStep = () => {
        if (currentStep < flowSteps.length) {
            // Remove previous highlights
            flowSteps.forEach(step => step.classList.remove('highlighted'));
            
            // Highlight current step
            flowSteps[currentStep].classList.add('highlighted');
            
            currentStep++;
            setTimeout(animateStep, 1000); // Move to next step after 1 second
        } else {
            // Reset and start over
            setTimeout(() => {
                currentStep = 0;
                animateStep();
            }, 3000); // Wait 3 seconds before restarting
        }
    };
    
    // Start the animation
    setTimeout(animateStep, 1000);
}

function showServiceDetails(serviceName) {
    if (!analyzerState.flowData) return;
    
    const service = analyzerState.flowData.services.find(s => s.name === serviceName);
    if (!service) return;
    
    const detailsContainer = document.getElementById('analyzerServiceDetails');
    detailsContainer.innerHTML = `
        <div class="row g-3">
            <div class="col-md-6">
                <h6><i class="bi bi-gear"></i> ${service.name}</h6>
                <table class="table table-sm table-dark">
                    <tr><td>Operation:</td><td>${service.operation}</td></tr>
                    <tr><td>Status:</td><td><span class="badge bg-${service.status === 'success' ? 'success' : service.status === 'error' ? 'danger' : 'warning'}">${service.status}</span></td></tr>
                    <tr><td>Duration:</td><td>${service.duration}ms</td></tr>
                    <tr><td>Start Time:</td><td>${service.start_time}</td></tr>
                    <tr><td>End Time:</td><td>${service.end_time}</td></tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6><i class="bi bi-list-ul"></i> Interactions</h6>
                <div style="max-height: 200px; overflow-y: auto;">
                    ${service.interactions ? service.interactions.map(interaction => `
                        <div class="mb-2 p-2" style="background: rgba(255,255,255,0.05); border-radius: 4px;">
                            <small><strong>${interaction.type}:</strong> ${interaction.description}</small>
                            <br><small class="text-muted">${interaction.timestamp}</small>
                        </div>
                    `).join('') : '<small class="text-muted">No detailed interactions available</small>'}
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('analyzerDetailsSection').style.display = 'block';
}

function resetFlowZoom() {
    // Placeholder for zoom reset functionality
    showToast('Zoom reset (placeholder)', 'info');
}

function exportFlowDiagram() {
    if (!analyzerState.flowData) {
        showToast('No flow data to export', 'warning');
        return;
    }
    
    // Create a simple JSON export
    const exportData = {
        application_uuid: analyzerState.selectedApp,
        flow_data: analyzerState.flowData,
        exported_at: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `flow_diagram_${analyzerState.selectedApp}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast('Flow diagram exported successfully!', 'success');
}

function renderTimelineAnalysis(timelineData) {
    const container = document.getElementById('timeline-analysis-section');
    console.log('Timeline container found:', !!container);
    console.log('Timeline data provided:', !!timelineData);
    
    if (!container) {
        console.error('Timeline analysis section not found in DOM!');
        return;
    }
    if (!timelineData) {
        console.error('No timeline data provided!');
        return;
    }
    
    console.log('Timeline data received:', timelineData);
    
    // Update summary statistics
    const totalEvents = timelineData.events ? timelineData.events.length : 0;
    const servicesInvolved = timelineData.service_counts ? Object.keys(timelineData.service_counts).length : 0;
    const referenceIds = timelineData.reference_ids ? Object.keys(timelineData.reference_ids).length : 0;
    
    const totalEventsEl = document.getElementById('total-events');
    const servicesInvolvedEl = document.getElementById('services-involved');
    const referenceIdsEl = document.getElementById('reference-ids');
    
    if (totalEventsEl) totalEventsEl.textContent = totalEvents;
    if (servicesInvolvedEl) servicesInvolvedEl.textContent = servicesInvolved;
    if (referenceIdsEl) referenceIdsEl.textContent = referenceIds;
    
    // Update performance metrics
    if (timelineData.performance_metrics) {
        const metrics = timelineData.performance_metrics;
        const totalDurationEl = document.getElementById('total-duration');
        const avgIntervalEl = document.getElementById('avg-event-interval');
        const peakServiceEl = document.getElementById('peak-activity-service');
        
        if (totalDurationEl) totalDurationEl.textContent = `${metrics.total_duration || 0}ms`;
        if (avgIntervalEl) avgIntervalEl.textContent = `${(metrics.total_duration / Math.max(totalEvents - 1, 1)).toFixed(1) || 0}ms`;
        if (peakServiceEl) {
            // Find service with most events
            const peakService = timelineData.service_counts ? 
                Object.entries(timelineData.service_counts).reduce((a, b) => a[1] > b[1] ? a : b)[0] : 'N/A';
            peakServiceEl.textContent = peakService;
        }
    }
    
    // Render timeline events table (show all events with scrollable container)
    const tableBody = document.getElementById('timeline-events-body');
    if (tableBody && timelineData.events) {
        // Show all events with row numbers
        tableBody.innerHTML = timelineData.events.map((event, index) => `
            <tr>
                <td class="text-white small" style="font-family: monospace; font-weight: 500;">${index + 1}</td>
                <td>${event.timestamp ? event.timestamp.substring(11, 23) : 'N/A'}</td>
                <td><span class="badge bg-primary">${event.service || 'Unknown'}</span></td>
                <td>${event.operation || 'N/A'}</td>
                <td>${event.details || 'N/A'}</td>
                <td>${event.target_service || 'N/A'}</td>
            </tr>
        `).join('');
        
        // Update timeline table info
        const tableInfo = document.getElementById('timeline-table-info');
        if (tableInfo) {
            tableInfo.innerHTML = `
                <i class="bi bi-table"></i> 
                <strong>${timelineData.events.length}</strong> total events | 
                <i class="bi bi-arrow-up-down"></i> Scroll to navigate through all rows
            `;
        }
        
        // Add scroll event listener to show visible row range
        const tableContainer = document.getElementById('timeline-table-container');
        const scrollIndicator = document.getElementById('scroll-position-indicator');
        const visibleRowsSpan = document.getElementById('visible-rows');
        
        if (tableContainer && scrollIndicator && visibleRowsSpan) {
            // Show the scroll indicator
            scrollIndicator.style.display = 'block';
            
            // Function to update visible row range
            const updateVisibleRows = () => {
                const containerHeight = tableContainer.clientHeight;
                const scrollTop = tableContainer.scrollTop;
                const rowHeight = 45; // Approximate row height
                const headerHeight = 45; // Header height
                
                const firstVisibleRow = Math.floor((scrollTop) / rowHeight) + 1;
                const visibleRowCount = Math.floor(containerHeight / rowHeight);
                const lastVisibleRow = Math.min(firstVisibleRow + visibleRowCount - 1, timelineData.events.length);
                
                visibleRowsSpan.textContent = `${firstVisibleRow}-${lastVisibleRow} of ${timelineData.events.length}`;
            };
            
            // Update on scroll
            tableContainer.addEventListener('scroll', updateVisibleRows);
            
            // Initial update
            setTimeout(updateVisibleRows, 100);
        }
        
        console.log(`Rendered ${timelineData.events.length} events in timeline table`);
    }
    
    // Show service counts summary
    const serviceCountsEl = document.getElementById('service-counts-summary');
    if (serviceCountsEl && timelineData.service_counts) {
        const countsHtml = Object.entries(timelineData.service_counts)
            .sort((a, b) => b[1] - a[1])
            .map(([service, count]) => `
                <span class="badge bg-secondary me-2 mb-1">${service}: ${count}</span>
            `).join('');
        serviceCountsEl.innerHTML = countsHtml;
    }
    
    // Show the timeline analysis section
    container.style.display = 'block';
    console.log('Timeline analysis section displayed');
    
    // Add View Sequence Diagram button if sequence diagram is available
    if (timelineData.sequence_diagram) {
        const sequenceBtn = document.getElementById('view-sequence-btn');
        if (sequenceBtn) {
            sequenceBtn.style.display = 'inline-block';
        }
    }
}

function exportTimelineData() {
    if (!analyzerState.currentFlowData || !analyzerState.currentFlowData.timeline_analysis) {
        showToast('No timeline data available', 'error');
        return;
    }
    
    const data = analyzerState.currentFlowData.timeline_analysis;
    const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json'
    });
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `timeline_analysis_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast('Timeline data exported successfully');
}

function copyTimelineData() {
    if (!analyzerState.currentFlowData || !analyzerState.currentFlowData.timeline_analysis) {
        showToast('No timeline data available', 'error');
        return;
    }
    
    const data = analyzerState.currentFlowData.timeline_analysis;
    navigator.clipboard.writeText(JSON.stringify(data, null, 2))
        .then(() => {
            showToast('Timeline data copied to clipboard');
        })
        .catch(err => {
            console.error('Failed to copy:', err);
            showToast('Failed to copy timeline data', 'error');
        });
}

function testTimelineSection() {
    console.log('Testing timeline section...');
    const container = document.getElementById('timeline-analysis-section');
    if (container) {
        // Force all possible CSS properties to make it visible
        container.style.display = 'block';
        container.style.visibility = 'visible';
        container.style.opacity = '1';
        container.style.position = 'relative';
        container.style.zIndex = '9999';
        container.style.backgroundColor = 'red'; // Make it obvious
        container.style.border = '5px solid yellow';
        container.style.padding = '20px';
        container.style.margin = '20px 0';
        container.style.width = '100%';
        container.style.height = 'auto';
        container.style.minHeight = '200px';
        
        console.log('Timeline section forced to show with red background');
        showToast('Timeline section should now be visible with red background', 'info');
        
        // Add some obvious content
        container.innerHTML = `
            <div style="background: white; color: black; padding: 20px; text-align: center;">
                <h2>🎉 TIMELINE SECTION IS NOW VISIBLE! 🎉</h2>
                <p>If you can see this, the timeline section is working!</p>
                <button class="btn btn-primary" onclick="openSequenceDiagram()">
                    View Sequence Diagram
                </button>
            </div>
        `;
        
        // Test with dummy data
        const dummyData = {
            events: [
                {timestamp: '2026-01-22T10:00:00Z', service: 'TEST', operation: 'Test Operation', details: 'Test details', target_service: 'Target'}
            ],
            service_counts: {TEST: 1},
            sequence_diagram: 'sequenceDiagram\n    participant TEST\n    TEST->>TEST: Test Message',
            performance_metrics: {total_duration: 1000}
        };
        
        // Store the dummy data for the sequence diagram
        if (!analyzerState.currentFlowData) {
            analyzerState.currentFlowData = {};
        }
        analyzerState.currentFlowData.timeline_analysis = dummyData;
        
        // Scroll to the timeline section
        container.scrollIntoView({ behavior: 'smooth' });
        
        console.log('Container position:', container.getBoundingClientRect());
        console.log('Container computed style:', window.getComputedStyle(container));
    } else {
        console.error('Timeline section not found!');
        showToast('Timeline section not found in DOM', 'error');
    }
}

// ================================
// UNIFIED DASHBOARD FUNCTIONS
// ================================

let dashboardState = {
    nodes: [],
    currentPage: 1,
    totalNodes: 0,
    loading: false,
    filters: {
        status: ['all'],
        owners: ['all'],
        clusters: ['all'],
        memory: ['all']
    },
    availableFilters: {
        owners: [],
        clusters: [],
        memoryRanges: ['small', 'medium', 'large']
    }
};

function initDashboard() {
    console.log('Dashboard initialized');
}

async function loadNodeDetails() {
    const poolId = document.getElementById('poolId').value.trim();
    const limit = document.getElementById('pageLimit').value;
    
    if (!poolId) {
        showToast('Please enter a Pool ID', 'error');
        return;
    }
    
    // Check if we have cached data for this pool
    const cachedData = loadPoolData(poolId);
    if (cachedData && cachedData.nodes) {
        const cacheAge = Date.now() - cachedData.timestamp;
        const cacheAgeMinutes = Math.floor(cacheAge / (1000 * 60));
        
        console.log(`Found cached data for pool ${poolId}, age: ${cacheAgeMinutes} minutes`);
        
        // Use cached data if it's less than 30 minutes old
        if (cacheAge < 30 * 60 * 1000) {
            console.log('Using cached pool data');
            dashboardState.currentPoolId = poolId;
            renderNodeDetails(cachedData.nodes);
            showToast(`Loaded ${cachedData.nodes.length} nodes from cache (${cacheAgeMinutes}m old)`, 'info');
            return;
        } else {
            console.log('Cache is too old, fetching fresh data');
        }
    }
    
    try {
        showNodeDetailsLoading(true);
        
        // Construct the Jarvis API URL
        const apiUrl = `https://jarvis.eng.nutanix.com/api/v2/pools/${poolId}/node_details`;
        const params = new URLSearchParams({
            '_dc': Date.now(),
            'page': 1,
            'start': 0,
            'limit': limit
        });
        
        console.log('Fetching node details from:', `${apiUrl}?${params}`);
        
        // Make the API call through our backend to avoid CORS issues
        const response = await fetch('/api/dashboard/node-details', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pool_id: poolId,
                limit: parseInt(limit),
                page: 1,
                start: 0
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            dashboardState.nodes = data.nodes || [];
            dashboardState.totalNodes = data.total || 0;
            dashboardState.currentPoolId = poolId;
            
            renderNodeDetails(dashboardState.nodes);
            updateDashboardStats(dashboardState.nodes);
            
            showToast(`Loaded ${dashboardState.nodes.length} nodes successfully!`, 'success');
        } else {
            throw new Error(data.error || 'Failed to fetch node details');
        }
        
    } catch (error) {
        console.error('Error loading node details:', error);
        showNodeDetailsError(error.message);
        showToast(`Failed to load nodes: ${error.message}`, 'error');
    } finally {
        showNodeDetailsLoading(false);
    }
}

function renderNodeDetails(nodes) {
    const grid = document.getElementById('nodeDetailsGrid');
    
    if (!grid) {
        console.error('Node details grid not found');
        return;
    }
    
    if (!nodes || nodes.length === 0) {
        grid.innerHTML = `
            <div class="col-12 text-center py-4">
                <i class="bi bi-server" style="font-size: 3rem; color: var(--text-muted);"></i>
                <p class="mt-2 text-muted">No nodes found</p>
            </div>
        `;
        return;
    }
    
    // Store nodes and render them
    allNodes = nodes;
    dashboardState.allNodes = nodes;
    
    // Save pool data to localStorage
    const poolId = dashboardState.currentPoolId || 'default';
    currentPoolId = poolId;
    savePoolData(poolId, nodes);
    
    // Load existing deployment mappings for this pool
    nodeDeploymentMap = loadDeploymentMappings(poolId);
    console.log(`Loaded ${Object.keys(nodeDeploymentMap).length} deployment mappings for pool ${poolId}`);
    
    // Populate filter options
    populateFilterOptions(nodes);
    
    // Simply render all nodes
    grid.innerHTML = nodes.map(node => createNodeCard(node)).join('');
    
    // Show RDM Integration Results if we have deployment mappings
    if (Object.keys(nodeDeploymentMap).length > 0) {
        displayRDMResultsFromMappings();
    }
}

// ================================
// SIMPLE WORKING FILTERS & PERSISTENT STORAGE
// ================================

let allNodes = [];
let nodeDeploymentMap = {}; // Store deployment IDs mapped to node names
let currentPoolId = null;

// Persistent storage keys
const STORAGE_KEYS = {
    POOL_DATA: 'dashboard_pool_data',
    DEPLOYMENT_MAPPINGS: 'dashboard_deployment_mappings',
    LAST_POOL_ID: 'dashboard_last_pool_id'
};

function toggleFilters() {
    const panel = document.getElementById('filterPanel');
    if (panel) {
        if (panel.style.display === 'none') {
            panel.style.display = 'block';
        } else {
            panel.style.display = 'none';
        }
    }
}

function populateFilterOptions(nodes) {
    if (!nodes || nodes.length === 0) return;
    
    // Get unique owners
    const owners = [...new Set(nodes.map(node => node.cluster_owner).filter(Boolean))].sort();
    const ownerSelect = document.getElementById('ownerFilter');
    if (ownerSelect) {
        ownerSelect.innerHTML = '<option value="">All Owners</option>' +
            owners.map(owner => `<option value="${owner}">${owner}</option>`).join('');
    }
    
    // Get unique clusters
    const clusters = [...new Set(nodes.map(node => node.cluster_name).filter(Boolean))].sort();
    const clusterSelect = document.getElementById('clusterFilter');
    if (clusterSelect) {
        clusterSelect.innerHTML = '<option value="">All Clusters</option>' +
            clusters.map(cluster => `<option value="${cluster}">${cluster}</option>`).join('');
    }
    
    // Get unique memory values
    const memoryValues = [...new Set(nodes.map(node => {
        if (!node.hardware || !node.hardware.mem) return null;
        const memStr = node.hardware.mem.toString();
        const memMatch = memStr.match(/(\d+(?:\.\d+)?)\s*GB/i);
        return memMatch ? parseInt(memMatch[1]) : null;
    }).filter(mem => mem !== null))].sort((a, b) => a - b);
    
    const memorySelect = document.getElementById('memoryFilter');
    if (memorySelect) {
        memorySelect.innerHTML = '<option value="">All Memory</option>' +
            memoryValues.map(mem => `<option value="${mem}">${mem} GB</option>`).join('');
    }
}

function getMemoryValue(node) {
    if (!node.hardware || !node.hardware.mem) return null;
    
    // Parse memory string like "540 GB" or "270 GB"
    const memStr = node.hardware.mem.toString();
    const memMatch = memStr.match(/(\d+(?:\.\d+)?)\s*GB/i);
    if (!memMatch) return null;
    
    return parseInt(memMatch[1]);
}

function applyFilters() {
    if (!allNodes || allNodes.length === 0) return;
    
    const ownerFilter = document.getElementById('ownerFilter')?.value || '';
    const clusterFilter = document.getElementById('clusterFilter')?.value || '';
    const memoryFilter = document.getElementById('memoryFilter')?.value || '';
    
    let filteredNodes = allNodes;
    
    // Apply owner filter
    if (ownerFilter) {
        filteredNodes = filteredNodes.filter(node => node.cluster_owner === ownerFilter);
    }
    
    // Apply cluster filter
    if (clusterFilter) {
        filteredNodes = filteredNodes.filter(node => node.cluster_name === clusterFilter);
    }
    
    // Apply memory filter
    if (memoryFilter) {
        filteredNodes = filteredNodes.filter(node => {
            const nodeMemory = getMemoryValue(node);
            return nodeMemory !== null && nodeMemory.toString() === memoryFilter;
        });
    }
    
    // Update grid
    const grid = document.getElementById('nodeDetailsGrid');
    if (grid) {
        if (filteredNodes.length === 0) {
            grid.innerHTML = `
                <div class="col-12 text-center py-4">
                    <i class="bi bi-funnel" style="font-size: 3rem; color: var(--text-muted);"></i>
                    <p class="mt-2 text-muted">No nodes match the current filters</p>
                    <button class="btn btn-sm btn-outline-primary" onclick="clearFilters()">
                        <i class="bi bi-x-circle"></i> Clear Filters
                    </button>
                </div>
            `;
        } else {
            grid.innerHTML = filteredNodes.map(node => createNodeCard(node)).join('');
        }
    }
}

function clearFilters() {
    document.getElementById('ownerFilter').value = '';
    document.getElementById('clusterFilter').value = '';
    document.getElementById('memoryFilter').value = '';
    applyFilters();
}

// ================================
// PERSISTENT STORAGE MANAGEMENT
// ================================

function savePoolData(poolId, nodes) {
    try {
        const poolData = getStoredPoolData();
        poolData[poolId] = {
            nodes: nodes,
            timestamp: Date.now(),
            lastUpdated: new Date().toISOString()
        };
        localStorage.setItem(STORAGE_KEYS.POOL_DATA, JSON.stringify(poolData));
        localStorage.setItem(STORAGE_KEYS.LAST_POOL_ID, poolId);
        console.log(`Saved pool data for ${poolId} with ${nodes.length} nodes`);
    } catch (error) {
        console.error('Error saving pool data:', error);
    }
}

function getStoredPoolData() {
    try {
        const data = localStorage.getItem(STORAGE_KEYS.POOL_DATA);
        return data ? JSON.parse(data) : {};
    } catch (error) {
        console.error('Error loading pool data:', error);
        return {};
    }
}

function loadPoolData(poolId) {
    try {
        const poolData = getStoredPoolData();
        if (poolData[poolId]) {
            console.log(`Loaded cached pool data for ${poolId} with ${poolData[poolId].nodes.length} nodes`);
            return poolData[poolId];
        }
        return null;
    } catch (error) {
        console.error('Error loading pool data:', error);
        return null;
    }
}

function saveDeploymentMappings(poolId, mappings) {
    try {
        const deploymentData = getStoredDeploymentMappings();
        deploymentData[poolId] = {
            mappings: mappings,
            timestamp: Date.now(),
            lastUpdated: new Date().toISOString()
        };
        localStorage.setItem(STORAGE_KEYS.DEPLOYMENT_MAPPINGS, JSON.stringify(deploymentData));
        console.log(`Saved deployment mappings for ${poolId} with ${Object.keys(mappings).length} nodes`);
    } catch (error) {
        console.error('Error saving deployment mappings:', error);
    }
}

function getStoredDeploymentMappings() {
    try {
        const data = localStorage.getItem(STORAGE_KEYS.DEPLOYMENT_MAPPINGS);
        return data ? JSON.parse(data) : {};
    } catch (error) {
        console.error('Error loading deployment mappings:', error);
        return {};
    }
}

function loadDeploymentMappings(poolId) {
    try {
        const deploymentData = getStoredDeploymentMappings();
        if (deploymentData[poolId]) {
            console.log(`Loaded cached deployment mappings for ${poolId} with ${Object.keys(deploymentData[poolId].mappings).length} nodes`);
            return deploymentData[poolId].mappings;
        }
        return {};
    } catch (error) {
        console.error('Error loading deployment mappings:', error);
        return {};
    }
}

function getLastPoolId() {
    try {
        return localStorage.getItem(STORAGE_KEYS.LAST_POOL_ID) || null;
    } catch (error) {
        console.error('Error getting last pool ID:', error);
        return null;
    }
}

function clearStoredData(poolId = null) {
    try {
        if (poolId) {
            // Clear specific pool data
            const poolData = getStoredPoolData();
            const deploymentData = getStoredDeploymentMappings();
            
            delete poolData[poolId];
            delete deploymentData[poolId];
            
            localStorage.setItem(STORAGE_KEYS.POOL_DATA, JSON.stringify(poolData));
            localStorage.setItem(STORAGE_KEYS.DEPLOYMENT_MAPPINGS, JSON.stringify(deploymentData));
            console.log(`Cleared stored data for pool ${poolId}`);
        } else {
            // Clear all data
            localStorage.removeItem(STORAGE_KEYS.POOL_DATA);
            localStorage.removeItem(STORAGE_KEYS.DEPLOYMENT_MAPPINGS);
            localStorage.removeItem(STORAGE_KEYS.LAST_POOL_ID);
            console.log('Cleared all stored data');
        }
    } catch (error) {
        console.error('Error clearing stored data:', error);
    }
}

function getStorageInfo() {
    const poolData = getStoredPoolData();
    const deploymentData = getStoredDeploymentMappings();
    const lastPoolId = getLastPoolId();
    
    return {
        pools: Object.keys(poolData),
        poolCount: Object.keys(poolData).length,
        deploymentPools: Object.keys(deploymentData),
        lastPoolId: lastPoolId,
        totalNodes: Object.values(poolData).reduce((sum, pool) => sum + (pool.nodes?.length || 0), 0),
        totalDeploymentMappings: Object.values(deploymentData).reduce((sum, pool) => sum + Object.keys(pool.mappings || {}).length, 0)
    };
}

// ================================
// RDM INTEGRATION
// ================================

async function fetchRDMLinks() {
    if (!allNodes || allNodes.length === 0) {
        showToast('No nodes loaded. Please load node details first.', 'warning');
        return;
    }
    
    const button = document.querySelector('button[onclick="fetchRDMLinks()"]');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="bi bi-hourglass-split"></i> Fetching...';
    button.disabled = true;
    
    try {
        // Extract node IDs from current nodes
        const nodeIds = allNodes
            .map(node => node._id?.$oid || node.id || node.uuid)
            .filter(id => id)
        
        if (nodeIds.length === 0) {
            showToast('No valid node IDs found in current data', 'error');
            return;
        }
        
        console.log('Fetching RDM data for node IDs:', nodeIds);
        
        // Step 1: Call RDM API to get busy resources
        const rdmResponse = await fetch('/api/rdm/busy-resources', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                node_pool: 'ncm_st',
                limit: 33,
                node_ids: nodeIds
            })
        });
        
        if (!rdmResponse.ok) {
            throw new Error(`RDM API failed: ${rdmResponse.status}`);
        }
        
        const rdmData = await rdmResponse.json();
        console.log('RDM Response:', rdmData);
        
        if (!rdmData.success || !rdmData.data || rdmData.data.length === 0) {
            showToast('No RDM data found for the selected nodes', 'info');
            return;
        }
        
        // Step 2: Store deployment mappings and show results
        console.log('RDM data retrieved successfully:', rdmData);
        
        // Step 3: Store deployment IDs against node names
        storeNodeDeploymentMapping(rdmData.data);
        
        // Step 4: Display results
        displayRDMResults(rdmData);
        showToast(`Successfully fetched RDM data for ${rdmData.data.length} resources with deployment links`, 'success');
        
    } catch (error) {
        console.error('Error fetching RDM links:', error);
        showToast(`Error fetching RDM links: ${error.message}`, 'error');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

function storeNodeDeploymentMapping(rdmResources) {
    // Load existing mappings for current pool
    const existingMappings = loadDeploymentMappings(currentPoolId || 'default');
    nodeDeploymentMap = { ...existingMappings };
    
    // Map node IDs to deployment IDs
    rdmResources.forEach(resource => {
        if (resource.node_id && resource.scheduled_deployment_id) {
            // Find the corresponding node name from allNodes
            const node = allNodes.find(n => 
                (n._id && n._id.$oid === resource.node_id) || 
                n.id === resource.node_id || 
                n.uuid === resource.node_id
            );
            
            if (node && node.name) {
                nodeDeploymentMap[node.name] = {
                    deployment_id: resource.scheduled_deployment_id,
                    cluster_name: resource.cluster_name,
                    deployment_status: resource.deployment_status,
                    node_id: resource.node_id,
                    lastUpdated: new Date().toISOString()
                };
                console.log(`Mapped node ${node.name} to deployment ${resource.scheduled_deployment_id}`);
            }
        }
    });
    
    // Save updated mappings to localStorage
    saveDeploymentMappings(currentPoolId || 'default', nodeDeploymentMap);
    
    console.log('Node deployment mapping updated and saved:', nodeDeploymentMap);
    
    // Refresh the node grid to show deployment buttons
    if (allNodes && allNodes.length > 0) {
        applyFilters(); // This will re-render the grid with deployment buttons
    }
    
    // Update the RDM Integration Results display
    displayRDMResultsFromMappings();
}

function displayRDMResultsFromMappings() {
    // Create RDM results from stored deployment mappings
    const mappingEntries = Object.entries(nodeDeploymentMap);
    
    if (mappingEntries.length === 0) {
        console.log('No deployment mappings to display');
        return;
    }
    
    let resultsHtml = `
        <div class="card-dark mt-3">
            <h6><i class="bi bi-link-45deg"></i> RDM Integration Results (from stored mappings)</h6>
            
            <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                <table class="table table-sm table-dark">
                    <thead>
                        <tr>
                            <th>Node Name</th>
                            <th>Cluster Name</th>
                            <th>Status</th>
                            <th>Deployment ID</th>
                            <th>RDM Link</th>
                        </tr>
                    </thead>
                    <tbody>
    `;
    
    mappingEntries.forEach(([nodeName, deploymentInfo]) => {
        const status = deploymentInfo.deployment_status || 'Unknown';
        const statusClass = status === 'SUCCESS' ? 'text-success' : 'text-warning';
        const deploymentId = deploymentInfo.deployment_id;
        const rdmLink = deploymentId ? `https://rdm.eng.nutanix.com/scheduled_deployments/${deploymentId}` : null;
        
        resultsHtml += `
            <tr>
                <td><strong>${nodeName}</strong></td>
                <td><small>${deploymentInfo.cluster_name || 'N/A'}</small></td>
                <td><span class="${statusClass}">${status}</span></td>
                <td><small>${deploymentId || 'N/A'}</small></td>
                <td>
                    ${rdmLink ? `
                        <a href="${rdmLink}" target="_blank" class="btn btn-xs btn-outline-warning" title="Open RDM Deployment">
                            <i class="bi bi-link-45deg"></i> Open
                        </a>
                    ` : '<span class="text-muted">No Link</span>'}
                </td>
            </tr>
        `;
    });
    
    resultsHtml += `
                    </tbody>
                </table>
            </div>
            
            <div class="mt-2 text-center">
                <small class="text-muted">
                    Showing ${mappingEntries.length} nodes with deployment mappings • 
                    Last updated: ${nodeDeploymentMap[mappingEntries[0][0]]?.lastUpdated ? 
                        new Date(nodeDeploymentMap[mappingEntries[0][0]].lastUpdated).toLocaleString() : 'Unknown'}
                </small>
            </div>
        </div>
    `;
    
    // Insert results after the node grid
    const nodeGrid = document.getElementById('nodeDetailsGrid');
    let existingResults = document.getElementById('rdmResults');
    if (existingResults) {
        existingResults.remove();
    }
    
    const resultsDiv = document.createElement('div');
    resultsDiv.id = 'rdmResults';
    resultsDiv.innerHTML = resultsHtml;
    nodeGrid.parentNode.insertBefore(resultsDiv, nodeGrid.nextSibling);
    
    console.log(`Displayed RDM results for ${mappingEntries.length} nodes from stored mappings`);
}

function displayRDMResults(rdmData) {
    // Create a simplified RDM results display with deployment links
    let resultsHtml = `
        <div class="card-dark mt-3">
            <h6><i class="bi bi-link-45deg"></i> RDM Integration Results</h6>
            
            <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                <table class="table table-sm table-dark">
                    <thead>
                        <tr>
                            <th>Node ID</th>
                            <th>Cluster Name</th>
                            <th>Status</th>
                            <th>Deployment ID</th>
                            <th>RDM Link</th>
                        </tr>
                    </thead>
                    <tbody>
    `;
    
    rdmData.data.forEach(resource => {
        const status = resource.is_free ? 'Free' : resource.deployment_status || 'Busy';
        const statusClass = resource.is_free ? 'text-success' : 
                           (resource.deployment_status === 'SUCCESS' ? 'text-success' : 'text-warning');
        
        const deploymentId = resource.scheduled_deployment_id;
        const rdmLink = deploymentId ? `https://rdm.eng.nutanix.com/scheduled_deployments/${deploymentId}` : null;
        
        resultsHtml += `
            <tr>
                <td><small>${resource.node_id || 'N/A'}</small></td>
                <td><small>${resource.cluster_name || 'N/A'}</small></td>
                <td><span class="${statusClass}">${status}</span></td>
                <td><small>${deploymentId || 'N/A'}</small></td>
                <td>
                    ${rdmLink ? `
                        <a href="${rdmLink}" target="_blank" class="btn btn-xs btn-outline-warning" title="Open RDM Deployment">
                            <i class="bi bi-link-45deg"></i> Open
                        </a>
                    ` : '<span class="text-muted">No Link</span>'}
                </td>
            </tr>
        `;
    });
    
    resultsHtml += `
                    </tbody>
                </table>
            </div>
            
            <div class="mt-2 text-center">
                <small class="text-muted">
                    Found ${rdmData.data.length} resources • 
                    ${rdmData.data.filter(r => r.scheduled_deployment_id).length} with deployment links
                </small>
            </div>
        </div>
    `;
    
    // Insert results after the node grid
    const nodeGrid = document.getElementById('nodeDetailsGrid');
    let existingResults = document.getElementById('rdmResults');
    if (existingResults) {
        existingResults.remove();
    }
    
    const resultsDiv = document.createElement('div');
    resultsDiv.id = 'rdmResults';
    resultsDiv.innerHTML = resultsHtml;
    nodeGrid.parentNode.insertBefore(resultsDiv, nodeGrid.nextSibling);
}


// Legacy function aliases for backward compatibility

function selectAllStatus() {
    const statusAll = document.getElementById('statusAll');
    const statusHealthy = document.getElementById('statusHealthy');
    const statusWarning = document.getElementById('statusWarning');
    const statusCritical = document.getElementById('statusCritical');
    
    if (statusAll) statusAll.checked = true;
    if (statusHealthy) statusHealthy.checked = false;
    if (statusWarning) statusWarning.checked = false;
    if (statusCritical) statusCritical.checked = false;
    
    updateStatusFilter();
}

function deselectAllStatus() {
    const statusAll = document.getElementById('statusAll');
    const statusHealthy = document.getElementById('statusHealthy');
    const statusWarning = document.getElementById('statusWarning');
    const statusCritical = document.getElementById('statusCritical');
    
    if (statusAll) statusAll.checked = false;
    if (statusHealthy) statusHealthy.checked = false;
    if (statusWarning) statusWarning.checked = false;
    if (statusCritical) statusCritical.checked = false;
    
    // Force to "All" if nothing is selected
    if (statusAll) statusAll.checked = true;
    updateStatusFilter();
}

// Old filter functions removed




function selectAllOwners() {
    const select = document.getElementById('ownerFilter');
    if (select) {
        for (let option of select.options) {
            option.selected = true;
        }
        applyFilters();
    }
}

function deselectAllOwners() {
    const select = document.getElementById('ownerFilter');
    if (select) {
        for (let option of select.options) {
            option.selected = false;
        }
        applyFilters();
    }
}

function selectAllClusters() {
    const select = document.getElementById('clusterFilter');
    if (select) {
        for (let option of select.options) {
            option.selected = true;
        }
        applyFilters();
    }
}

function deselectAllClusters() {
    const select = document.getElementById('clusterFilter');
    if (select) {
        for (let option of select.options) {
            option.selected = false;
        }
        applyFilters();
    }
}

function selectAllOwners() {
    const ownerSelect = document.getElementById('ownerFilter');
    if (!ownerSelect) {
        console.warn('Owner filter element not found');
        return;
    }
    for (let option of ownerSelect.options) {
        option.selected = true;
    }
    applyAllFilters();
}

function deselectAllOwners() {
    const ownerSelect = document.getElementById('ownerFilter');
    if (!ownerSelect) {
        console.warn('Owner filter element not found');
        return;
    }
    for (let option of ownerSelect.options) {
        option.selected = false;
    }
    applyAllFilters();
}

function selectAllClusters() {
    const clusterSelect = document.getElementById('clusterFilter');
    if (!clusterSelect) {
        console.warn('Cluster filter element not found');
        return;
    }
    for (let option of clusterSelect.options) {
        option.selected = true;
    }
    applyAllFilters();
}

function deselectAllClusters() {
    const clusterSelect = document.getElementById('clusterFilter');
    if (!clusterSelect) {
        console.warn('Cluster filter element not found');
        return;
    }
    for (let option of clusterSelect.options) {
        option.selected = false;
    }
    applyAllFilters();
}

function getMemoryCategory(node) {
    const memoryStr = node.hardware?.mem || '0';
    const memoryNum = parseFloat(memoryStr.replace(/[^0-9.]/g, ''));
    
    if (memoryNum < 500) {
        return 'small';
    } else if (memoryNum <= 1000) {
        return 'medium';
    } else {
        return 'large';
    }
}

function clearAllFilters() {
    try {
        // Reset status checkboxes
        const statusAll = document.getElementById('statusAll');
        if (statusAll) statusAll.checked = true;
        ['statusHealthy', 'statusWarning', 'statusCritical'].forEach(id => {
            const cb = document.getElementById(id);
            if (cb) cb.checked = false;
        });
        
        // Reset memory checkboxes
        const memoryAll = document.getElementById('memoryAll');
        if (memoryAll) memoryAll.checked = true;
        ['memorySmall', 'memoryMedium', 'memoryLarge'].forEach(id => {
            const cb = document.getElementById(id);
            if (cb) cb.checked = false;
        });
        
        // Clear dropdowns
        const ownerSelect = document.getElementById('ownerFilter');
        const clusterSelect = document.getElementById('clusterFilter');
        if (ownerSelect) {
            for (let option of ownerSelect.options) {
                option.selected = false;
            }
        }
        if (clusterSelect) {
            for (let option of clusterSelect.options) {
                option.selected = false;
            }
        }
        
        applyFilters();
        showToast('All filters cleared', 'info');
    } catch (error) {
        console.error('Error clearing filters:', error);
    }
}

function updateActiveFiltersDisplay() {
    const display = document.getElementById('activeFiltersDisplay');
    const activeFilters = [];
    
    // Status filters
    if (!dashboardState.filters.status.includes('all')) {
        activeFilters.push(...dashboardState.filters.status.map(status => 
            `<span class="badge bg-${status === 'healthy' ? 'success' : status === 'warning' ? 'warning' : 'danger'}">${status}</span>`
        ));
    }
    
    // Owner filters
    if (!dashboardState.filters.owners.includes('all')) {
        activeFilters.push(`<span class="badge bg-info">Owners: ${dashboardState.filters.owners.length}</span>`);
    }
    
    // Cluster filters
    if (!dashboardState.filters.clusters.includes('all')) {
        activeFilters.push(`<span class="badge bg-primary">Clusters: ${dashboardState.filters.clusters.length}</span>`);
    }
    
    // Memory filters
    if (!dashboardState.filters.memory.includes('all')) {
        const memoryLabels = {
            small: '< 500GB',
            medium: '500GB-1TB',
            large: '> 1TB'
        };
        activeFilters.push(...dashboardState.filters.memory.map(mem => 
            `<span class="badge bg-secondary">${memoryLabels[mem]}</span>`
        ));
    }
    
    if (activeFilters.length === 0) {
        display.innerHTML = '<span class="badge bg-secondary">None</span>';
    } else {
        display.innerHTML = activeFilters.join(' ');
    }
}

// Legacy function for backward compatibility
function filterNodes(nodes) {
    return applyAllFilters(nodes);
}

function getNodeStatus(node) {
    if (node.is_enabled) {
        // Check for warning conditions (case-insensitive)
        if (node.comment && node.comment.toLowerCase().includes('eol')) {
            return 'warning';
        }
        return 'healthy';
    } else {
        return 'critical';
    }
}

// Quick filter functions
function setQuickStatusFilter(status) {
    // Clear all filters first
    clearAllFilters();
    
    // Set specific status filter
    dashboardState.filters.status = [status];
    const statusAll = document.getElementById('statusAll');
    const statusSpecific = document.getElementById(`status${status.charAt(0).toUpperCase() + status.slice(1)}`);
    
    if (statusAll) statusAll.checked = false;
    if (statusSpecific) statusSpecific.checked = true;
    
    applyAllFilters();
}

// Legacy functions for backward compatibility
function filterNodesByStatus() {
    applyAllFilters();
}

function clearNodeFilter() {
    clearAllFilters();
}

// Debug function to analyze node status discrepancies
function debugNodeStatuses() {
    if (!dashboardState.allNodes) {
        console.log('No nodes loaded');
        return;
    }
    
    console.log('=== NODE STATUS DEBUG ===');
    console.log('Total nodes:', dashboardState.allNodes.length);
    
    const statusBreakdown = {
        healthy: [],
        warning: [],
        critical: []
    };
    
    dashboardState.allNodes.forEach((node, index) => {
        const status = getNodeStatus(node);
        statusBreakdown[status].push({
            index: index + 1,
            name: node.name,
            is_enabled: node.is_enabled,
            comment: node.comment || 'No comment',
            calculated_status: status
        });
    });
    
    console.log('Healthy nodes:', statusBreakdown.healthy.length, statusBreakdown.healthy);
    console.log('Warning nodes:', statusBreakdown.warning.length, statusBreakdown.warning);
    console.log('Critical nodes:', statusBreakdown.critical.length, statusBreakdown.critical);
    
    // Test filtering
    const healthyFiltered = filterNodes(dashboardState.allNodes).length;
    document.getElementById('nodeStatusFilter').value = 'healthy';
    console.log('Healthy filter result:', healthyFiltered);
    
    return statusBreakdown;
}

// Add to window for easy access in console
window.debugNodeStatuses = debugNodeStatuses;

// Keyboard shortcuts for filtering (when dashboard is active)
document.addEventListener('keydown', function(event) {
    // Only apply shortcuts when dashboard section is visible
    const dashboardSection = document.getElementById('dashboardSection');
    if (!dashboardSection || dashboardSection.classList.contains('section-hidden')) {
        return;
    }
    
    // Ctrl/Cmd + number keys for quick filtering
    if ((event.ctrlKey || event.metaKey) && !event.shiftKey && !event.altKey) {
        switch(event.key) {
            case '1':
                event.preventDefault();
                clearAllFilters();
                showToast('Showing all nodes', 'info');
                break;
            case '2':
                event.preventDefault();
                setQuickStatusFilter('healthy');
                showToast('Showing healthy nodes only', 'success');
                break;
            case '3':
                event.preventDefault();
                setQuickStatusFilter('warning');
                showToast('Showing warning nodes only', 'warning');
                break;
            case '4':
                event.preventDefault();
                setQuickStatusFilter('critical');
                showToast('Showing critical nodes only', 'error');
                break;
            case 'f':
                event.preventDefault();
                toggleAdvancedFilters();
                showToast('Toggled advanced filters', 'info');
                break;
        }
    }
    
    // Escape key to close filters
    if (event.key === 'Escape') {
        const panel = document.getElementById('advancedFiltersPanel');
        if (panel && panel.style.display !== 'none') {
            toggleAdvancedFilters();
        }
    }
});

function updateFilterInfo(filteredCount, totalCount) {
    const filterInfo = document.getElementById('nodeFilterInfo');
    if (filterInfo) {
        if (filteredCount === totalCount) {
            filterInfo.textContent = `Showing all ${totalCount} nodes`;
        } else {
            const filterValue = document.getElementById('nodeStatusFilter').value;
            const statusText = filterValue.charAt(0).toUpperCase() + filterValue.slice(1);
            filterInfo.textContent = `Showing ${filteredCount} of ${totalCount} nodes (${statusText} filter active)`;
        }
    }
    
    // Update filter badges
    updateFilterBadges();
}

function updateFilterBadges() {
    const badgesContainer = document.getElementById('nodeFilterBadges');
    if (!badgesContainer || !dashboardState.allNodes) {
        return;
    }
    
    const filterValue = document.getElementById('nodeStatusFilter').value;
    
    if (filterValue === 'all') {
        badgesContainer.innerHTML = '';
        return;
    }
    
    // Count nodes by status
    const statusCounts = {
        healthy: 0,
        warning: 0,
        critical: 0
    };
    
    dashboardState.allNodes.forEach(node => {
        const status = getNodeStatus(node);
        statusCounts[status]++;
    });
    
    // Show active filter badge
    const statusText = filterValue.charAt(0).toUpperCase() + filterValue.slice(1);
    const badgeColor = filterValue === 'healthy' ? 'success' : 
                      filterValue === 'warning' ? 'warning' : 'danger';
    
    badgesContainer.innerHTML = `
        <span class="badge bg-${badgeColor}">
            <i class="bi bi-funnel"></i> ${statusText}: ${statusCounts[filterValue]}
        </span>
        <button class="btn btn-sm btn-outline-secondary py-0 px-1" onclick="clearNodeFilter()" title="Clear filter">
            <i class="bi bi-x"></i>
        </button>
    `;
}

function getDeploymentButton(nodeName) {
    const deploymentInfo = nodeDeploymentMap[nodeName];
    
    console.log(`Getting deployment button for node: ${nodeName}, deploymentInfo:`, deploymentInfo);
    console.log('Current nodeDeploymentMap:', nodeDeploymentMap);
    
    if (deploymentInfo && deploymentInfo.deployment_id) {
        const deploymentUrl = `https://rdm.eng.nutanix.com/scheduled_deployments/${deploymentInfo.deployment_id}`;
        console.log(`Creating deployment button for ${nodeName} with URL: ${deploymentUrl}`);
        return `
            <button class="btn btn-sm btn-outline-warning" onclick="openDeploymentLink('${deploymentUrl}')" title="View Deployment: ${deploymentInfo.deployment_id}">
                <i class="bi bi-link-45deg"></i>
            </button>
        `;
    }
    
    console.log(`No deployment button for ${nodeName} - no deployment info found`);
    return ''; // No deployment button if no deployment ID
}

function openDeploymentLink(url) {
    window.open(url, '_blank');
    showToast('Opening deployment link in new tab', 'info');
}

function showStorageInfo() {
    const info = getStorageInfo();
    const poolData = getStoredPoolData();
    const deploymentData = getStoredDeploymentMappings();
    
    let infoHtml = `
        <div class="card-dark mt-3">
            <h6><i class="bi bi-database"></i> Persistent Storage Information</h6>
            
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-primary">Pool Data Cache</h6>
                    <ul class="list-unstyled small">
                        <li><strong>Cached Pools:</strong> ${info.poolCount}</li>
                        <li><strong>Total Nodes:</strong> ${info.totalNodes}</li>
                        <li><strong>Last Pool ID:</strong> ${info.lastPoolId || 'None'}</li>
                    </ul>
                    
                    ${info.pools.length > 0 ? `
                        <h6 class="text-info mt-3">Cached Pools:</h6>
                        <div class="small">
                            ${info.pools.map(poolId => {
                                const pool = poolData[poolId];
                                const age = Math.floor((Date.now() - pool.timestamp) / (1000 * 60));
                                return `
                                    <div class="d-flex justify-content-between align-items-center mb-1">
                                        <span>${poolId} (${pool.nodes.length} nodes)</span>
                                        <span class="text-muted">${age}m ago</span>
                                        <button class="btn btn-xs btn-outline-danger" onclick="clearStoredData('${poolId}')">
                                            <i class="bi bi-trash"></i>
                                        </button>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    ` : '<p class="text-muted small">No cached pools</p>'}
                </div>
                
                <div class="col-md-6">
                    <h6 class="text-warning">Deployment Mappings</h6>
                    <ul class="list-unstyled small">
                        <li><strong>Pools with Deployments:</strong> ${info.deploymentPools.length}</li>
                        <li><strong>Total Mappings:</strong> ${info.totalDeploymentMappings}</li>
                    </ul>
                    
                    ${info.deploymentPools.length > 0 ? `
                        <h6 class="text-info mt-3">Deployment Pools:</h6>
                        <div class="small">
                            ${info.deploymentPools.map(poolId => {
                                const pool = deploymentData[poolId];
                                const age = Math.floor((Date.now() - pool.timestamp) / (1000 * 60));
                                const mappingCount = Object.keys(pool.mappings).length;
                                return `
                                    <div class="d-flex justify-content-between align-items-center mb-1">
                                        <span>${poolId} (${mappingCount} nodes)</span>
                                        <span class="text-muted">${age}m ago</span>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    ` : '<p class="text-muted small">No deployment mappings</p>'}
                    
                    <div class="mt-3">
                        <button class="btn btn-sm btn-outline-danger" onclick="clearAllStoredData()">
                            <i class="bi bi-trash"></i> Clear All Cache
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Insert or update storage info
    let existingInfo = document.getElementById('storageInfo');
    if (existingInfo) {
        existingInfo.remove();
    }
    
    const nodeGrid = document.getElementById('nodeDetailsGrid');
    const infoDiv = document.createElement('div');
    infoDiv.id = 'storageInfo';
    infoDiv.innerHTML = infoHtml;
    nodeGrid.parentNode.insertBefore(infoDiv, nodeGrid.nextSibling);
    
    showToast('Storage information displayed', 'info');
}

function clearAllStoredData() {
    if (confirm('Are you sure you want to clear all cached data? This will remove all stored pool data and deployment mappings.')) {
        clearStoredData();
        showToast('All cached data cleared', 'success');
        
        // Refresh storage info if it's visible
        const storageInfo = document.getElementById('storageInfo');
        if (storageInfo) {
            showStorageInfo();
        }
    }
}

// Test function to add demo deployment mappings
function addDemoDeploymentMappings() {
    nodeDeploymentMap = {
        'demo-node-1': {
            deployment_id: '68db9ee17298f65bc645cb97',
            cluster_name: 'demo_cluster',
            deployment_status: 'SUCCESS'
        },
        'demo-node-2': {
            deployment_id: '68dcf3167298f6b5d750c848',
            cluster_name: 'demo_cluster_old',
            deployment_status: 'SUCCESS'
        },
        'demo-node-3': {
            deployment_id: '681d9d6b92fce9821163336e',
            cluster_name: 'demo_cluster',
            deployment_status: 'SUCCESS'
        }
    };
    
    console.log('Added demo deployment mappings:', nodeDeploymentMap);
    
    // Refresh the grid to show deployment buttons
    if (allNodes && allNodes.length > 0) {
        applyFilters();
    }
    
    showToast('Demo deployment mappings added! You should now see deployment link buttons.', 'success');
}

function createNodeCard(node) {
    // Extract important details from actual Jarvis API response structure
    const nodeName = node.name || 'Unknown Node';
    const nodeId = node._id?.$oid || 'N/A';
    const status = node.is_enabled ? 'Enabled' : 'Disabled';
    const clusterName = node.cluster_name || 'N/A';
    const clusterOwner = node.cluster_owner || 'N/A';
    const model = node.hardware?.model || 'N/A';
    const memory = node.hardware?.mem || 'N/A';
    const cpuCores = node.hardware?.cpu_cores || 'N/A';
    const cpuModel = node.hardware?.cpu || 'N/A';
    const position = node.hardware?.position || 'N/A';
    const serial = node.hardware?.serial || 'N/A';
    const creditEstimate = node.hardware?.credit_estimate || 0;
    const comment = node.comment || '';
    const networkGateway = node.network_gateway || 'N/A';
    
    // Calculate storage info
    const storage = node.hardware?.storage || [];
    const totalStorage = storage.reduce((total, disk) => {
        const sizeStr = disk.size || '0';
        const sizeNum = parseFloat(sizeStr.replace(/[^0-9.]/g, ''));
        return total + (sizeNum || 0);
    }, 0);
    
    // Format cluster creation date
    const createdAt = node.cluster_created_at?.$date ? 
        new Date(node.cluster_created_at.$date).toLocaleDateString() : 'N/A';
    
    // Determine status color and icon
    const statusColor = node.is_enabled ? 'success' : 'danger';
    const statusIcon = node.is_enabled ? 'check-circle' : 'x-circle';
    
    return `
        <div class="col-lg-4 col-md-6 mb-3 node-card-fade-in">
            <div class="card-dark h-100">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="mb-0">
                        <i class="bi bi-server me-2"></i>
                        ${nodeName}
                    </h6>
                    <span class="badge bg-${statusColor}">
                        <i class="bi bi-${statusIcon}"></i> ${status}
                    </span>
                </div>
                
                <div class="small text-muted mb-3">
                    <div><strong>Model:</strong> ${model}</div>
                    <div><strong>Position:</strong> ${position}</div>
                    <div><strong>Owner:</strong> ${clusterOwner}</div>
                    <div><strong>Created:</strong> ${createdAt}</div>
                </div>
                
                <!-- Hardware Specs -->
                <div class="mb-2">
                    <div class="d-flex justify-content-between small">
                        <span><i class="bi bi-cpu"></i> CPU Cores</span>
                        <span>${cpuCores}</span>
                    </div>
                </div>
                
                <div class="mb-2">
                    <div class="d-flex justify-content-between small">
                        <span><i class="bi bi-memory"></i> Memory</span>
                        <span>${memory}</span>
                    </div>
                </div>
                
                <div class="mb-2">
                    <div class="d-flex justify-content-between small">
                        <span><i class="bi bi-hdd"></i> Storage</span>
                        <span>${totalStorage.toFixed(1)} TB</span>
                    </div>
                </div>
                
                <div class="mb-3">
                    <div class="d-flex justify-content-between small">
                        <span><i class="bi bi-credit-card"></i> Credits</span>
                        <span class="badge bg-info">${creditEstimate}</span>
                    </div>
                </div>
                
                ${comment ? `<div class="mb-2"><small class="text-warning"><i class="bi bi-info-circle"></i> ${comment}</small></div>` : ''}
                
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-outline-primary flex-fill" onclick="viewNodeDetails('${nodeId}')">
                        <i class="bi bi-eye"></i> Details
                    </button>
                    ${getDeploymentButton(nodeName)}
                    <button class="btn btn-sm btn-outline-secondary" onclick="refreshSingleNode('${nodeId}')">
                        <i class="bi bi-arrow-clockwise"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}

function updateDashboardStats(nodes, filteredNodes = null) {
    const stats = calculateNodeStats(nodes);
    const filteredStats = filteredNodes ? calculateNodeStats(filteredNodes) : stats;
    
    // Update main stats (always show total stats)
    document.getElementById('totalNodes').textContent = stats.total;
    document.getElementById('healthyNodes').textContent = stats.healthy;
    document.getElementById('warningNodes').textContent = stats.warning;
    document.getElementById('criticalNodes').textContent = stats.critical;
    
    // Add filter indication to stats if filtered
    if (filteredNodes && filteredNodes.length !== nodes.length) {
        const filterValue = document.getElementById('nodeStatusFilter').value;
        
        // Highlight the active filter stat
        document.querySelectorAll('#dashboardStats .card-dark').forEach(card => {
            card.classList.remove('border-primary');
        });
        
        if (filterValue === 'healthy') {
            document.getElementById('healthyNodes').parentElement.classList.add('border-primary');
        } else if (filterValue === 'warning') {
            document.getElementById('warningNodes').parentElement.classList.add('border-primary');
        } else if (filterValue === 'critical') {
            document.getElementById('criticalNodes').parentElement.classList.add('border-primary');
        }
    } else {
        // Remove all highlights when showing all
        document.querySelectorAll('#dashboardStats .card-dark').forEach(card => {
            card.classList.remove('border-primary');
        });
    }
    
    // Show stats section
    document.getElementById('dashboardStats').style.display = 'flex';
}

function calculateNodeStats(nodes) {
    const stats = {
        total: nodes.length,
        healthy: 0,
        warning: 0,
        critical: 0
    };
    
    nodes.forEach(node => {
        const status = getNodeStatus(node);
        stats[status]++;
    });
    
    // Debug logging (only when needed)
    if (window.DEBUG_NODE_STATS) {
        console.log('Node stats calculation:', {
            total: stats.total,
            healthy: stats.healthy,
            warning: stats.warning,
            critical: stats.critical
        });
    }
    
    return stats;
}

function getStatusColor(status) {
    const statusLower = (status || '').toLowerCase();
    if (statusLower.includes('healthy') || statusLower.includes('ok') || statusLower.includes('normal')) {
        return 'success';
    } else if (statusLower.includes('warning') || statusLower.includes('degraded')) {
        return 'warning';
    } else if (statusLower.includes('critical') || statusLower.includes('error') || statusLower.includes('failed')) {
        return 'danger';
    }
    return 'secondary';
}

function getStatusIcon(status) {
    const statusLower = (status || '').toLowerCase();
    if (statusLower.includes('healthy') || statusLower.includes('ok') || statusLower.includes('normal')) {
        return 'check-circle';
    } else if (statusLower.includes('warning') || statusLower.includes('degraded')) {
        return 'exclamation-triangle';
    } else if (statusLower.includes('critical') || statusLower.includes('error') || statusLower.includes('failed')) {
        return 'x-circle';
    }
    return 'question-circle';
}

function getUsageColor(percentage) {
    if (percentage >= 90) return 'bg-danger';
    if (percentage >= 75) return 'bg-warning';
    if (percentage >= 50) return 'bg-info';
    return 'bg-success';
}

function formatUptime(uptime) {
    if (!uptime || uptime === 0) return 'N/A';
    
    const seconds = parseInt(uptime);
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) {
        return `${days}d ${hours}h`;
    } else if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else {
        return `${minutes}m`;
    }
}

function showNodeDetailsLoading(show) {
    document.getElementById('nodeDetailsLoading').style.display = show ? 'block' : 'none';
    document.getElementById('nodeDetailsError').style.display = 'none';
}

function showNodeDetailsError(message) {
    document.getElementById('nodeDetailsError').style.display = 'block';
    document.getElementById('nodeDetailsErrorMessage').textContent = message;
    document.getElementById('nodeDetailsLoading').style.display = 'none';
}

function refreshNodeDetails() {
    loadNodeDetails();
}

function refreshSingleNode(nodeId) {
    showToast(`Refreshing node ${nodeId.substring(0, 8)}...`, 'info');
    // For now, just refresh all nodes
    refreshNodeDetails();
}

function viewNodeDetails(nodeId) {
    console.log('viewNodeDetails called with nodeId:', nodeId);
    
    // Use allNodes if available (after filtering), otherwise use nodes
    const nodeArray = dashboardState.allNodes || dashboardState.nodes;
    console.log('Available nodes:', nodeArray?.length || 0);
    
    if (!nodeArray || nodeArray.length === 0) {
        console.error('No nodes available');
        showToast('No node data available', 'error');
        return;
    }
    
    const node = nodeArray.find(n => (n._id?.$oid || n.id || n.uuid) === nodeId);
    console.log('Found node:', node ? node.name : 'Not found');
    
    if (node) {
        // Create a modal or detailed view
        showNodeDetailModal(node);
    } else {
        console.error('Node not found:', nodeId);
        console.log('Available node IDs:', nodeArray.map(n => n._id?.$oid || n.id || n.uuid));
        showToast('Node details not found', 'error');
    }
}

function showNodeDetailModal(node) {
    const storage = node.hardware?.storage || [];
    const storageDetails = storage.map(disk => 
        `${disk.model || 'Unknown'} (${disk.type || 'Unknown'}) - ${disk.size || 'Unknown'}`
    ).join('<br>');
    
    const createdAt = node.cluster_created_at?.$date ? 
        new Date(node.cluster_created_at.$date).toLocaleString() : 'N/A';
    
    const modalContent = `
        <div class="modal fade" id="nodeDetailModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content bg-dark text-white">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-server"></i> ${node.name || 'Unknown Node'}
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6><i class="bi bi-info-circle"></i> Basic Information</h6>
                                <table class="table table-dark table-sm">
                                    <tr><td><strong>Name:</strong></td><td>${node.name || 'N/A'}</td></tr>
                                    <tr><td><strong>ID:</strong></td><td>${node._id?.$oid || 'N/A'}</td></tr>
                                    <tr><td><strong>Status:</strong></td><td><span class="badge bg-${node.is_enabled ? 'success' : 'danger'}">${node.is_enabled ? 'Enabled' : 'Disabled'}</span></td></tr>
                                    <tr><td><strong>Owner:</strong></td><td>${node.cluster_owner || 'N/A'}</td></tr>
                                    <tr><td><strong>Cluster:</strong></td><td>${node.cluster_name || 'N/A'}</td></tr>
                                    <tr><td><strong>Created:</strong></td><td>${createdAt}</td></tr>
                                    <tr><td><strong>Gateway:</strong></td><td>${node.network_gateway || 'N/A'}</td></tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h6><i class="bi bi-cpu"></i> Hardware Specifications</h6>
                                <table class="table table-dark table-sm">
                                    <tr><td><strong>Model:</strong></td><td>${node.hardware?.model || 'N/A'}</td></tr>
                                    <tr><td><strong>Serial:</strong></td><td>${node.hardware?.serial || 'N/A'}</td></tr>
                                    <tr><td><strong>Position:</strong></td><td>${node.hardware?.position || 'N/A'}</td></tr>
                                    <tr><td><strong>CPU:</strong></td><td>${node.hardware?.cpu || 'N/A'}</td></tr>
                                    <tr><td><strong>CPU Cores:</strong></td><td>${node.hardware?.cpu_cores || 'N/A'}</td></tr>
                                    <tr><td><strong>CPU Sockets:</strong></td><td>${node.hardware?.num_cpu_sockets || 'N/A'}</td></tr>
                                    <tr><td><strong>Memory:</strong></td><td>${node.hardware?.mem || 'N/A'}</td></tr>
                                    <tr><td><strong>Credits:</strong></td><td>${node.hardware?.credit_estimate || 0}</td></tr>
                                </table>
                            </div>
                        </div>
                        
                        <div class="row mt-3">
                            <div class="col-12">
                                <h6><i class="bi bi-hdd"></i> Storage Details</h6>
                                <div class="table-responsive">
                                    <table class="table table-dark table-sm">
                                        <thead>
                                            <tr>
                                                <th>Disk</th>
                                                <th>Model</th>
                                                <th>Type</th>
                                                <th>Size</th>
                                                <th>Serial</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${storage.map(disk => `
                                                <tr>
                                                    <td>${disk.disk || 'N/A'}</td>
                                                    <td>${disk.model || 'N/A'}</td>
                                                    <td><span class="badge bg-${disk.type === 'SSD' ? 'success' : disk.type === 'NVMe' ? 'primary' : 'secondary'}">${disk.type || 'Unknown'}</span></td>
                                                    <td>${disk.size || 'N/A'}</td>
                                                    <td><small>${disk.serial || 'N/A'}</small></td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                        
                        ${node.static_vlans && node.static_vlans.length > 0 ? `
                        <div class="row mt-3">
                            <div class="col-12">
                                <h6><i class="bi bi-network"></i> Network VLANs</h6>
                                <div class="d-flex flex-wrap gap-2">
                                    ${node.static_vlans.map(vlan => `<span class="badge bg-info">${vlan}</span>`).join('')}
                                </div>
                            </div>
                        </div>
                        ` : ''}
                        
                        ${node.comment ? `
                        <div class="row mt-3">
                            <div class="col-12">
                                <h6><i class="bi bi-chat-text"></i> Comments</h6>
                                <div class="alert alert-info">${node.comment}</div>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" onclick="exportSingleNodeData('${node._id?.$oid}')">
                            <i class="bi bi-download"></i> Export Details
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if present
    const existingModal = document.getElementById('nodeDetailModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalContent);
    
    // Show modal
    try {
        const modalElement = document.getElementById('nodeDetailModal');
        if (!modalElement) {
            console.error('Modal element not found after creation');
            showToast('Failed to create modal', 'error');
            return;
        }
        
        console.log('Creating Bootstrap modal for node:', node.name);
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        console.log('Modal should be visible now');
    } catch (error) {
        console.error('Error showing modal:', error);
        showToast('Failed to show node details', 'error');
    }
}

function exportNodeData() {
    if (dashboardState.nodes.length === 0) {
        showToast('No node data to export', 'warning');
        return;
    }
    
    const csvData = convertNodesToCSV(dashboardState.nodes);
    downloadCSV(csvData, `node-details-${new Date().toISOString().split('T')[0]}.csv`);
    showToast('Node data exported successfully!', 'success');
}

function convertNodesToCSV(nodes) {
    const headers = ['Name', 'ID', 'Model', 'Status', 'Owner', 'Cluster', 'CPU Cores', 'Memory', 'Storage TB', 'Credits', 'Position', 'Gateway', 'Comment'];
    const rows = nodes.map(node => {
        const storage = node.hardware?.storage || [];
        const totalStorage = storage.reduce((total, disk) => {
            const sizeStr = disk.size || '0';
            const sizeNum = parseFloat(sizeStr.replace(/[^0-9.]/g, ''));
            return total + (sizeNum || 0);
        }, 0);
        
        return [
            node.name || 'Unknown',
            node._id?.$oid || 'N/A',
            node.hardware?.model || 'N/A',
            node.is_enabled ? 'Enabled' : 'Disabled',
            node.cluster_owner || 'N/A',
            node.cluster_name || 'N/A',
            node.hardware?.cpu_cores || 'N/A',
            node.hardware?.mem || 'N/A',
            totalStorage.toFixed(1),
            node.hardware?.credit_estimate || 0,
            node.hardware?.position || 'N/A',
            node.network_gateway || 'N/A',
            node.comment || ''
        ];
    });
    
    return [headers, ...rows].map(row => row.map(field => `"${field}"`).join(',')).join('\n');
}

function downloadCSV(csvContent, filename) {
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// ================================
// DASHBOARD INITIALIZATION
// ================================


// Legacy function aliases for backward compatibility
function applyAllFilters() {
    applyFilters();
}

function filterNodes(nodes) {
    return dashboardState.allNodes || [];
}

function filterNodesByStatus() {
    applyFilters();
}

function clearNodeFilter() {
    clearAllFilters();
}

// Simple initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard filters ready');
});

// Clean up old functions - remove everything after this and keep only the simple ones above


function exportSingleNodeData(nodeId) {
    // Use allNodes if available (after filtering), otherwise use nodes
    const nodeArray = dashboardState.allNodes || dashboardState.nodes;
    const node = nodeArray.find(n => n._id?.$oid === nodeId);
    
    if (node) {
        const csvData = convertNodesToCSV([node]);
        downloadCSV(csvData, `node-${node.name || 'unknown'}-${new Date().toISOString().split('T')[0]}.csv`);
        showToast('Node data exported successfully!', 'success');
    } else {
        console.error('Node not found for export:', nodeId);
        showToast('Node not found for export', 'error');
    }
}
