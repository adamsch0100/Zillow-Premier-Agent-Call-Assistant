// Initialize application state
let state = {
    isCallActive: false,
    isRecording: false,
    currentStage: 'initial',
    selectedSuggestionType: 'all',
    keyInfo: new Set(),
    actionItems: new Set(),
    settings: {
        autoRecord: false,
        notificationVolume: 0.5,
        keyboardShortcuts: true
    }
};

// Initialize components
const wsClient = new WebSocketClient();
const speechProcessor = new SpeechProcessor(wsClient);
const responseMatcher = new ResponseMatcher();

// Event handler registration
document.addEventListener('DOMContentLoaded', initializeApp);
document.addEventListener('keydown', handleKeyboardShortcuts);

// Initialize application
async function initializeApp() {
    try {
        // Connect WebSocket
        await wsClient.connect();
        
        // Initialize audio processing
        await initializeAudio();
        
        // Load settings
        loadSettings();
        
        // Set up event listeners
        setupEventListeners();
        
        // Initialize UI components
        initializeUI();
        
    } catch (error) {
        console.error('Error initializing app:', error);
        showNotification('Error initializing application', 'error');
    }
}

// Audio initialization
async function initializeAudio() {
    try {
        await speechProcessor.initialize();
        document.getElementById('start-call').disabled = false;
        showNotification('Audio system initialized', 'success');
    } catch (error) {
        console.error('Failed to initialize audio:', error);
        showNotification('Error: Could not access microphone', 'error');
        throw error;
    }
}

// Event listeners setup
function setupEventListeners() {
    // WebSocket events
    wsClient.on('transcription', handleTranscription);
    wsClient.on('suggestion', handleSuggestion);
    wsClient.on('almProgress', handleALMProgress);
    wsClient.on('callMetrics', handleCallMetrics);
    wsClient.on('error', handleError);
    wsClient.on('connection_failed', handleConnectionFailure);
    
    // DOM events
    document.getElementById('record-call').addEventListener('click', toggleRecording);
    document.getElementById('settings-toggle').addEventListener('click', toggleSettings);
    
    // Suggestion type filters
    document.querySelectorAll('[data-suggestion-type]').forEach(button => {
        button.addEventListener('click', () => {
            toggleSuggestionType(button.dataset.suggestionType);
        });
    });
}

// Call control functions
async function startCall() {
    if (!state.isCallActive) {
        try {
            state.isCallActive = true;
            updateCallStatus('active');
            
            // Start audio processing
            await speechProcessor.startProcessing();
            
            // Start recording if auto-record is enabled
            if (state.settings.autoRecord) {
                startRecording();
            }
            
            // Notify backend
            wsClient.startCall();
            
            // Start call timer
            startCallTimer();
            
            showNotification('Call started', 'success');
            
        } catch (error) {
            console.error('Error starting call:', error);
            showNotification('Error starting call', 'error');
            endCall();
        }
    } else {
        endCall();
    }
}

function endCall() {
    state.isCallActive = false;
    updateCallStatus('inactive');
    
    // Stop audio processing
    speechProcessor.stopProcessing();
    
    // Stop recording if active
    if (state.isRecording) {
        stopRecording();
    }
    
    // Notify backend
    wsClient.endCall();
    
    // Stop call timer
    stopCallTimer();
    
    // Save call summary
    saveCallSummary();
    
    showNotification('Call ended', 'info');
}

// Recording functions
function startRecording() {
    if (!state.isRecording) {
        state.isRecording = true;
        speechProcessor.startRecording();
        updateRecordingStatus(true);
        showNotification('Recording started', 'info');
    }
}

function stopRecording() {
    if (state.isRecording) {
        state.isRecording = false;
        speechProcessor.stopRecording();
        updateRecordingStatus(false);
        showNotification('Recording saved', 'success');
    }
}

function toggleRecording() {
    if (state.isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

// WebSocket message handlers
function handleTranscription(data) {
    try {
        const transcriptionDiv = document.getElementById('transcription');
        const entry = createTranscriptionEntry(data);
        transcriptionDiv.appendChild(entry);
        transcriptionDiv.scrollTop = transcriptionDiv.scrollHeight;
        
        // Update context and get suggestions
        responseMatcher.updateContext(data);
        const suggestions = responseMatcher.getSuggestions(data);
        updateSuggestionsUI(suggestions);
        
        // Update metrics
        const metrics = responseMatcher.getMetrics();
        updateMetricsUI(metrics);
        
        // Update key information
        updateKeyInformation(data);
        
    } catch (error) {
        console.error('Error handling transcription:', error);
    }
}

function handleSuggestion(data) {
    try {
        const filteredSuggestions = filterSuggestions(data.suggestions, state.selectedSuggestionType);
        updateSuggestionsUI(filteredSuggestions);
    } catch (error) {
        console.error('Error handling suggestions:', error);
    }
}

function handleALMProgress(data) {
    try {
        updateALMProgress(data);
        updateCallStage(data.currentStage);
    } catch (error) {
        console.error('Error handling ALM progress:', error);
    }
}

function handleCallMetrics(data) {
    try {
        updateMetricsUI(data);
        checkCallQualityAlerts(data);
    } catch (error) {
        console.error('Error handling call metrics:', error);
    }
}

// UI update functions
function updateCallStatus(status) {
    const statusElement = document.getElementById('call-status');
    const buttonElement = document.getElementById('start-call');
    
    const statusConfig = {
        active: {
            buttonText: 'End Call',
            statusClass: 'bg-green-500',
            statusText: 'Active Call'
        },
        inactive: {
            buttonText: 'Start Call',
            statusClass: 'bg-gray-500',
            statusText: 'Ready'
        }
    };
    
    const config = statusConfig[status];
    
    statusElement.className = `px-3 py-1 rounded-full ${config.statusClass}`;
    statusElement.textContent = config.statusText;
    buttonElement.textContent = config.buttonText;
}

function updateSuggestionsUI(suggestions) {
    const suggestionsDiv = document.getElementById('suggestions');
    suggestionsDiv.innerHTML = '';
    
    suggestions.forEach(suggestionGroup => {
        const groupDiv = createSuggestionGroup(suggestionGroup);
        suggestionsDiv.appendChild(groupDiv);
    });
}

function updateMetricsUI(metrics) {
    // Update basic metrics
    document.getElementById('rapport-score').textContent = metrics.rapport;
    document.getElementById('key-info').textContent = `${metrics.keyInfo}/5 Points`;
    document.getElementById('objections').textContent = `${metrics.objections} Handled`;
    document.getElementById('interest-level').textContent = metrics.interestLevel || '-';
    
    // Update progress bars
    updateProgressBar('qualification', metrics.qualificationProgress);
    updateProgressBar('needs', metrics.needsAssessmentProgress);
    updateProgressBar('appointment', metrics.appointmentProgress);
}

function updateProgressBar(id, value) {
    const progressElement = document.getElementById(`progress-${id}`);
    const barElement = document.getElementById(`progress-${id}-bar`);
    
    if (progressElement && barElement) {
        progressElement.textContent = `${Math.round(value)}%`;
        barElement.style.width = `${value}%`;
    }
}

// Utility functions
function showNotification(message, type = 'info') {
    const notificationArea = document.getElementById('notification-area');
    const notification = document.createElement('div');
    
    const typeClasses = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-blue-500',
        warning: 'bg-yellow-500'
    };
    
    notification.className = `notification ${typeClasses[type]} text-white px-4 py-2 rounded shadow-lg mb-2`;
    notification.textContent = message;
    
    notificationArea.appendChild(notification);
    
    // Remove notification after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function createTranscriptionEntry(data) {
    const entry = document.createElement('div');
    entry.className = 'p-2 rounded bg-gray-50 mb-2';
    
    const speakerClass = data.speaker === 'Agent' ? 'text-blue-600' : 'text-green-600';
    
    entry.innerHTML = `
        <div class="flex items-center justify-between">
            <span class="font-semibold ${speakerClass}">${data.speaker}</span>
            <span class="text-xs text-gray-500">${new Date().toLocaleTimeString()}</span>
        </div>
        <p class="mt-1">${data.text}</p>
    `;
    
    return entry;
}

function createSuggestionGroup(group) {
    const groupDiv = document.createElement('div');
    groupDiv.className = 'p-3 border-l-4 border-blue-500 bg-blue-50 mb-3';
    
    const title = document.createElement('h3');
    title.className = 'font-semibold';
    title.textContent = getSuggestionGroupTitle(group.type);
    
    const list = document.createElement('ul');
    list.className = 'mt-2 space-y-2';
    
    group.suggestions.forEach(suggestion => {
        const item = document.createElement('li');
        item.className = 'cursor-pointer hover:bg-blue-100 p-1 rounded flex items-center justify-between';
        
        const text = document.createElement('span');
        text.textContent = suggestion.text;
        
        const confidence = document.createElement('span');
        confidence.className = 'text-xs text-gray-500';
        confidence.textContent = `${Math.round(suggestion.confidence * 100)}%`;
        
        item.appendChild(text);
        item.appendChild(confidence);
        item.onclick = () => copySuggestion(suggestion.text);
        
        list.appendChild(item);
    });
    
    groupDiv.appendChild(title);
    groupDiv.appendChild(list);
    
    return groupDiv;
}

function getSuggestionGroupTitle(type) {
    const titles = {
        'appointment': 'Scheduling Suggestions',
        'location': 'Location Questions',
        'motivation': 'Motivation Discovery',
        'objection': 'Objection Handlers',
        'rapport': 'Rapport Building',
        'closing': 'Closing Statements'
    };
    return titles[type] || 'Suggested Responses';
}

// Keyboard shortcuts
function handleKeyboardShortcuts(event) {
    if (!state.settings.keyboardShortcuts) return;
    
    // Command/Control + S: Start/Stop Call
    if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        if (state.isCallActive) {
            endCall();
        } else {
            startCall();
        }
    }
    
    // Command/Control + R: Toggle Recording
    if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
        event.preventDefault();
        toggleRecording();
    }
    
    // Command/Control + K: Clear Transcription
    if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault();
        clearTranscription();
    }
}

// Settings management
function loadSettings() {
    const savedSettings = localStorage.getItem('agentAssistantSettings');
    if (savedSettings) {
        state.settings = { ...state.settings, ...JSON.parse(savedSettings) };
    }
    updateSettingsUI();
}

function saveSettings() {
    localStorage.setItem('agentAssistantSettings', JSON.stringify(state.settings));
    showNotification('Settings saved', 'success');
}

function updateSettingsUI() {
    // Update settings toggles and inputs based on state.settings
    Object.entries(state.settings).forEach(([key, value]) => {
        const element = document.querySelector(`[data-setting="${key}"]`);
        if (element) {
            if (element.type === 'checkbox') {
                element.checked = value;
            } else {
                element.value = value;
            }
        }
    });
}

// Call summary and analytics
async function saveCallSummary() {
    try {
        const summary = {
            duration: document.getElementById('call-duration').textContent,
            keyInfo: Array.from(state.keyInfo),
            actionItems: Array.from(state.actionItems),
            metrics: responseMatcher.getMetrics(),
            timestamp: new Date().toISOString()
        };
        
        // Send to backend for storage
        await wsClient.send({
            type: 'save_call_summary',
            payload: summary
        });
        
        showNotification('Call summary saved', 'success');
        
    } catch (error) {
        console.error('Error saving call summary:', error);
        showNotification('Error saving call summary', 'error');
    }
}

// Initialize the application
initializeApp();