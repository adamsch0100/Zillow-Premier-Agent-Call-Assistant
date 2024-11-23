class WebSocketManager {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.listeners = new Map();
    this.isConnected = false;
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.notifyListeners('connection', { status: 'connected' });
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.isConnected = false;
        this.notifyListeners('connection', { status: 'disconnected' });
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.notifyListeners('error', { error });
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
    }
  }

  handleMessage(data) {
    switch (data.type) {
      case 'suggestions':
        this.notifyListeners('suggestions', data.suggestions);
        break;
      case 'alm_update':
        this.notifyListeners('almUpdate', data.almStage);
        break;
      case 'transcription':
        this.notifyListeners('transcription', data.text);
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
      setTimeout(() => this.connect(), 2000 * this.reconnectAttempts);
    } else {
      console.error('Max reconnection attempts reached');
      this.notifyListeners('error', { 
        error: 'Failed to reconnect after maximum attempts' 
      });
    }
  }

  sendMessage(type, data) {
    if (!this.isConnected) {
      console.error('WebSocket is not connected');
      return;
    }

    try {
      const message = JSON.stringify({
        type,
        ...data,
        timestamp: new Date().toISOString()
      });
      this.ws.send(message);
    } catch (error) {
      console.error('Error sending message:', error);
    }
  }

  // Audio streaming methods
  startAudioStream() {
    return navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0 && this.isConnected) {
            this.ws.send(event.data);
          }
        };
        mediaRecorder.start(100); // Capture in 100ms chunks
        return mediaRecorder;
      })
      .catch(error => {
        console.error('Error accessing microphone:', error);
        throw error;
      });
  }

  // Event listener management
  addEventListener(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
  }

  removeEventListener(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback);
    }
  }

  notifyListeners(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => callback(data));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

export default WebSocketManager;