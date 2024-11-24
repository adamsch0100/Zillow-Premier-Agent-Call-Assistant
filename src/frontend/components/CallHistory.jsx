import React, { useState, useEffect } from 'react';
import '../styles/CallHistory.css';

const CallHistory = () => {
    const [recordings, setRecordings] = useState([]);
    const [selectedRecording, setSelectedRecording] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchRecordings();
    }, []);

    const fetchRecordings = async () => {
        try {
            const response = await fetch('/api/recordings');
            if (!response.ok) {
                throw new Error('Failed to fetch recordings');
            }
            const data = await response.json();
            setRecordings(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const formatDuration = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleString();
    };

    const handlePlayRecording = async (recordingId) => {
        try {
            const response = await fetch(`/api/recordings/${recordingId}/audio`);
            if (!response.ok) {
                throw new Error('Failed to fetch audio');
            }
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            
            // Update selected recording with audio URL
            setSelectedRecording(prev => ({
                ...recordings.find(r => r.recording_id === recordingId),
                audioUrl: url
            }));
        } catch (err) {
            setError(err.message);
        }
    };

    if (isLoading) return <div className="loading">Loading call history...</div>;
    if (error) return <div className="error">{error}</div>;

    return (
        <div className="call-history">
            <h2>Call History</h2>
            
            <div className="recordings-list">
                {recordings.map(recording => (
                    <div 
                        key={recording.recording_id} 
                        className={`recording-item ${selectedRecording?.recording_id === recording.recording_id ? 'selected' : ''}`}
                        onClick={() => handlePlayRecording(recording.recording_id)}
                    >
                        <div className="recording-info">
                            <div className="recording-primary">
                                <span className="client-name">{recording.client_id}</span>
                                <span className="recording-date">{formatDate(recording.start_time)}</span>
                            </div>
                            <div className="recording-secondary">
                                <span className="agent-name">Agent: {recording.agent_id}</span>
                                <span className="duration">Duration: {formatDuration(recording.duration)}</span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {selectedRecording && (
                <div className="recording-player">
                    <h3>Playing: Call with {selectedRecording.client_id}</h3>
                    <audio 
                        controls 
                        src={selectedRecording.audioUrl}
                        className="audio-player"
                    >
                        Your browser does not support the audio element.
                    </audio>
                    <div className="recording-details">
                        <p>Date: {formatDate(selectedRecording.start_time)}</p>
                        <p>Duration: {formatDuration(selectedRecording.duration)}</p>
                        <p>Agent: {selectedRecording.agent_id}</p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CallHistory;