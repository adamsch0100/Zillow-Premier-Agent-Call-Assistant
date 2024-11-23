class WebSocketClient {
    constructor(url = 'ws://localhost:8000/ws') {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.eventHandlers = new Map();
        this.connectionStatus = 'disconnected';
        this.pendingMessages = [];
        this.callActive = false;
        
        // Bind methods
        this.connect = this.connect.bind(this);
        this.reconnect = this.reconnect.bind(this);
        this.handleMessage = this.handleMessage.bind(this);
        this.handleClose = this.handleClose.bind(this);
        this.handleError = this.handleError.bind(this);
        
        // Initialize heartbeat
        this.heartbeatInterval = null;
        this.lastHeartbeat = null;
    }

    async connect() {
        try {
            this.ws = new WebSocket(this.url);
            this.setupEventListeners();
            this.updateConnectionStatus('connecting');
            
            return new Promise((resolve, reject) => {
                this.ws.addEventListener('open', () => {
                    this.onConnectionEstablished();
                    resolve();
                }, { once: true });
                
                this.ws.addEventListener('error', (error) => {
                    reject(error);
                }, { once: true });
                
                // Set connection timeout
                setTimeout(() => {
                    if (this.connectionStatus !== 'connected') {
                        reject(new Error('Connection timeout'));
                    }
                }, 5000);
            });
        } catch (error) {
            this.handleError(error);
            throw error;
        }
    }

    setupEventListeners() {
        this.ws.addEventListener('message', this.handleMessage);
        this.ws.addEventListener('close', this.handleClose);
        this.ws.addEventListener('error', this.handleError);
    }

    onConnectionEstablished() {
        this.connectionStatus = 'connected';
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.updateConnectionStatus('connected');
        this.startHeartbeat();
        
        // Send any pending messages
        while (this.pendingMessages.length > 0) {
            const message = this.pendingMessages.shift();
            this.send(message);
        }
    }

    async reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.updateConnectionStatus('failed');
            this.emit('connection_failed', {
                message: 'Maximum reconnection attempts reached'
            });
            return;
        }

        this.reconnectAttempts++;
        this.updateConnectionStatus('reconnecting');
        
        // Exponential backoff
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 30000);
        
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`);
        
        await new Promise(resolve => setTimeout(resolve, delay));
        
        try {
            await this.connect();
        } catch (error) {
            console.error('Reconnection failed:', error);
            this.reconnect();
        }
    }

    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                this.send({ type: 'heartbeat' });
                this.lastHeartbeat = Date.now();
                
                // Check if we've received a heartbeat response within 5 seconds
                setTimeout(() => {
                    if (Date.now() - this.lastHeartbeat > 5000) {
                        console.warn('Heartbeat timeout, reconnecting...');
                        this.ws.close();
                    }
                }, 5000);
            }
        }, 30000); // Send heartbeat every 30 seconds
    }

    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    updateConnectionStatus(status) {
        this.connectionStatus = status;
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            const statusMap = {
                'connecting': { text: 'Connecting...', class: 'bg-yellow-500' },
                'connected': { text: 'Connected', class: 'bg-green-500' },
                'reconnecting': { text: 'Reconnecting...', class: 'bg-yellow-500' },
                'disconnected': { text: 'Disconnected', class: 'bg-red-500' },
                'failed': { text: 'Connection Failed', class: 'bg-red-700' }
            };
            
            const status_info = statusMap[status] || statusMap['disconnected'];
            statusElement.textContent = status_info.text;
            statusElement.className = `px-3 py-1 rounded-full ${status_info.class}`;
        }
    }

    send(data) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify(data));
            } catch (error) {
                console.error('Error sending message:', error);
                this.pendingMessages.push(data);
            }
        } else {
            this.pendingMessages.push(data);
            if (this.connectionStatus !== 'connecting' && this.connectionStatus !== 'reconnecting') {
                this.reconnect();
            }
        }
    }

    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, new Set());
        }
        this.eventHandlers.get(event).add(handler);
    }

    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).delete(handler);
        }
    }

    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            for (const handler of this.eventHandlers.get(event)) {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            }
        }
    }

    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            // Handle heartbeat response
            if (data.type === 'heartbeat') {
                this.lastHeartbeat = Date.now();
                return;
            }
            
            // Handle other message types
            if (data.type && this.eventHandlers.has(data.type)) {
                this.emit(data.type, data.payload);
            }
            
            // Update audio quality indicators if present
            if (data.audioQuality) {
                this.updateAudioQualityIndicators(data.audioQuality);
            }
        } catch (error) {
            console.error('Error handling message:', error);
        }
    }

    handleClose(event) {
        this.stopHeartbeat();
        this.updateConnectionStatus('disconnected');
        
        if (this.callActive) {
            this.emit('call_interrupted', {
                message: 'Connection lost during active call'
            });
        }
        
        if (!event.wasClean) {
            console.warn(`WebSocket connection closed unexpectedly: ${event.code} ${event.reason}`);
            this.reconnect();
        }
    }

    handleError(error) {
        console.error('WebSocket error:', error);
        this.emit('error', {
            message: 'WebSocket error occurred',
            error: error
        });
    }

    updateAudioQualityIndicators(quality) {
        // Update signal strength visualization
        const signalStrength = document.getElementById('signal-strength');
        if (signalStrength) {
            const bars = signalStrength.getElementsByClassName('bar');
            const strength = Math.min(Math.floor(quality.signalStrength * 5), 5);
            
            for (let i = 0; i < bars.length; i++) {
                bars[i].style.opacity = i < strength ? '1' : '0.3';
            }
        }
        
        // Update noise level indicator
        const noiseLevel = document.getElementById('noise-level');
        if (noiseLevel) {
            const indicator = noiseLevel.getElementsByClassName('bg-green-500')[0];
            const percentage = Math.min(quality.noiseLevel * 100, 100);
            indicator.style.width = `${percentage}%`;
            
            // Update color based on noise level
            const colors = {
                low: 'bg-green-500',
                medium: 'bg-yellow-500',
                high: 'bg-red-500'
            };
            
            indicator.className = `h-full rounded ${
                percentage < 30 ? colors.low :
                percentage < 70 ? colors.medium :
                colors.high
            }`;
        }
    }

    // Call control methods
    startCall() {
        this.callActive = true;
        this.send({
            type: 'start_call',
            timestamp: new Date().toISOString()
        });
    }

    endCall() {
        this.callActive = false;
        this.send({
            type: 'end_call',
            timestamp: new Date().toISOString()
        });
    }

    // Audio processing methods
    sendAudioChunk(audioData) {
        if (this.callActive) {
            this.send({
                type: 'audio_chunk',
                payload: {
                    audio: audioData,
                    timestamp: new Date().toISOString()
                }
            });
        }
    }
}