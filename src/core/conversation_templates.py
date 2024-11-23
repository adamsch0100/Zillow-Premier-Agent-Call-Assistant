"""
Conversation templates and responses for the Real Estate Call Assistant.
"""

OPENING_SCRIPTS = {
    "named_no_tour": {
        "template": "Hi, this is {agent_name} with {brokerage}, am I speaking with {lead_name}? "
                   "Great! I see you are reaching out about {property_address}, when would you like to go see it?",
        "keywords": ["hi", "hello", "reaching out", "property", "see"],
    },
    "unnamed_no_tour": {
        "template": "Hi, this is {agent_name} with {brokerage}, who am I speaking with this morning? "
                   "It is nice to meet you {given_name}! I see you are reaching out about {property_address}, "
                   "when would you like to go see it?",
        "keywords": ["hi", "hello", "meet", "reaching out", "property", "see"],
    },
    "named_scheduled": {
        "template": "Hi, this is {agent_name} with {brokerage}, am I speaking with {lead_name}? "
                   "Great! I see you have scheduled a showing for {property_address}, on {date} at {time}. "
                   "I will be happy to show it to you then! Are you open to touring other properties similar "
                   "to this one while we are out looking at this home?",
        "keywords": ["scheduled", "showing", "similar", "properties", "touring"],
    },
    "unnamed_scheduled": {
        "template": "Hi, this is {agent_name} with {brokerage}, who am I speaking with this morning? "
                   "It is nice to meet you {given_name}! I see you have scheduled a showing for {property_address}, "
                   "on {date} at {time}, I will be happy to show it to you then! Are you open to touring other "
                   "properties similar to this one while we are out looking at this home?",
        "keywords": ["scheduled", "showing", "similar", "properties", "touring"],
    }
}

OBJECTION_HANDLERS = {
    "listing_agent": {
        "steamroll": {
            "template": "The listing agent for this property is a colleague of mine and I can absolutely "
                       "show you this home, when would you like to go see it?",
            "keywords": ["listing agent", "show", "colleague"],
        },
        "education": {
            "template": "I understand and just want to make sure you're taken care of. I would be happy to "
                       "represent you as your full-service real estate agent, and I am available all week to "
                       "show you as many properties as necessary to find you the best home. It is a common "
                       "misconception that the listing agent will be able to get you the best deal, as they "
                       "are also looking out for the best interest of the seller. They will not fully be able "
                       "to commit to your needs. If you had interest in multiple properties, it could become "
                       "quite the nuisance for you to reach out to multiple agents, as you would receive various "
                       "follow up communication from all of them moving forward. Again, I would love to represent "
                       "you, regardless of how many properties we look at, and be your one stop shop for all of "
                       "your real estate needs! Are you free to tour the property tomorrow morning?",
            "keywords": ["listing agent", "represent", "best deal", "seller", "multiple properties"],
        }
    },
    "working_with_agent": {
        "template": "I completely understand! I am free to show you this property, and I would be happy to "
                   "help you find the right home. Of course, if we toured this home together, my expectation "
                   "would be that I would represent you, and write an offer on your behalf if you decide to "
                   "move forward. If you are not comfortable with that, I totally understand, and do not want "
                   "to step on anyone's toes! If that's the case, I would recommend reaching out to your agent, "
                   "and schedule a tour when they're available. I personally have been servicing this area for "
                   "{years_experience} years, and have a strong understanding of the market, and what it takes "
                   "to win offers. I will send you my contact information, and of course you are always welcome "
                   "to reach out to me at any time if you'd like to work together! Would you like me to show "
                   "you this property?",
        "keywords": ["working with", "another agent", "represent", "offer"],
    },
    "quick_question": {
        "template": "Absolutely, I will be happy to help! I don't have information in front of me at this "
                   "moment but will be happy to reach out to the seller as soon as we're off the call and "
                   "answer any question's you have! What would you like to know about the property?",
        "follow_up": "Perfect! I will get that information for you and get back with you shortly! I'd love "
                    "to schedule a showing for you to tour the property as well, are you free tomorrow "
                    "morning to see it?",
        "keywords": ["question", "information", "know about", "property"],
    },
    "pending_property": {
        "template": "I do see that as well. Many sellers will still entertain back up offers after their "
                   "home goes in contract. I will be happy to reach out to the seller and see if they are "
                   "accepting back up offers at this time! When are you free to tour the property?",
        "keywords": ["pending", "contract", "backup", "offers"],
    },
    "out_of_town": {
        "template": "I understand, and that won't be a problem. I would be happy to tour the property on "
                   "your behalf and send you a video, or perhaps we can view the home live together virtually "
                   "through Zoom or FaceTime! Are you free for a virtual showing tomorrow morning?",
        "keywords": ["out of town", "not in town", "virtual", "video"],
    },
    "not_ready": {
        "template": "I completely understand! I would be happy to represent you as your agent moving forward, "
                   "and when the time is right, we can certainly ramp up our search! When are you free to "
                   "tour this property?",
        "keywords": ["not ready", "year", "rent", "future"],
    }
}

ALM_QUESTIONS = {
    "appointment": [
        "When would you like to go see the property?",
        "Are you available tomorrow morning for a tour?",
        "Would you prefer an in-person showing or a virtual tour?",
        "What time works best for you to view the property?",
    ],
    "location": [
        "Are there any other properties you've been looking at?",
        "Are you only interested in this area, or are you open to seeing alternative locations and neighborhoods?",
        "What other neighborhoods are you considering?",
        "How far from this location would you be willing to look?",
    ],
    "motivation": [
        "What interests you about this property?",
        "How long have you been looking?",
        "Have you seen any other properties?",
        "What features are most important to you in a home?",
        "Are you currently renting or owning?",
        "Will you need to sell a home as well?",
    ]
}

CLOSING_TEMPLATES = {
    "appointment_set": {
        "template": "Thank you for taking the time to go over your home search needs! As soon as we're "
                   "off the call, I will reach out to the seller of this property, as well as a few others "
                   "that I think you'll really be interested in based on what we discussed. I will get back "
                   "to you shortly with appointment confirmations! The phone number I am showing for you is "
                   "{phone}, is that correct? Perfect, and the email I am showing is {email}, is that the "
                   "best email for you? Awesome, and what is your preferred method of communication? Great! "
                   "I will get back with you shortly, and I'm very excited to work with you!",
        "keywords": ["thank you", "confirmation", "contact", "excited"],
    },
    "nurture_lead": {
        "template": "Thank you for taking the time to speak with me today! I will be happy to set you up "
                   "on a search for properties that are similar to what we discussed, and we can keep an "
                   "eye on the market together. If you come across any other properties that you'd like to "
                   "discuss or would like to talk strategy for how and when to make a purchase in this "
                   "market, I am always happy to help! I am excited to work with you!",
        "keywords": ["thank you", "search", "market", "strategy", "excited"],
    }
}

# Phrases to avoid or flag as problematic during the first call
AVOID_PHRASES = [
    "not available",
    "already sold",
    "need pre-approval",
    "bad condition",
    "major issues",
    "act quickly",
    "losing the property",
    "market conditions",
    "financing",
    "credit score",
    "down payment",
    "let me check the MLS",
    "I'm not available",
    "can't do that time",
]

# Positive phrases to encourage
POSITIVE_PHRASES = [
    "excited to work with you",
    "happy to help",
    "absolutely",
    "definitely",
    "looking forward to",
    "great opportunity",
    "perfect",
    "wonderful",
]