class ResponseMatcher {
    constructor() {
        this.context = {
            phase: 'A',  // Start with Appointment phase
            progress: {
                A: 0,
                L: 0,
                M: 0
            },
            keyInfo: new Set(),
            objections: [],
            rapport: 0
        };
    }

    updateContext(transcription) {
        // Update ALM phase and progress based on conversation
        this.updateALMProgress(transcription);
        
        // Track key information captured
        this.updateKeyInfo(transcription);
        
        // Detect and track objections
        this.detectObjections(transcription);
        
        // Update rapport score
        this.updateRapport(transcription);
    }

    updateALMProgress(transcription) {
        // Check for phase-specific keywords and update progress
        const text = transcription.text.toLowerCase();
        
        // Appointment phase triggers
        if (text.includes('when') || text.includes('time') || text.includes('schedule')) {
            this.context.phase = 'A';
            this.context.progress.A += 20;
        }
        
        // Location phase triggers
        if (text.includes('area') || text.includes('neighborhood') || text.includes('location')) {
            this.context.phase = 'L';
            this.context.progress.L += 20;
        }
        
        // Motivation phase triggers
        if (text.includes('why') || text.includes('looking for') || text.includes('need')) {
            this.context.phase = 'M';
            this.context.progress.M += 20;
        }

        // Cap progress at 100
        Object.keys(this.context.progress).forEach(key => {
            this.context.progress[key] = Math.min(this.context.progress[key], 100);
        });
    }

    updateKeyInfo(transcription) {
        const text = transcription.text.toLowerCase();
        
        // Track important information
        if (text.includes('phone') || text.includes('email')) {
            this.context.keyInfo.add('contact');
        }
        if (text.includes('budget') || text.includes('price')) {
            this.context.keyInfo.add('budget');
        }
        if (text.includes('timeline') || text.includes('when')) {
            this.context.keyInfo.add('timeline');
        }
    }

    detectObjections(transcription) {
        const text = transcription.text.toLowerCase();
        
        // Common objections
        const objectionPatterns = {
            'agent': ['already have an agent', 'working with someone'],
            'price': ['too expensive', 'over budget'],
            'timing': ['not ready', 'too soon'],
            'location': ['too far', 'different area']
        };

        Object.entries(objectionPatterns).forEach(([type, patterns]) => {
            if (patterns.some(pattern => text.includes(pattern))) {
                this.context.objections.push({
                    type,
                    text: transcription.text
                });
            }
        });
    }

    updateRapport(transcription) {
        const text = transcription.text.toLowerCase();
        
        // Positive rapport indicators
        const positivePatterns = [
            'thank you',
            'appreciate',
            'great',
            'perfect',
            'wonderful'
        ];

        // Negative rapport indicators
        const negativePatterns = [
            'no',
            'not interested',
            'busy',
            'don\'t want'
        ];

        // Update rapport score
        positivePatterns.forEach(pattern => {
            if (text.includes(pattern)) this.context.rapport += 1;
        });

        negativePatterns.forEach(pattern => {
            if (text.includes(pattern)) this.context.rapport -= 1;
        });
    }

    getSuggestions(transcription) {
        // Generate next-best responses based on context
        const suggestions = [];
        
        // Add phase-specific suggestions
        switch (this.context.phase) {
            case 'A':
                suggestions.push(this.getAppointmentSuggestions());
                break;
            case 'L':
                suggestions.push(this.getLocationSuggestions());
                break;
            case 'M':
                suggestions.push(this.getMotivationSuggestions());
                break;
        }

        // Add objection handlers if needed
        if (this.context.objections.length > 0) {
            suggestions.push(this.getObjectionHandlers());
        }

        return suggestions;
    }

    getAppointmentSuggestions() {
        return {
            type: 'appointment',
            suggestions: [
                'Would you like to see the property today or tomorrow?',
                'I have several time slots available. What works best for you?',
                'Would morning or afternoon be better for you?'
            ]
        };
    }

    getLocationSuggestions() {
        return {
            type: 'location',
            suggestions: [
                'What other areas are you considering?',
                'Would you like to see other properties in this neighborhood?',
                'How important is the location to you?'
            ]
        };
    }

    getMotivationSuggestions() {
        return {
            type: 'motivation',
            suggestions: [
                'What features are most important to you in a home?',
                'What\'s motivating your move at this time?',
                'How soon are you looking to move?'
            ]
        };
    }

    getObjectionHandlers() {
        const lastObjection = this.context.objections[this.context.objections.length - 1];
        
        const handlers = {
            'agent': [
                'Have you signed any paperwork with them?',
                'What if I could show you properties they might have missed?'
            ],
            'price': [
                'What\'s your ideal price range?',
                'Would you like to see similar properties in your budget?'
            ],
            'timing': [
                'What timeline works better for you?',
                'Would you like me to keep you updated on new listings?'
            ],
            'location': [
                'What areas are you most interested in?',
                'I know several similar properties in your preferred location.'
            ]
        };

        return {
            type: 'objection',
            objectionType: lastObjection.type,
            suggestions: handlers[lastObjection.type] || []
        };
    }

    getMetrics() {
        return {
            almProgress: this.context.progress,
            keyInfo: this.context.keyInfo.size,
            objections: this.context.objections.length,
            rapport: this.getRapportLevel()
        };
    }

    getRapportLevel() {
        if (this.context.rapport >= 3) return 'Excellent';
        if (this.context.rapport >= 1) return 'Good';
        if (this.context.rapport >= -1) return 'Neutral';
        return 'Needs Improvement';
    }
}