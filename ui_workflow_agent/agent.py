from google.adk.agents.llm_agent import Agent
from google.genai import types
from ui_workflow_agent.tools.mcp_tools import invoke_browser_use_tool
from ui_workflow_agent.tools.mcp_devtools_client import navigate_to_url, fill_input, click, search_and_click
from domain.messages import AidinExtractedData
#from google.adk.models.lite_llm import LiteLlm

model = "gemini-2.5-flash"
#model = LiteLlm(model="ollama_chat/mistral-small3.1")

safety_settings = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.OFF,
    ),
]

content_config = types.GenerateContentConfig(
   safety_settings=safety_settings,
   temperature=0.28,
   max_output_tokens=10000,
   top_p=0.95,
)

root_agent = Agent(
    model=model,
    name='data_extractor_agent',
    description='An agent to extract data from unstructured medical information and convert it into structured JSON format.',
    instruction='Use the appropriate tools to extract data as needed.',
    generate_content_config=content_config,
    # output_schema=AidinExtractedData,
    # output_key='data_extractor_output'
)

