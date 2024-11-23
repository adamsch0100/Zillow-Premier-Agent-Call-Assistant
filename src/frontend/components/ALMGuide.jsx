import React, { useState } from 'react';

const ALMGuide = () => {
  const [currentStage, setCurrentStage] = useState('appointment');
  const [callStatus, setCallStatus] = useState({
    appointment: false,
    location: false,
    motivation: false
  });

  // Core scripts for each stage
  const scripts = {
    appointment: {
      title: "A: Secure the Appointment",
      scripts: [
        "When would you like to go see the property?",
        "I can show you this home today or tomorrow. What works best for you?",
        "Would you prefer a morning or afternoon viewing?"
      ],
      objections: {
        "Just looking": [
          "I completely understand. Many of my clients start by just looking. When would you like to go see this property?",
          "That's actually the perfect time for us to connect! Would tomorrow or the next day work better for viewing?"
        ],
        "Want listing agent": [
          "The listing agent is a colleague of mine and I can absolutely show you this home. When would you like to go see it?",
          "I would be happy to represent you as your full-service agent. When would you like to view the property?"
        ],
        "Already have agent": [
          "I completely understand! I am free to show you this property, and I'd be happy to help you find the right home. When works best for you?"
        ]
      }
    },
    location: {
      title: "L: Explore Location Preferences",
      scripts: [
        "Are there any other properties you've been looking at? I'd be happy to arrange tours for those as well.",
        "Are you only interested in this area, or are you open to seeing alternative locations?",
        "Would you like me to find similar properties in this neighborhood for us to view?"
      ]
    },
    motivation: {
      title: "M: Understand Motivation",
      scripts: [
        "What interests you about this property?",
        "How long have you been looking?",
        "Have you seen any other properties?"
      ]
    }
  };

  const handleStageComplete = (stage) => {
    setCallStatus(prev => ({
      ...prev,
      [stage]: true
    }));
    
    // Move to next stage
    if (stage === 'appointment') setCurrentStage('location');
    if (stage === 'location') setCurrentStage('motivation');
  };

  return (
    <div className="alm-guide">
      <div className="progress-tracker">
        <div className={`stage ${currentStage === 'appointment' ? 'active' : ''} ${callStatus.appointment ? 'completed' : ''}`}>
          Appointment
        </div>
        <div className={`stage ${currentStage === 'location' ? 'active' : ''} ${callStatus.location ? 'completed' : ''}`}>
          Location
        </div>
        <div className={`stage ${currentStage === 'motivation' ? 'active' : ''} ${callStatus.motivation ? 'completed' : ''}`}>
          Motivation
        </div>
      </div>

      <div className="current-stage">
        <h2>{scripts[currentStage].title}</h2>
        <div className="scripts">
          {scripts[currentStage].scripts.map((script, index) => (
            <div key={index} className="script-item" onClick={() => navigator.clipboard.writeText(script)}>
              {script}
            </div>
          ))}
        </div>
        
        {currentStage === 'appointment' && (
          <div className="objections">
            <h3>Common Objections</h3>
            {Object.entries(scripts.appointment.objections).map(([objection, responses]) => (
              <div key={objection} className="objection-group">
                <h4>{objection}</h4>
                {responses.map((response, index) => (
                  <div key={index} className="response-item" onClick={() => navigator.clipboard.writeText(response)}>
                    {response}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        <button 
          className="complete-stage" 
          onClick={() => handleStageComplete(currentStage)}
        >
          Complete {currentStage.charAt(0).toUpperCase() + currentStage.slice(1)}
        </button>
      </div>
    </div>
  );
};

export default ALMGuide;