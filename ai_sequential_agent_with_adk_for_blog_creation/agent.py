from google.adk.agents import SequentialAgent
from ai_sequential_agent_with_adk_for_blog_creation.AgentTool import *
from google.adk.tools import AgentTool

root_agent = SequentialAgent(
    name="BlogPipeline",
    sub_agents=[outline_agent, writer_agent, editor_agent]
)
print("✅ Sequential Agent created.")
