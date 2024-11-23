import pytest
import asyncio
from datetime import datetime
from src.backend.app.services.openai_service import AIService, SuggestionRequest
from src.backend.app.services.suggestion_generator import SuggestionGenerator, ConversationContext

# Common Zillow lead scenarios
SCENARIOS = {
    "just_looking": {
        "conversation": [
            {"speaker": "agent", "text": "Hi, this is John with ABC Realty. I saw you were interested in the property on 123 Main Street. Is now a good time to talk?"},
            {"speaker": "customer", "text": "Yeah, I was just browsing Zillow and wanted to see what's out there. I'm not really serious about buying yet."},
        ],
        "property_details": {
            "address": "123 Main Street",
            "price": "$450,000",
            "bedrooms": "4",
            "bathrooms": "2.5",
            "sqft": "2,500",
            "year_built": "2010"
        },
        "agent_info": {
            "name": "John Smith",
            "brokerage": "ABC Realty",
            "experience": "10 years",
            "specialization": "Residential Properties"
        }
    },
    "price_objection": {
        "conversation": [
            {"speaker": "agent", "text": "Hi, this is Sarah from XYZ Homes. I noticed you were looking at our listing on Oak Avenue. Would you like to learn more about it?"},
            {"speaker": "customer", "text": "Yes, but I saw the price and it seems really high for the area. I'm not sure if it's within my budget."},
        ],
        "property_details": {
            "address": "456 Oak Avenue",
            "price": "$550,000",
            "bedrooms": "3",
            "bathrooms": "2",
            "sqft": "2,200",
            "year_built": "2015"
        },
        "agent_info": {
            "name": "Sarah Johnson",
            "brokerage": "XYZ Homes",
            "experience": "5 years",
            "specialization": "Luxury Properties"
        }
    },
    "already_has_agent": {
        "conversation": [
            {"speaker": "agent", "text": "Hello, this is Mike with Best Homes Realty. I saw you were interested in the Colonial house on Pine Street. Is this a good time?"},
            {"speaker": "customer", "text": "Oh, actually I'm already working with an agent. They just haven't shown me anything I like yet."},
        ],
        "property_details": {
            "address": "789 Pine Street",
            "price": "$625,000",
            "bedrooms": "5",
            "bathrooms": "3",
            "sqft": "3,000",
            "year_built": "2005"
        },
        "agent_info": {
            "name": "Mike Wilson",
            "brokerage": "Best Homes Realty",
            "experience": "15 years",
            "specialization": "Luxury Properties"
        }
    },
    "needs_to_sell_first": {
        "conversation": [
            {"speaker": "agent", "text": "Hi, this is Lisa from Premier Properties. I saw your interest in the Maple Drive property. Do you have a few minutes to chat?"},
            {"speaker": "customer", "text": "Yes, but we need to sell our current home first before we can buy anything new. We're not sure about the timing."},
        ],
        "property_details": {
            "address": "321 Maple Drive",
            "price": "$475,000",
            "bedrooms": "4",
            "bathrooms": "2",
            "sqft": "2,300",
            "year_built": "2012"
        },
        "agent_info": {
            "name": "Lisa Brown",
            "brokerage": "Premier Properties",
            "experience": "8 years",
            "specialization": "Residential Properties"
        }
    }
}

@pytest.mark.asyncio
async def test_suggestion_quality():
    """Test the quality of suggestions for different scenarios."""
    suggestion_generator = SuggestionGenerator()
    results = {}

    for scenario_name, scenario_data in SCENARIOS.items():
        # Create conversation context
        context = ConversationContext(
            transcript="\n".join([f"{msg['speaker']}: {msg['text']}" for msg in scenario_data['conversation']]),
            last_segment=scenario_data['conversation'][-1]['text'],
            conversation_history=scenario_data['conversation'],
            property_details=scenario_data['property_details'],
            agent_info=scenario_data['agent_info']
        )

        # Generate suggestions
        suggestions = await suggestion_generator.generate_suggestions(context)
        
        # Analyze conversation
        analysis = await suggestion_generator.analyze_conversation(context)
        
        results[scenario_name] = {
            "analysis": analysis,
            "suggestions": suggestions,
            "context": context
        }

    return results

@pytest.mark.asyncio
async def test_objection_handling():
    """Test the system's ability to identify and handle common objections."""
    suggestion_generator = SuggestionGenerator()
    objection_results = {}

    for scenario_name, scenario_data in SCENARIOS.items():
        context = ConversationContext(
            transcript="\n".join([f"{msg['speaker']}: {msg['text']}" for msg in scenario_data['conversation']]),
            last_segment=scenario_data['conversation'][-1]['text'],
            conversation_history=scenario_data['conversation']
        )

        analysis = await suggestion_generator.analyze_conversation(context)
        objection_results[scenario_name] = {
            "identified_objections": analysis.get("objections", []),
            "interest_level": analysis.get("interest_level", "unknown"),
            "conversation_stage": analysis.get("stage", "unknown")
        }

    return objection_results

@pytest.mark.asyncio
async def test_conversation_flow():
    """Test the system's ability to maintain conversation flow and context."""
    suggestion_generator = SuggestionGenerator()
    flow_results = {}

    for scenario_name, scenario_data in SCENARIOS.items():
        conversation_history = scenario_data['conversation'].copy()
        context = ConversationContext(
            transcript="\n".join([f"{msg['speaker']}: {msg['text']}" for msg in conversation_history]),
            last_segment=conversation_history[-1]['text'],
            conversation_history=conversation_history,
            property_details=scenario_data['property_details'],
            agent_info=scenario_data['agent_info']
        )

        # Generate initial suggestions
        suggestions = await suggestion_generator.generate_suggestions(context)
        
        # Simulate selecting and using the first suggestion
        if suggestions:
            conversation_history.append({
                "speaker": "agent",
                "text": suggestions[0]["text"]
            })
            
            # Add simulated customer response based on scenario
            if scenario_name == "just_looking":
                conversation_history.append({
                    "speaker": "customer",
                    "text": "Well, I might be interested in seeing it, but I'm really just starting my search."
                })
            elif scenario_name == "price_objection":
                conversation_history.append({
                    "speaker": "customer",
                    "text": "I was thinking something more in the $450,000 range."
                })

            # Generate follow-up suggestions
            context.conversation_history = conversation_history
            context.last_segment = conversation_history[-1]['text']
            context.transcript = "\n".join([f"{msg['speaker']}: {msg['text']}" for msg in conversation_history])
            
            follow_up_suggestions = await suggestion_generator.generate_suggestions(context)
            
            flow_results[scenario_name] = {
                "initial_suggestion": suggestions[0],
                "customer_response": conversation_history[-1]['text'],
                "follow_up_suggestions": follow_up_suggestions
            }

    return flow_results

async def run_all_tests():
    """Run all tests and return comprehensive results."""
    results = {
        "suggestion_quality": await test_suggestion_quality(),
        "objection_handling": await test_objection_handling(),
        "conversation_flow": await test_conversation_flow()
    }
    return results

def analyze_test_results(results):
    """Analyze test results and provide recommendations for improvement."""
    analysis = {
        "strengths": [],
        "weaknesses": [],
        "recommendations": []
    }
    
    # Analyze suggestion quality
    for scenario, data in results["suggestion_quality"].items():
        suggestions = data["suggestions"]
        if suggestions and len(suggestions) >= 3:
            analysis["strengths"].append(f"Generated multiple suggestions for {scenario}")
        else:
            analysis["weaknesses"].append(f"Limited suggestions for {scenario}")

    # Analyze objection handling
    objection_accuracy = 0
    total_scenarios = len(results["objection_handling"])
    for scenario, data in results["objection_handling"].items():
        if data["identified_objections"]:
            objection_accuracy += 1
    
    objection_accuracy_rate = objection_accuracy / total_scenarios
    if objection_accuracy_rate >= 0.8:
        analysis["strengths"].append("Strong objection identification")
    else:
        analysis["weaknesses"].append("Needs improvement in objection identification")
        analysis["recommendations"].append("Enhance objection detection patterns")

    # Analyze conversation flow
    for scenario, data in results["conversation_flow"].items():
        if "follow_up_suggestions" in data and data["follow_up_suggestions"]:
            analysis["strengths"].append(f"Maintained context in {scenario}")
        else:
            analysis["weaknesses"].append(f"Lost context in {scenario}")

    # Generate recommendations
    if analysis["weaknesses"]:
        for weakness in analysis["weaknesses"]:
            if "objection" in weakness.lower():
                analysis["recommendations"].append("Add more objection patterns and responses")
            elif "context" in weakness.lower():
                analysis["recommendations"].append("Improve context retention between exchanges")
            elif "suggestion" in weakness.lower():
                analysis["recommendations"].append("Expand suggestion templates and dynamic generation")

    return analysis

if __name__ == "__main__":
    results = asyncio.run(run_all_tests())
    analysis = analyze_test_results(results)
    print("\nTest Results Analysis:")
    print("\nStrengths:")
    for strength in analysis["strengths"]:
        print(f"✓ {strength}")
    print("\nWeaknesses:")
    for weakness in analysis["weaknesses"]:
        print(f"⚠ {weakness}")
    print("\nRecommendations:")
    for recommendation in analysis["recommendations"]:
        print(f"→ {recommendation}")