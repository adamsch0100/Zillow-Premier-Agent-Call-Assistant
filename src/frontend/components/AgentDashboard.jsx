import React, { useState, useEffect } from 'react';
import SuggestionPanel from './SuggestionPanel';
import '../styles/AgentDashboard.css';

const AgentDashboard = () => {
  const [callActive, setCallActive] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcription, setTranscription] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [almStage, setAlmStage] = useState({
    appointment: { secured: false },
    location: { discussed: false },
    motivation: { discussed: false },
    current_priority: 'appointment'
  });
  const [callStats, setCallStats] = useState({
    duration: 0,
    appointmentsSet: 0,
    callsToday: 0
  });

  useEffect(() => {
    // Initialize WebSocket connection when component mounts
    const ws = new WebSocket('ws://localhost:8000/ws/agent');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };

    return () => {
      ws.close();
    };
  }, []);

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'transcription':
        setTranscription(prev => prev + '\n' + data.text);
        break;
      case 'suggestions':
        setSuggestions(data.suggestions);
        break;
      case 'alm_update':
        setAlmStage(data.almStage);
        break;
      case 'call_stats':
        setCallStats(data.stats);
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  };

  const startCall = async () => {
    try {
      setCallActive(true);
      setRecording(true);
      // Additional call start logic
    } catch (error) {
      console.error('Error starting call:', error);
    }
  };

  const endCall = () => {
    setCallActive(false);
    setRecording(false);
    // Additional call end logic
  };

  const handleSuggestionSelect = (suggestion) => {
    // Copy suggestion to clipboard or trigger text-to-speech
    navigator.clipboard.writeText(suggestion)
      .then(() => console.log('Suggestion copied to clipboard'))
      .catch(err => console.error('Failed to copy suggestion:', err));
  };

  return (
    <div className="agent-dashboard">
      <header className="dashboard-header">
        <h1>Real Estate Call Assistant</h1>
        <div className="call-controls">
          <button 
            className={`call-button ${callActive ? 'active' : ''}`}
            onClick={callActive ? endCall : startCall}
          >
            {callActive ? 'End Call' : 'Start Call'}
          </button>
          <div className="call-status">
            {callActive && <span className="recording-indicator">Recording</span>}
          </div>
        </div>
      </header>

      <div className="dashboard-content">
        <div className="left-panel">
          <div className="call-stats">
            <h3>Today's Statistics</h3>
            <div className="stats-grid">
              <div className="stat-item">
                <label>Calls Today</label>
                <span>{callStats.callsToday}</span>
              </div>
              <div className="stat-item">
                <label>Appointments Set</label>
                <span>{callStats.appointmentsSet}</span>
              </div>
              <div className="stat-item">
                <label>Current Call Duration</label>
                <span>{Math.floor(callStats.duration / 60)}:{(callStats.duration % 60).toString().padStart(2, '0')}</span>
              </div>
            </div>
          </div>

          <div className="transcription-panel">
            <h3>Live Transcription</h3>
            <div className="transcription-content">
              {transcription.split('\n').map((line, index) => (
                <p key={index}>{line}</p>
              ))}
            </div>
          </div>
        </div>

        <div className="right-panel">
          <SuggestionPanel 
            suggestions={suggestions}
            almStage={almStage}
            onSuggestionSelect={handleSuggestionSelect}
          />
        </div>
      </div>
    </div>
  );
};

export default AgentDashboard;