/**
 * Quebec Voice Agent - Client-Side Implementation
 *
 * Features:
 * - WebSocket connection to FastAPI backend
 * - Real-time audio streaming with PCM16 format
 * - Voice Activity Detection (VAD) for barge-in
 * - Automatic response cancellation when user speaks during agent response
 */

class VoiceClient {
    constructor() {
        this.ws = null;
        this.sessionId = null;
        this.isConnected = false;
        this.isRecording = false;
        this.isAgentSpeaking = false;

        // Audio context and nodes
        this.audioContext = null;
        this.mediaStream = null;
        this.audioWorkletNode = null;
        this.analyser = null;

        // VAD configuration
        this.vadThreshold = -45; // dBFS
        this.vadCheckInterval = null;

        // UI elements
        this.statusEl = document.getElementById('status');
        this.connectBtn = document.getElementById('connectBtn');
        this.disconnectBtn = document.getElementById('disconnectBtn');
        this.talkBtn = document.getElementById('talkBtn');
        this.transcriptEl = document.getElementById('transcript');
        this.vadMeterEl = document.getElementById('vadMeter');
        this.vadStatusEl = document.getElementById('vadStatus');

        this.setupEventListeners();
    }

    setupEventListeners() {
        this.connectBtn.addEventListener('click', () => this.connect());
        this.disconnectBtn.addEventListener('click', () => this.disconnect());

        // Push-to-talk
        this.talkBtn.addEventListener('mousedown', () => this.startRecording());
        this.talkBtn.addEventListener('mouseup', () => this.stopRecording());
        this.talkBtn.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.startRecording();
        });
        this.talkBtn.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.stopRecording();
        });
    }

    async connect() {
        const serverUrl = document.getElementById('serverUrl').value;
        const language = document.getElementById('language').value;
        const agentType = document.getElementById('agentType').value;

        this.updateStatus('connecting', '🟡 Connecting...');

        try {
            // Create session
            const response = await fetch(`${serverUrl}/session/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    language,
                    agent_type: agentType,
                    geolocation: language === 'fr-CA' ? 'Quebec' : null,
                }),
            });

            if (!response.ok) {
                throw new Error(`Failed to create session: ${response.statusText}`);
            }

            const data = await response.json();
            this.sessionId = data.session_id;

            // Connect WebSocket
            const wsUrl = serverUrl.replace('http', 'ws') + data.websocket_url;
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => this.onWebSocketOpen();
            this.ws.onmessage = (event) => this.onWebSocketMessage(event);
            this.ws.onerror = (error) => this.onWebSocketError(error);
            this.ws.onclose = () => this.onWebSocketClose();

        } catch (error) {
            console.error('Connection error:', error);
            this.updateStatus('disconnected', '⚫ Connection failed: ' + error.message);
        }
    }

    async disconnect() {
        if (this.ws) {
            this.ws.close();
        }

        if (this.audioContext) {
            await this.audioContext.close();
            this.audioContext = null;
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        this.isConnected = false;
        this.updateStatus('disconnected', '⚫ Disconnected');
        this.connectBtn.disabled = false;
        this.disconnectBtn.disabled = true;
        this.talkBtn.disabled = true;
    }

    async onWebSocketOpen() {
        console.log('WebSocket connected');
        this.isConnected = true;
        this.updateStatus('connected', '🟢 Connected');

        this.connectBtn.disabled = true;
        this.disconnectBtn.disabled = false;
        this.talkBtn.disabled = false;

        // Initialize audio context
        await this.initializeAudio();
    }

    onWebSocketMessage(event) {
        try {
            const message = JSON.parse(event.data);

            switch (message.type) {
                case 'audio':
                    this.playAudioResponse(message.data);
                    this.isAgentSpeaking = true;
                    break;

                case 'transcript':
                    this.addTranscript('agent', message.data);
                    break;

                case 'audio_end':
                    this.isAgentSpeaking = false;
                    break;

                default:
                    console.log('Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Error handling message:', error);
        }
    }

    onWebSocketError(error) {
        console.error('WebSocket error:', error);
        this.updateStatus('disconnected', '⚫ Connection error');
    }

    onWebSocketClose() {
        console.log('WebSocket closed');
        this.disconnect();
    }

    async initializeAudio() {
        try {
            // Request microphone access
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 16000,
                },
            });

            // Create audio context
            this.audioContext = new AudioContext({ sampleRate: 16000 });

            // Create analyser for VAD
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 2048;
            this.analyser.smoothingTimeConstant = 0.8;

            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            source.connect(this.analyser);

            console.log('Audio initialized');

        } catch (error) {
            console.error('Failed to initialize audio:', error);
            alert('Failed to access microphone. Please check permissions.');
        }
    }

    async startRecording() {
        if (!this.isConnected || this.isRecording) return;

        this.isRecording = true;
        this.talkBtn.classList.add('active');
        this.talkBtn.textContent = '🎤 Recording...';

        try {
            // Create script processor for audio capture
            const scriptProcessor = this.audioContext.createScriptProcessor(4096, 1, 1);
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);

            source.connect(scriptProcessor);
            scriptProcessor.connect(this.audioContext.destination);

            scriptProcessor.onaudioprocess = (event) => {
                if (!this.isRecording) return;

                const inputData = event.inputBuffer.getChannelData(0);

                // Convert float32 to PCM16
                const pcm16 = this.floatTo16BitPCM(inputData);

                // Send to server
                this.sendAudio(pcm16);
            };

            // Store for cleanup
            this.scriptProcessor = scriptProcessor;

            // Start VAD monitoring
            this.startVADMonitoring();

        } catch (error) {
            console.error('Failed to start recording:', error);
            this.stopRecording();
        }
    }

    stopRecording() {
        if (!this.isRecording) return;

        this.isRecording = false;
        this.talkBtn.classList.remove('active');
        this.talkBtn.textContent = '🎤 Hold to Talk';

        // Cleanup
        if (this.scriptProcessor) {
            this.scriptProcessor.disconnect();
            this.scriptProcessor = null;
        }

        // Stop VAD monitoring
        this.stopVADMonitoring();

        // Notify server that audio input ended
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'audio_end' }));
        }
    }

    sendAudio(pcm16Data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            // Convert to hex string
            const hexString = Array.from(pcm16Data)
                .map(byte => byte.toString(16).padStart(2, '0'))
                .join('');

            this.ws.send(JSON.stringify({
                type: 'audio',
                data: hexString,
            }));
        }
    }

    startVADMonitoring() {
        // Monitor for barge-in (user speaking while agent is responding)
        this.vadCheckInterval = setInterval(() => {
            const level = this.getAudioLevel();

            // Update VAD meter
            const percentage = Math.min(100, ((level + 100) / 100) * 100);
            this.vadMeterEl.style.width = `${percentage}%`;
            this.vadStatusEl.textContent = `Level: ${level.toFixed(1)} dBFS | Threshold: ${this.vadThreshold} dBFS`;

            // Check for barge-in
            if (this.isAgentSpeaking && level > this.vadThreshold) {
                console.log('Barge-in detected!');
                this.handleBargeIn();
            }
        }, 100);
    }

    stopVADMonitoring() {
        if (this.vadCheckInterval) {
            clearInterval(this.vadCheckInterval);
            this.vadCheckInterval = null;
        }
    }

    getAudioLevel() {
        if (!this.analyser) return -100;

        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(dataArray);

        // Calculate RMS
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i] * dataArray[i];
        }
        const rms = Math.sqrt(sum / dataArray.length);

        // Convert to dBFS (decibels relative to full scale)
        const dBFS = 20 * Math.log10(rms / 255);

        return dBFS;
    }

    handleBargeIn() {
        // Stop agent audio
        if (this.audioContext) {
            this.audioContext.suspend();
        }

        this.isAgentSpeaking = false;

        // Send barge-in event to server
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'barge_in' }));
        }

        // Resume audio context after a short delay
        setTimeout(() => {
            if (this.audioContext) {
                this.audioContext.resume();
            }
        }, 500);
    }

    floatTo16BitPCM(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return new Uint8Array(int16Array.buffer);
    }

    playAudioResponse(hexData) {
        // Convert hex string to PCM16
        const bytes = new Uint8Array(hexData.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
        const int16Array = new Int16Array(bytes.buffer);

        // Convert to float32 for playback
        const float32Array = new Float32Array(int16Array.length);
        for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7FFF);
        }

        // Create audio buffer
        const audioBuffer = this.audioContext.createBuffer(1, float32Array.length, 16000);
        audioBuffer.getChannelData(0).set(float32Array);

        // Play
        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.audioContext.destination);
        source.start();

        source.onended = () => {
            this.isAgentSpeaking = false;
        };
    }

    addTranscript(role, text) {
        const messageEl = document.createElement('div');
        messageEl.className = `transcript-message ${role}`;

        const labelEl = document.createElement('div');
        labelEl.className = 'transcript-label';
        labelEl.textContent = role === 'user' ? 'You' : 'Jean-Guy';

        const textEl = document.createElement('div');
        textEl.textContent = text;

        messageEl.appendChild(labelEl);
        messageEl.appendChild(textEl);

        // Clear placeholder if this is the first message
        if (this.transcriptEl.children.length === 1 &&
            this.transcriptEl.children[0].style.color === '#999') {
            this.transcriptEl.innerHTML = '';
        }

        this.transcriptEl.appendChild(messageEl);
        this.transcriptEl.scrollTop = this.transcriptEl.scrollHeight;
    }

    updateStatus(state, message) {
        this.statusEl.className = `status ${state}`;
        this.statusEl.textContent = message;
    }
}

// Initialize client when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.voiceClient = new VoiceClient();
});
