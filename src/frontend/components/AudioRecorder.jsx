import React, { useState, useEffect, useRef } from 'react';
import '../styles/AudioRecorder.css';

const AudioRecorder = ({ onRecordingStart, onRecordingStop, onAudioData }) => {
    const [isRecording, setIsRecording] = useState(false);
    const [audioStream, setAudioStream] = useState(null);
    const [recordingTime, setRecordingTime] = useState(0);
    const mediaRecorderRef = useRef(null);
    const timerRef = useRef(null);

    useEffect(() => {
        return () => {
            stopRecording();
            if (timerRef.current) {
                clearInterval(timerRef.current);
            }
        };
    }, []);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            setAudioStream(stream);

            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;

            const audioChunks = [];
            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
                if (onAudioData) {
                    onAudioData(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                const audioUrl = URL.createObjectURL(audioBlob);
                if (onRecordingStop) {
                    onRecordingStop(audioUrl, audioBlob);
                }
            };

            mediaRecorder.start(100); // Send data every 100ms
            setIsRecording(true);
            if (onRecordingStart) {
                onRecordingStart();
            }

            // Start timer
            timerRef.current = setInterval(() => {
                setRecordingTime((prevTime) => prevTime + 1);
            }, 1000);

        } catch (error) {
            console.error('Error accessing microphone:', error);
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            audioStream?.getTracks().forEach(track => track.stop());
            setIsRecording(false);
            setRecordingTime(0);
            if (timerRef.current) {
                clearInterval(timerRef.current);
            }
        }
    };

    const formatTime = (seconds) => {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    };

    return (
        <div className="audio-recorder">
            <div className="recording-controls">
                {!isRecording ? (
                    <button 
                        className="start-button"
                        onClick={startRecording}
                    >
                        Start Recording
                    </button>
                ) : (
                    <button 
                        className="stop-button"
                        onClick={stopRecording}
                    >
                        Stop Recording
                    </button>
                )}
            </div>
            {isRecording && (
                <div className="recording-indicator">
                    <div className="recording-dot"></div>
                    <span className="recording-time">{formatTime(recordingTime)}</span>
                </div>
            )}
        </div>
    );
};

export default AudioRecorder;