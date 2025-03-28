"""
Marketing Brief Validator Agent using LangGraph.

This module implements a LangGraph-based agent that validates marketing briefs
by checking for required information and providing warnings for missing or
incomplete data.
"""

from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import tools_condition, ToolNode
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Initialize OpenAI client
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0
)

# State Structure
class BriefState(TypedDict):
    """State structure for the brief validation process."""
    messages: List[HumanMessage]
    extracted_info: Dict[str, str]
    missing_critical: List[str]
    missing_non_critical: List[str]
    validation_warnings: List[str]
    report: str 


# Lets add the pdf to ocr and then extract the text from the pdf and also parse it into html tables for better readability for the LLM.
# Also maybe pedantic might be usefull for the LLM to be more precise and not hallucinate.
def extract_brief_info(text: str) -> Dict[str, str]:
    """Extract information from the brief text using LLM."""
    extraction_prompt = f"""
    Your task is to extract specific information from a marketing brief and return it in JSON format.
    If any information is not explicitly mentioned in the brief, mark it as "MISSING".
    
    Required format:
    {{
        "client": "string or MISSING",
        "brand": "string or MISSING",
        "product": "string or MISSING",
        "campaign": "string or MISSING",
        "date": "string or MISSING",
        "deadline": "string or MISSING",
        "creative_agency": "our/external or MISSING",
        "business_team": "BD1/BD2/BD3/etc or MISSING",
        "budget": "number with currency or MISSING",
        "languages": "Czech/English or MISSING",
        "period": "time range or MISSING",
        "target_audience": "string or MISSING",
        "campaign_target": "string or MISSING"
    }}
    
    Rules:
    1. Only extract information that is explicitly stated
    2. Do not make assumptions or infer information
    3. Return exactly the keys shown above
    4. Format must be valid JSON
    5. Do not include markdown code block markers
    6. For Czech briefs:
       - Client is under "Subjekt / Klient"
       - Campaign is under "Název kampaně"
       - Target audience is under "Cílová skupina (CS)"
       - Period is under "Timing kampaně"
       - Campaign target is under "Cíl kampaně"
       - Budget is under "Rozpočet (vč. DPH) podle mediatypů" - sum up all media types with values
       - Deadline is under "Deadline pro potenciální nedotáčky"
       - If the brief is in Czech, set languages to "Czech"
    7. For budget:
       - Sum up all media types that have numerical values
       - Convert any numbers to a simple format (e.g., "8255192 Kč")
       - Ignore entries marked with 'x' or empty values
    8. For deadline:
       - If specified as "+X days", convert to a clear statement like "2 days after campaign start"
    9. For target audience:
       - Include both age range and demographic segments
    10. For campaign target:
        - Extract specific metrics or goals mentioned
    
    Brief text:
    {text}
    """
    
    messages = [
        SystemMessage(content="You are a precise information extraction assistant. Extract only the requested information and mark missing items as 'MISSING'. Return only the JSON object without any markdown formatting."),
        HumanMessage(content=extraction_prompt)
    ]
    
    response = llm.invoke(messages)
    try:
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] 
        if content.endswith("```"):
            content = content.rsplit("\n", 1)[0]  
        if content.startswith("json"):
            content = content.split("\n", 1)[1]  
        content = content.strip()
        
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON response from LLM - {str(e)}")
        print("Response content:", response.content)
        return {}

def validate_extracted_info(info: Dict[str, str]) -> tuple[List[str], List[str], List[str], Dict[str, str]]:
    """Validate the extracted information and return warnings."""
    missing_critical = []
    missing_non_critical = []
    validation_warnings = []
    critical_explanations = {
        "budget": "Budget is crucial for planning media mix and determining campaign scope. Without it, we cannot allocate resources effectively or ensure ROI.",
        "languages": "Language specification is essential for content creation and media planning. It affects creative development, media buying, and campaign effectiveness.",
        "period": "Campaign period is vital for timing, media planning, and resource allocation. It helps ensure all deliverables are properly scheduled.",
        "target_audience": "Target audience definition is fundamental for creative development and media planning. It ensures the campaign reaches the right people with the right message.",
        "campaign_target": "Campaign target defines success metrics and objectives. Without it, we cannot measure campaign effectiveness or align team efforts."
    }
    
    
    critical_fields = ["budget", "languages", "period", "target_audience", "campaign_target"]
    non_critical_fields = ["client", "brand", "product", "campaign", "date", "deadline", 
                         "creative_agency", "business_team"]
    
    
    missing_critical_with_explanations = {}
    for field in critical_fields:
        if field not in info or info[field] == "MISSING":
            missing_critical.append(field)
            missing_critical_with_explanations[field] = critical_explanations[field]
    
    
    for field in non_critical_fields:
        if field not in info or info[field] == "MISSING":
            missing_non_critical.append(field)
     
    
    if "budget" in info and info["budget"] != "MISSING":
        
        budget_str = info["budget"].replace(" ", "").replace("Kč", "").strip()
        try:
            float(budget_str)
        except ValueError:
            validation_warnings.append("Budget format is invalid. Please provide a valid number.")
    
    if "languages" in info and info["languages"] != "MISSING":
        valid_languages = ["Czech", "English"]
        if not any(lang in info["languages"] for lang in valid_languages):
            validation_warnings.append("Languages should be either Czech or English.")
    
    if "creative_agency" in info and info["creative_agency"] != "MISSING":
        if info["creative_agency"].lower() not in ["our", "external"]:
            validation_warnings.append("Creative agency should be specified as 'our' or 'external'.")
    
    if "business_team" in info and info["business_team"] != "MISSING":
        if not info["business_team"].startswith("BD"):
            validation_warnings.append("Business team should be specified as BD1, BD2, BD3, etc.")
    
    
    if "period" in info and info["period"] != "MISSING":
        if not any(char.isdigit() for char in info["period"]):
            validation_warnings.append("Period should include specific dates or time range.")
    
    if "target_audience" in info and info["target_audience"] != "MISSING":
        if not any(char.isdigit() for char in info["target_audience"]):
            validation_warnings.append("Target audience should include age range or demographic segments.")
    
    if "campaign_target" in info and info["campaign_target"] != "MISSING":
        if not any(char.isdigit() for char in info["campaign_target"]):
            validation_warnings.append("Campaign target should include specific metrics or goals.")
    
    return missing_critical, missing_non_critical, validation_warnings, missing_critical_with_explanations

def process_brief(state: BriefState) -> BriefState:
    """Process the brief and extract information."""
    
    brief_text = state["messages"][-1].content
    
    
    state["extracted_info"] = extract_brief_info(brief_text)
    
    
    missing_critical, missing_non_critical, validation_warnings, critical_explanations = validate_extracted_info(state["extracted_info"])
    
    state["missing_critical"] = missing_critical
    state["missing_non_critical"] = missing_non_critical
    state["validation_warnings"] = validation_warnings
    
    return state

def generate_report(state: BriefState) -> BriefState:
    """Generate a report of missing information and warnings."""
    report = []
    
    if state["missing_critical"]:
        report.append("CRITICAL INFORMATION MISSING:")
        for item in state["missing_critical"]:
            report.append(f"- {item.replace('_', ' ').title()}")
    
    if state["missing_non_critical"]:
        report.append("\nNON-CRITICAL INFORMATION MISSING:")
        for item in state["missing_non_critical"]:
            report.append(f"- {item.replace('_', ' ').title()}")
    
    if state["validation_warnings"]:
        report.append("\nVALIDATION WARNINGS:")
        for warning in state["validation_warnings"]:
            report.append(f"- {warning}")
    
    if not report:
        report.append("All required information is present and valid!")
    
    state["report"] = "\n".join(report)
    return state

def create_brief_validator_graph():
    """Create and return the brief validator graph."""
    builder = StateGraph(BriefState)
    
    
    builder.add_node("process", process_brief)
    builder.add_node("generate_report", generate_report)
    
 
    builder.add_edge(START, "process")
    builder.add_edge("process", "generate_report")
    builder.add_edge("generate_report", END)
    
    return builder.compile()

def validate_brief(brief_text: str) -> Dict[str, List[str]]:
    """Validate a marketing brief and return missing information and warnings."""

    graph = create_brief_validator_graph()
    
   
    initial_state = {
        "messages": [HumanMessage(content=brief_text)],
        "extracted_info": {},
        "missing_critical": [],
        "missing_non_critical": [],
        "validation_warnings": [],
        "report": ""
    }

    final_state = graph.invoke(initial_state)
    

    critical_explanations = {
        "budget": "Budget is required to determine campaign scope and feasibility",
        "languages": "Languages must be specified as either Czech or English",
        "period": "Campaign period must include specific dates or time range",
        "target_audience": "Target audience must include age range or demographic segments",
        "campaign_target": "Campaign target must include specific metrics or goals"
    }
    
 
    result = {
        "missing_critical": [
            {
                "field": field.replace("_", " ").title(),
                "explanation": critical_explanations[field]
            }
            for field in final_state["missing_critical"]
        ],
        "missing_non_critical": [field.replace("_", " ").title() for field in final_state["missing_non_critical"]],
        "validation_warnings": final_state["validation_warnings"]
    }
    
    return result

if __name__ == "__main__":
    
    example_brief = """
    We need a marketing campaign for our new product launch.
    The campaign should target young professionals and increase brand awareness.
    Budget is 50,000 EUR.
    We want to run it in Czech and English.
    The campaign period is Q2 2024.
    """
    
    report = validate_brief(example_brief)
    print("\nBrief Validation Report:")
    print(report) 