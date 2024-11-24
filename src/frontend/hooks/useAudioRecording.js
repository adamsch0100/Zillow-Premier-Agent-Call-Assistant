import { useState, useRef, useCallback, useEffect } from 'react';
import { websocketManager } from '../utils/websocket-manager';

const AUDIO_CHUNK_SIZE = 4096; // bytes

export const useAudioRecording = () => {
    const [isRecording, setIsRecording] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const [error, setError] = useState(null);
    
    const mediaRecorderRef = useRef(null);
    const streamRef = useRef(null);
    const timerRef = useRef(null);
    
    const startRecording = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;
            
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    // Convert blob to ArrayBuffer for WebSocket transmission
                    event.data.arrayBuffer().then(buffer => {
                        websocketManager.sendAudioChunk(buffer);
                    });
                }
            };
            
            mediaRecorder.start(100); // Capture data every 100ms
            setIsRecording(true);
            
            // Start timer
            timerRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);
            
        } catch (err) {
            setError(err.message);
            console.error('Error starting recording:', err);
        }
    }, []);
    
    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            streamRef.current.getTracks().forEach(track => track.stop());
            
            // Clear timer
            if (timerRef.current) {
                clearInterval(timerRef.current);
                timerRef.current = null;
            }
            
            setIsRecording(false);
            setRecordingTime(0);
            websocketManager.endAudioStream();
        }
    }, [isRecording]);
    
    useEffect(() => {
        return () => {
            // Cleanup on unmount
            if (isRecording) {
                stopRecording();
            }
        };
    }, [isRecording, stopRecording]);
    
    return {
        isRecording,
        recordingTime,
        error,
        startRecording,
        stopRecording
    };
};