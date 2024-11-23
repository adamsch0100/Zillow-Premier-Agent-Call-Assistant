class SpeechProcessor {
    constructor(wsClient) {
        this.wsClient = wsClient;
        this.audioContext = null;
        this.mediaStream = null;
        this.mediaRecorder = null;
        this.processingNode = null;
        this.analyserNode = null;
        this.gainNode = null;
        this.isProcessing = false;
        this.isRecording = false;
        this.recordedChunks = [];
        this.audioQualityInterval = null;
        
        // Audio processing configuration
        this.config = {
            sampleRate: 16000,
            bufferSize: 4096,
            channels: 1,
            bitDepth: 16,
            encoderPath: '/path/to/encoderWorker.js',
            recordingFormat: 'audio/wav'
        };
        
        // Noise detection settings
        this.noiseThreshold = -50; // dB
        this.silenceTimeout = 1500; // ms
        this.lastVoiceDetection = Date.now();
        
        // Audio quality metrics
        this.metrics = {
            signalStrength: 0,
            noiseLevel: 0,
            clippingCount: 0,
            silenceDuration: 0
        };
        
        // Bind methods
        this.handleAudioProcess = this.handleAudioProcess.bind(this);
        this.updateAudioQuality = this.updateAudioQuality.bind(this);
    }

    async initialize() {
        try {
            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            this.mediaStream = stream;
            
            // Initialize Web Audio API
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.config.sampleRate
            });
            
            // Create audio nodes
            const source = this.audioContext.createMediaStreamSource(stream);
            this.analyserNode = this.audioContext.createAnalyser();
            this.gainNode = this.audioContext.createGain();
            this.processingNode = this.audioContext.createScriptProcessor(
                this.config.bufferSize,
                this.config.channels,
                this.config.channels
            );
            
            // Connect nodes
            source.connect(this.analyserNode);
            this.analyserNode.connect(this.processingNode);
            this.processingNode.connect(this.gainNode);
            this.gainNode.connect(this.audioContext.destination);
            
            // Configure analyser
            this.analyserNode.fftSize = 2048;
            this.analyserNode.smoothingTimeConstant = 0.8;
            
            // Initialize MediaRecorder for call recording
            this.initializeRecorder(stream);
            
            console.log('Audio processing initialized successfully');
            return true;
            
        } catch (error) {
            console.error('Error initializing audio:', error);
            throw error;
        }
    }

    initializeRecorder(stream) {
        const options = { mimeType: this.config.recordingFormat };
        
        try {
            this.mediaRecorder = new MediaRecorder(stream, options);
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = async () => {
                const blob = new Blob(this.recordedChunks, {
                    type: this.config.recordingFormat
                });
                await this.saveRecording(blob);
            };
            
        } catch (error) {
            console.error('Error initializing recorder:', error);
            throw error;
        }
    }

    startProcessing() {
        if (!this.isProcessing) {
            this.isProcessing = true;
            this.processingNode.addEventListener('audioprocess', this.handleAudioProcess);
            this.startAudioQualityMonitoring();
            console.log('Started audio processing');
        }
    }

    stopProcessing() {
        if (this.isProcessing) {
            this.isProcessing = false;
            this.processingNode.removeEventListener('audioprocess', this.handleAudioProcess);
            this.stopAudioQualityMonitoring();
            console.log('Stopped audio processing');
        }
    }

    startRecording() {
        if (!this.isRecording && this.mediaRecorder) {
            this.recordedChunks = [];
            this.mediaRecorder.start();
            this.isRecording = true;
            console.log('Started recording');
        }
    }

    stopRecording() {
        if (this.isRecording && this.mediaRecorder) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            console.log('Stopped recording');
        }
    }

    handleAudioProcess(event) {
        if (!this.isProcessing) return;

        const inputBuffer = event.inputBuffer;
        const inputData = inputBuffer.getChannelData(0);
        
        // Process audio data
        const processedData = this.processAudioData(inputData);
        
        // Check if there's voice activity
        if (this.detectVoiceActivity(processedData)) {
            this.lastVoiceDetection = Date.now();
            
            // Send audio chunk to server
            const audioChunk = this.encodeAudioData(processedData);
            this.wsClient.sendAudioChunk(audioChunk);
        } else {
            // Check for extended silence
            const silenceDuration = Date.now() - this.lastVoiceDetection;
            if (silenceDuration > this.silenceTimeout) {
                this.metrics.silenceDuration = silenceDuration;
            }
        }
    }

    processAudioData(inputData) {
        // Convert to 16-bit PCM
        const processedData = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
            const s = Math.max(-1, Math.min(1, inputData[i]));
            processedData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return processedData;
    }

    detectVoiceActivity(audioData) {
        // Calculate RMS of the signal
        let sum = 0;
        for (let i = 0; i < audioData.length; i++) {
            sum += (audioData[i] * audioData[i]);
        }
        const rms = Math.sqrt(sum / audioData.length);
        
        // Convert to dB
        const db = 20 * Math.log10(rms);
        
        // Update signal strength metric
        this.metrics.signalStrength = Math.max(0, Math.min(1, (db - this.noiseThreshold) / 50));
        
        return db > this.noiseThreshold;
    }

    encodeAudioData(processedData) {
        // Create WAV header
        const header = new ArrayBuffer(44);
        const view = new DataView(header);
        
        // WAV header format
        writeString(view, 0, 'RIFF');
        view.setUint32(4, 36 + processedData.length * 2, true);
        writeString(view, 8, 'WAVE');
        writeString(view, 12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, this.config.sampleRate, true);
        view.setUint32(28, this.config.sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeString(view, 36, 'data');
        view.setUint32(40, processedData.length * 2, true);
        
        // Combine header and audio data
        const blob = new Blob([header, processedData.buffer], {
            type: 'audio/wav'
        });
        
        return blob;
    }

    startAudioQualityMonitoring() {
        this.audioQualityInterval = setInterval(this.updateAudioQuality, 100);
    }

    stopAudioQualityMonitoring() {
        if (this.audioQualityInterval) {
            clearInterval(this.audioQualityInterval);
            this.audioQualityInterval = null;
        }
    }

    updateAudioQuality() {
        if (!this.analyserNode) return;
        
        const dataArray = new Uint8Array(this.analyserNode.frequencyBinCount);
        this.analyserNode.getByteFrequencyData(dataArray);
        
        // Calculate average frequency magnitude
        let sum = 0;
        let peakMagnitude = 0;
        for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
            peakMagnitude = Math.max(peakMagnitude, dataArray[i]);
        }
        const avgMagnitude = sum / dataArray.length;
        
        // Update metrics
        this.metrics.noiseLevel = avgMagnitude / 255;
        if (peakMagnitude >= 254) {
            this.metrics.clippingCount++;
        }
        
        // Send quality metrics to server
        this.wsClient.send({
            type: 'audio_quality',
            payload: {
                signalStrength: this.metrics.signalStrength,
                noiseLevel: this.metrics.noiseLevel,
                clippingCount: this.metrics.clippingCount,
                silenceDuration: this.metrics.silenceDuration
            }
        });
    }

    async saveRecording(blob) {
        try {
            // Create download link
            const url = URL.createObjectURL(blob);
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const a = document.createElement('a');
            document.body.appendChild(a);
            a.style = 'display: none';
            a.href = url;
            a.download = `call-recording-${timestamp}.wav`;
            a.click();
            
            // Clean up
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            this.recordedChunks = [];
            
        } catch (error) {
            console.error('Error saving recording:', error);
            throw error;
        }
    }

    release() {
        this.stopProcessing();
        this.stopRecording();
        
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
        }
        
        if (this.audioContext) {
            this.audioContext.close();
        }
    }
}

// Utility function to write strings to DataView
function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}