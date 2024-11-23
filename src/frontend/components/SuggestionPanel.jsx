import React, { useState, useEffect } from 'react';
import '../styles/SuggestionPanel.css';

const SuggestionPanel = ({ suggestions, almStage, onSuggestionSelect }) => {
  const [selectedSuggestion, setSelectedSuggestion] = useState(null);
  const [progressPercentage, setProgressPercentage] = useState(0);

  useEffect(() => {
    // Calculate progress percentage based on ALM stage
    if (almStage) {
      const stepsCompleted = [
        almStage.appointment.secured,
        almStage.location.discussed,
        almStage.motivation.discussed
      ].filter(Boolean).length;
      
      setProgressPercentage((stepsCompleted / 3) * 100);
    }
  }, [almStage]);

  const handleSuggestionClick = (suggestion) => {
    setSelectedSuggestion(suggestion);
    onSuggestionSelect(suggestion);
  };

  const getCurrentFocus = () => {
    if (!almStage.appointment.secured) return 'Appointment';
    if (!almStage.location.discussed) return 'Location';
    if (!almStage.motivation.discussed) return 'Motivation';
    return 'Closing';
  };

  return (
    <div className="suggestion-panel">
      <div className="alm-progress">
        <div className="progress-header">
          <h3>ALM Progress</h3>
          <span>{progressPercentage}% Complete</span>
        </div>
        <div className="progress-bar">
          <div 
            className="progress-fill"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
        <div className="current-focus">
          <span>Current Focus: {getCurrentFocus()}</span>
        </div>
      </div>

      <div className="suggestions-container">
        <h3>Suggested Responses</h3>
        <div className="suggestions-list">
          {suggestions.map((suggestion, index) => (
            <div
              key={index}
              className={`suggestion-item ${selectedSuggestion === suggestion ? 'selected' : ''}`}
              onClick={() => handleSuggestionClick(suggestion)}
            >
              {suggestion}
            </div>
          ))}
        </div>
      </div>

      <div className="alm-status">
        <div className={`status-item ${almStage.appointment.secured ? 'completed' : ''}`}>
          <span className="status-label">Appointment:</span>
          <span className="status-value">
            {almStage.appointment.secured ? '✓ Secured' : 'Pending'}
          </span>
        </div>
        <div className={`status-item ${almStage.location.discussed ? 'completed' : ''}`}>
          <span className="status-label">Location:</span>
          <span className="status-value">
            {almStage.location.discussed ? '✓ Discussed' : 'Not Discussed'}
          </span>
        </div>
        <div className={`status-item ${almStage.motivation.discussed ? 'completed' : ''}`}>
          <span className="status-label">Motivation:</span>
          <span className="status-value">
            {almStage.motivation.discussed ? '✓ Discussed' : 'Not Discussed'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default SuggestionPanel;