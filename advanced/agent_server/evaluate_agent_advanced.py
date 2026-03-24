import asyncio
import logging
import re

import mlflow
from dotenv import load_dotenv
from mlflow.entities import Feedback, SpanType
from mlflow.genai.agent_server import get_invoke_function
from mlflow.genai.scorers import (
    Completeness,
    ConversationalSafety,
    ConversationCompleteness,
    Fluency,
    KnowledgeRetention,
    RelevanceToQuery,
    Safety,
    ToolCallCorrectness,
    ToolCallEfficiency,
    UserFrustration,
    scorer,
)
from mlflow.genai.simulators import ConversationSimulator
from mlflow.types.responses import ResponsesAgentRequest

# Load environment variables from .env if it exists
load_dotenv(dotenv_path=".env", override=True)
logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)

# need to import agent for our @invoke-registered function to be found
from agent_server import agent  # noqa: F401

# ---------------------------------------------------------------------------
# 20 FreshMart-specific test cases
# Covers: structured data (Genie), unstructured data (Vector Search),
#         mixed queries, and memory/personalization
# ---------------------------------------------------------------------------
test_cases = [
    # ── Structured Data Questions (Genie) ── 1-7
    {
        "goal": "Find out what organic produce items are currently in stock",
        "persona": "A health-conscious shopper who prefers organic products.",
        "simulation_guidelines": [
            "Ask what organic options are available in produce.",
            "Follow up by asking about prices for a few items.",
            "Prefer short messages",
        ],
    },
    {
        "goal": "Find out how much I spent at FreshMart last month",
        "persona": "A budget-conscious customer reviewing monthly expenses.",
        "simulation_guidelines": [
            "Ask about total spending last month.",
            "Ask for a breakdown by category or store visit.",
            "Prefer short messages",
        ],
    },
    {
        "goal": "Find which FreshMart store is closest to downtown Portland",
        "persona": "A new customer looking for a convenient store location.",
        "simulation_guidelines": [
            "Ask which stores are near downtown Portland.",
            "Ask about store hours and services available.",
            "Prefer short messages",
        ],
    },
    {
        "goal": "Find bakery items under $5",
        "persona": "A bargain hunter looking for affordable bakery treats.",
        "simulation_guidelines": [
            "Ask what bakery items are available under $5.",
            "Ask about the most popular ones.",
            "Prefer short messages",
        ],
    },
    {
        "goal": "Review my last 3 orders and see what I purchased",
        "persona": "A regular customer who wants to reorder items from recent purchases.",
        "simulation_guidelines": [
            "Ask to see recent order history.",
            "Ask for details on what items were in one of the orders.",
            "Prefer short messages",
        ],
    },
    {
        "goal": "Check what payment methods I have on file",
        "persona": "A customer preparing for a large purchase who wants to verify payment options.",
        "simulation_guidelines": [
            "Ask what payment methods are saved to the account.",
            "Ask if mobile pay is accepted.",
            "Prefer short messages",
        ],
    },
    {
        "goal": "Find out which Dairy products are running low on stock",
        "persona": "A customer who wants to buy dairy before items sell out.",
        "simulation_guidelines": [
            "Ask about dairy products with low stock.",
            "Ask when restocking typically happens.",
            "Prefer short messages",
        ],
    },
    # ── Unstructured Data Questions (Vector Search policies) ── 8-14
    {
        "goal": "Understand FreshMart's return policy for spoiled produce bought yesterday",
        "persona": "A frustrated customer who bought spoiled strawberries.",
        "simulation_guidelines": [
            "Describe the issue with the spoiled produce.",
            "Ask about the return window for perishable items.",
            "Ask how to get a refund without a receipt.",
        ],
    },
    {
        "goal": "Learn about the Gold membership tier benefits",
        "persona": "A Silver member considering whether to spend more to reach Gold status.",
        "simulation_guidelines": [
            "Ask what benefits Gold members get.",
            "Ask how much you need to spend to qualify.",
            "Ask about the points earn rate for Gold.",
        ],
    },
    {
        "goal": "Check if there are any recalls on spinach products",
        "persona": "A concerned parent who just fed spinach to their toddler.",
        "simulation_guidelines": [
            "Express concern and ask about spinach recalls.",
            "Ask what lot numbers or brands are affected.",
            "Ask what to do if you already consumed the product.",
        ],
    },
    {
        "goal": "Find out same-day delivery costs for a Silver member",
        "persona": "A Silver member who wants groceries delivered today.",
        "simulation_guidelines": [
            "Ask about same-day delivery options and fees.",
            "Ask about the minimum order amount for free delivery.",
            "Ask about delivery time windows.",
        ],
    },
    {
        "goal": "Understand FreshMart's price matching policy",
        "persona": "A savvy shopper who saw a competitor ad with a lower price.",
        "simulation_guidelines": [
            "Ask if FreshMart matches competitor prices.",
            "Ask about any restrictions or limits.",
            "Prefer short messages",
        ],
    },
    {
        "goal": "Find out the return window for frozen food items",
        "persona": "A customer who found freezer-burned ice cream bought 3 weeks ago.",
        "simulation_guidelines": [
            "Describe the freezer-burned ice cream issue.",
            "Ask about the return window for frozen items.",
            "Ask if a receipt is needed.",
        ],
    },
    {
        "goal": "Find out what happens when a delivery order has wrong items",
        "persona": "An upset customer who received the wrong groceries in a delivery.",
        "simulation_guidelines": [
            "Describe receiving wrong items in a delivery order.",
            "Ask about getting a refund or replacement.",
            "Ask about any courtesy credit or compensation.",
        ],
    },
    # ── Mixed Questions (structured + unstructured) ── 15-18
    {
        "goal": "Understand Gold member delivery benefits and browse available produce",
        "persona": "A Gold member planning a large grocery order with delivery.",
        "simulation_guidelines": [
            "Ask about delivery fee discounts for Gold members.",
            "Then ask what produce items are in stock.",
            "Ask about curbside pickup as an alternative.",
        ],
    },
    {
        "goal": "Check if CrunchTime peanut butter crackers are safe to eat",
        "persona": "A worried customer who has a child with a milk allergy and bought CrunchTime crackers.",
        "simulation_guidelines": [
            "Express concern about CrunchTime crackers and milk allergy.",
            "Ask if there is a recall on this product.",
            "Ask how to get a refund for the recalled item.",
        ],
    },
    {
        "goal": "Return an item without a receipt and understand the options",
        "persona": "A customer who lost the receipt for a non-perishable item purchased 2 weeks ago.",
        "simulation_guidelines": [
            "Explain you lost the receipt and want to return an item.",
            "Ask about no-receipt return limits and refund methods.",
            "Ask if the loyalty card purchase history can help.",
        ],
    },
    {
        "goal": "Find the best deals for a Platinum member shopping for organic products",
        "persona": "A loyal Platinum member who shops exclusively organic.",
        "simulation_guidelines": [
            "Ask about Platinum-exclusive benefits and discounts.",
            "Ask to see organic products currently available.",
            "Ask about the store-brand discount for Platinum members.",
        ],
    },
    # ── Memory & Personalization ── 19-20
    {
        "goal": "Save dietary preferences and get personalized product recommendations",
        "persona": "A customer with peanut allergy and gluten-free dietary needs.",
        "simulation_guidelines": [
            "Tell the assistant about peanut allergy and gluten-free preference.",
            "Ask the assistant to remember these preferences.",
            "Ask for product recommendations that fit these restrictions.",
        ],
    },
    {
        "goal": "Plan a dinner party for 8 people with ingredient help and store hours",
        "persona": "A home cook planning a weekend dinner party who needs help finding ingredients.",
        "simulation_guidelines": [
            "Describe the dinner party plan and ask for ingredient suggestions.",
            "Ask about availability of specific items in stock.",
            "Ask about store hours to plan the shopping trip.",
        ],
    },
]


# ---------------------------------------------------------------------------
# Custom Scorers
# ---------------------------------------------------------------------------

# Known policy-specific values from FreshMart policy documents.
# Used to check if the agent cites concrete details rather than being vague.
POLICY_KEYWORDS = [
    "48-hour", "48 hour", "90-day", "90 day", "30-day", "30 day",
    "7 day", "7-day", "$7.99", "$5.99", "$3.99",
    "$50", "$75", "$100", "$25", "$35",
    "bronze", "silver", "gold", "platinum",
    "1 point", "1.5 point", "2 point", "3 point",
    "100 points", "500 points", "1,000 points",
    "double fresh guarantee", "price promise",
    "sunbright", "happy farms", "crunchtime",
    "e. coli", "soy allergen", "milk allergen",
    "1-800-freshmt", "24 hours", "48 hours",
    "5-7 business days", "3-5 business days",
    "4:00 pm", "2:00 pm", "15 miles", "25 miles",
    "7:00 am", "10:00 pm", "8:00 am", "9:00 pm",
]


@scorer
def tool_routing_accuracy(*, outputs=None, trace=None) -> Feedback:
    """Check if the agent routes queries to the correct MCP tool.

    Genie (retail-grocery-genie) should be used for structured data queries
    (products, customers, transactions, stores, payments).
    Vector Search (retail-policy-docs) should be used for policy questions
    (returns, membership, delivery, recalls, privacy, customer service, store ops).
    """
    if trace is None:
        return Feedback(
            name="tool_routing_accuracy",
            value="unknown",
            rationale="No trace available to inspect tool calls.",
        )

    tool_spans = trace.search_spans(span_type=SpanType.TOOL)
    if not tool_spans:
        return Feedback(
            name="tool_routing_accuracy",
            value="no_tools",
            rationale="No tool calls were made during this interaction.",
        )

    tool_names = [span.name for span in tool_spans]

    used_genie = any("genie" in n.lower() for n in tool_names)
    used_vector = any(
        "vector" in n.lower() or "policy" in n.lower() or "search" in n.lower()
        for n in tool_names
    )
    used_memory = any("memory" in n.lower() for n in tool_names)

    tools_summary = ", ".join(set(tool_names))
    rationale_parts = []
    if used_genie:
        rationale_parts.append("Used Genie for structured data queries")
    if used_vector:
        rationale_parts.append("Used Vector Search for policy lookups")
    if used_memory:
        rationale_parts.append("Used memory tools for personalization")
    if not rationale_parts:
        rationale_parts.append("Used other tools")

    return Feedback(
        name="tool_routing_accuracy",
        value="yes" if (used_genie or used_vector or used_memory) else "no",
        rationale=f"Tools called: [{tools_summary}]. {'; '.join(rationale_parts)}.",
    )


@scorer
def policy_specificity(*, inputs=None, outputs=None) -> Feedback:
    """Check if the agent provides specific policy details rather than vague answers.

    Looks for concrete numbers, tier names, dollar amounts, time windows,
    and other specific policy values from FreshMart's policy documents.
    """
    if outputs is None:
        return Feedback(
            name="policy_specificity",
            value=0.0,
            rationale="No output to evaluate.",
        )

    # Extract text from output
    response_text = str(outputs).lower()

    # Count how many specific policy keywords appear
    found = [kw for kw in POLICY_KEYWORDS if kw.lower() in response_text]
    score = min(len(found) / 3.0, 1.0)  # 3+ specific details = perfect score

    if not found:
        rationale = "Response contained no specific policy details (numbers, tiers, dollar amounts, time windows)."
    else:
        rationale = f"Found {len(found)} specific policy detail(s): {', '.join(found[:5])}."

    return Feedback(
        name="policy_specificity",
        value=score,
        rationale=rationale,
    )


@scorer
def retail_tone_appropriateness(*, inputs=None, outputs=None) -> Feedback:
    """Evaluate if the response maintains a friendly, professional retail customer service tone.

    Checks for: empathy toward complaints, no blame on the customer,
    actionable next steps, and warm/helpful language.
    """
    if outputs is None:
        return Feedback(
            name="retail_tone_appropriateness",
            value=0.0,
            rationale="No output to evaluate.",
        )

    response_text = str(outputs).lower()

    score = 0.0
    reasons = []

    # Check for empathetic language
    empathy_phrases = [
        "sorry", "apologize", "understand", "appreciate", "happy to help",
        "glad to", "let me help", "i can help", "no worries", "of course",
        "absolutely", "certainly", "great question",
    ]
    empathy_count = sum(1 for p in empathy_phrases if p in response_text)
    if empathy_count > 0:
        score += 0.35
        reasons.append(f"Empathetic language detected ({empathy_count} phrases)")
    else:
        reasons.append("No empathetic language detected")

    # Check for actionable next steps
    action_phrases = [
        "you can", "to do this", "here's how", "steps", "visit",
        "contact", "call", "bring", "return", "check",
        "i recommend", "i suggest",
    ]
    action_count = sum(1 for p in action_phrases if p in response_text)
    if action_count > 0:
        score += 0.35
        reasons.append(f"Actionable guidance provided ({action_count} phrases)")
    else:
        reasons.append("No actionable guidance found")

    # Check for warm/helpful tone (greeting, closing, personalization)
    warm_phrases = [
        "welcome", "thank you", "thanks", "enjoy", "have a great",
        "anything else", "let me know", "feel free", "is there anything",
    ]
    warm_count = sum(1 for p in warm_phrases if p in response_text)
    if warm_count > 0:
        score += 0.30
        reasons.append(f"Warm/helpful closing or opening ({warm_count} phrases)")
    else:
        reasons.append("No warm/helpful tone markers found")

    # Penalize for blame language
    blame_phrases = [
        "your fault", "you should have", "you failed", "that's your problem",
        "not our responsibility", "you were wrong",
    ]
    blame_count = sum(1 for p in blame_phrases if p in response_text)
    if blame_count > 0:
        score = max(score - 0.5, 0.0)
        reasons.append(f"PENALTY: Blame language detected ({blame_count} phrases)")

    return Feedback(
        name="retail_tone_appropriateness",
        value=round(score, 2),
        rationale="; ".join(reasons),
    )


# ---------------------------------------------------------------------------
# Simulator & Predict Function
# ---------------------------------------------------------------------------

simulator = ConversationSimulator(
    test_cases=test_cases,
    max_turns=5,
    user_model="databricks:/databricks-claude-sonnet-4-5",
)

# Get the invoke function that was registered via @invoke decorator in your agent
invoke_fn = get_invoke_function()
assert invoke_fn is not None, (
    "No function registered with the `@invoke` decorator found."
    "Ensure you have a function decorated with `@invoke()`."
)

# if invoke function is async, wrap it in a sync function.
# The simulator may already be running an event loop, so we use nest_asyncio
# to allow nested run_until_complete() calls without deadlocking.
if asyncio.iscoroutinefunction(invoke_fn):
    import nest_asyncio

    nest_asyncio.apply()

    def predict_fn(input: list[dict], **kwargs) -> dict:
        req = ResponsesAgentRequest(input=input)
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(invoke_fn(req))
        return response.model_dump()
else:

    def predict_fn(input: list[dict], **kwargs) -> dict:
        req = ResponsesAgentRequest(input=input)
        response = invoke_fn(req)
        return response.model_dump()


def evaluate():
    mlflow.genai.evaluate(
        data=simulator,
        predict_fn=predict_fn,
        scorers=[
            # Predefined scorers
            Completeness(),
            ConversationCompleteness(),
            ConversationalSafety(),
            KnowledgeRetention(),
            UserFrustration(),
            Fluency(),
            RelevanceToQuery(),
            Safety(),
            ToolCallCorrectness(),
            ToolCallEfficiency(),
            # Custom scorers
            tool_routing_accuracy,
            policy_specificity,
            retail_tone_appropriateness,
        ],
    )
