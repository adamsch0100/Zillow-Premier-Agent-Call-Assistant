"""
Test script for the Real Estate Call Assistant conversation flow.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.conversation_analyzer import ConversationAnalyzer, ConversationStage, ObjectionType

def test_basic_conversation_flow():
    """Test a basic successful conversation flow."""
    analyzer = ConversationAnalyzer()
    
    # Test opening
    result = analyzer.analyze_speech(
        "Hi, this is John with ABC Realty, am I speaking with Sarah?",
        "agent"
    )
    assert result['suggestion_type'] == 'alm_question'
    assert analyzer.state.stage == ConversationStage.APPOINTMENT
    
    # Test appointment setting
    result = analyzer.analyze_speech(
        "Yes, I would love to see it tomorrow afternoon",
        "client"
    )
    assert analyzer.state.stage == ConversationStage.LOCATION
    assert analyzer.state.appointment_set == True
    
    # Test location discussion
    result = analyzer.analyze_speech(
        "I'm interested in this area and maybe the north side as well",
        "client"
    )
    assert analyzer.state.stage == ConversationStage.MOTIVATION
    assert analyzer.state.location_discussed == True
    
    # Test motivation discovery
    result = analyzer.analyze_speech(
        "We're looking to upgrade because we need more space for our growing family",
        "client"
    )
    assert analyzer.state.stage == ConversationStage.CLOSING
    assert analyzer.state.motivation_uncovered == True
    
    # Test closing
    result = analyzer.analyze_speech(
        "Perfect! I'm excited to work with you and show you the property tomorrow!",
        "agent"
    )
    assert result['suggestion_type'] == 'end_call'

def test_objection_handling():
    """Test handling of common objections."""
    analyzer = ConversationAnalyzer()
    
    # Test listing agent objection
    result = analyzer.analyze_speech(
        "I'd rather speak with the listing agent directly",
        "client"
    )
    assert result['suggestion_type'] == 'objection_handler'
    assert ObjectionType.LISTING_AGENT in analyzer.detected_objections
    
    # Test working with another agent
    result = analyzer.analyze_speech(
        "I'm already working with another agent",
        "client"
    )
    assert result['suggestion_type'] == 'objection_handler'
    assert ObjectionType.WORKING_WITH_AGENT in analyzer.detected_objections
    
    # Test quick question objection
    result = analyzer.analyze_speech(
        "I just have a quick question about the property",
        "client"
    )
    assert result['suggestion_type'] == 'objection_handler'
    assert ObjectionType.QUICK_QUESTION in analyzer.detected_objections

def test_warning_phrases():
    """Test detection of phrases to avoid."""
    analyzer = ConversationAnalyzer()
    
    result = analyzer.analyze_speech(
        "Let me check your credit score and discuss financing options",
        "agent"
    )
    assert len(result.get('warnings', [])) > 0
    
    result = analyzer.analyze_speech(
        "The property is not available and already sold",
        "agent"
    )
    assert len(result.get('warnings', [])) > 0

if __name__ == "__main__":
    print("Running conversation flow tests...")
    test_basic_conversation_flow()
    print("✓ Basic conversation flow test passed")
    
    test_objection_handling()
    print("✓ Objection handling test passed")
    
    test_warning_phrases()
    print("✓ Warning phrases test passed")
    
    print("\nAll tests passed successfully!")