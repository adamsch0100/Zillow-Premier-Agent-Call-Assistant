# Real Estate Call Assistant - Project Brief

## Project Overview
We're building a real-time AI assistant that helps real estate agents handle Zillow lead calls more effectively. The system listens to phone conversations and provides instant suggestions for responses based on a pre-defined script and common scenarios.

## Core Features

### 1. Real-Time Call Analysis
- Listens to ongoing phone calls
- Transcribes conversation in real-time
- Identifies key triggers and customer objections
- Detects conversation sentiment

### 2. Smart Response System
- Provides script suggestions based on conversation context
- Handles common objections:
  * Listing agent requests
  * Already working with another agent
  * Quick questions about properties
  * Pending properties
  * Out-of-town buyers
  * Buyers not ready to purchase
- Prevents common mistakes (e.g., discussing financing too early)

### 3. User Interface
- Clean, minimal design for easy reading during calls
- Shows live transcription
- Displays contextual suggestions
- Indicates call status and recording

## Knowledge Base
The system is trained on Zillow's recommended scripts, including:

1. Opening Scripts:
```
- Name on lead, no tour
- No name on lead
- Scheduled tour scenarios
```

2. Objection Handlers:
```
- Listing agent requests
- Working with another agent
- Quick questions
- Pending properties
- Out-of-town buyers
- Not ready to buy
```

3. Best Practices:
```
- No bad news on first call
- End with "excited to work with you"
- Don't pull up MLS during call
- Don't discuss financing initially
- Focus on scheduling showings
```

## Technical Requirements

### Speech Processing
```yaml
Input:
  - Real-time audio capture
  - Phone call integration
  - Background noise handling

Processing:
  - Speech-to-text conversion
  - Speaker separation
  - Real estate terminology recognition
```

### AI/ML Components
```yaml
Analysis:
  - Conversation context tracking
  - Trigger word detection
  - Sentiment analysis
  - Response matching

Training:
  - Script-based training data
  - Common objection patterns
  - Best practice responses
```

### Backend Requirements
```yaml
Core:
  - Real-time audio processing
  - WebSocket connections
  - API integrations
  - Response generation

Database:
  - User profiles
  - Call recordings
  - Success metrics
  - Response effectiveness
```

### Frontend Requirements
```yaml
Interface:
  - Real-time updates
  - Clear suggestion display
  - Easy-to-read during calls
  - Mobile responsive

Features:
  - Call controls
  - Script customization
  - Settings management
  - Performance analytics
```

## Development Priorities

### MVP Features (Phase 1)
1. Basic call listening and transcription
2. Simple script suggestions
3. Core objection handlers
4. Basic user interface

### Enhanced Features (Phase 2)
1. Advanced sentiment analysis
2. Custom script learning
3. Performance analytics
4. Multi-agent support

## User Flow
1. Agent receives Zillow lead call
2. System automatically starts listening
3. Transcribes conversation in real-time
4. Identifies conversation context and objections
5. Provides relevant script suggestions
6. Tracks successful responses for learning

## Success Metrics
```yaml
Primary:
  - Lead conversion rate
  - Call success rate
  - Script effectiveness
  - Response timing

Secondary:
  - System accuracy
  - Suggestion relevance
  - User satisfaction
  - Technical performance
```

## Integration Points
```yaml
Required:
  - Phone system
  - Speech-to-text API
  - AI/ML services
  - CRM system (optional)
```

## Notes for AI Development Team
1. Focus on real-time performance
2. Prioritize accuracy of suggestion timing
3. Keep interface minimal and non-distracting
4. Ensure easy script customization
5. Build learning capability for improvement
6. Consider privacy and security requirements