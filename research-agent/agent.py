import os
from dotenv import load_dotenv
import sys
import warnings
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search
from google.adk.runners import InMemoryRunner
from google.adk.plugins.logging_plugin import (
    LoggingPlugin,
)  # <---- 1. Import the Plugin
from google.genai import types
import asyncio

from google.genai import types
from typing import List

# --- Load environment variables from .env file ---
# This line finds the .env file and loads its contents into os.environ
load_dotenv()

# The Google ADK/GenAI client will automatically look for this key.
# However, you can verify it loaded or access it manually:
api_key_value = os.getenv("GOOGLE_API_KEY")

if not api_key_value:
    print("FATAL ERROR: GOOGLE_API_KEY environment variable not found.")
    # You might want to exit or raise an error here
    exit()

# Suppress aiohttp warnings about unclosed sessions
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed client session")
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed connector")

retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)


def count_papers(papers: List[str]):
    """
    This function counts the number of papers in a list of strings.
    Args:
      papers: A list of strings, where each string is a research paper.
    Returns:
      The number of papers in the list.
    """
    return len(papers)


# Google search agent
google_search_agent = LlmAgent(
    name="google_search_agent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    description="Searches for information using Google search",
    instruction="Use the google_search tool to find information on the given topic. Return the raw search results.",
    tools=[google_search],
)

# Root agent
root_agent = LlmAgent(
    name="research_paper_finder_agent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""Your task is to find research papers and count them. 

   You must follow these steps:
   1) Find research papers on the user provided topic using the 'google_search_agent'. 
   2) Then, pass the papers to 'count_papers' tool to count the number of papers returned.
   3) Return both the list of research papers and the total number of papers.
   """,
    tools=[AgentTool(agent=google_search_agent), count_papers],
)

print("✅ Agent created")

# --- Runner Setup ---
# The LoggingPlugin is correctly passed to the Runner, not the Agent.
runner = InMemoryRunner(
    agent=root_agent,
    plugins=[
        LoggingPlugin()
    ],  # <---- 2. Add the plugin. Handles standard Observability logging across ALL agents
)

print("✅ Runner configured")


async def main(query: str):
    """Runs the agent with the provided query and prints the final result."""
    print("🚀 Running agent with LoggingPlugin...")
    print("📊 Watch the comprehensive logging output below:\n")
    print(f"User Query: {query}")
    try:
        # runner.run_debug() returns a list of events.
        # We rename the variable to 'events' for clarity.
        events = await runner.run_debug(query)

        final_response_text = "No final response found."

        # Iterate through the list of events to find the final response
        for event in events:
            # Check if the event is the final response intended for the user
            if event.is_final_response():
                # The final response event is a Content object, so we extract the text
                if event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text
                    break  # Found the final answer, so stop iterating
        # --- Client Cleanup ---

        # 1. Close the root agent's client
        root_client = root_agent.model.api_client
        if root_client is not None:
            try:
                await root_client.close()
            except Exception:
                # Added a try/except just in case the client object is valid but failed to close
                pass

        # 2. Close the sub-agent's client
        sub_agent_client = google_search_agent.model.api_client
        if sub_agent_client is not None:
            try:
                await sub_agent_client.close()
            except Exception:
                pass

    finally:
        # 3. Ensure the Runner itself is closed (if it has a close method)
        # Note: Check ADK documentation, but many async runners/services require cleanup.
        if hasattr(runner, 'close'):
            await runner.close()

    print("\n--- Final Agent Response ---")
    # Print the extracted text
    print(final_response_text)
    print("----------------------------")


# --- Command Line Entry Point ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        # If no argument is passed, use a default query
        default_query = "Find recent papers on large language model safety and count them."
        print(f"⚠️ No query provided. Using default: '{default_query}'")
        query_to_run = default_query
    else:
        # The query is the argument passed after the script name
        query_to_run = " ".join(sys.argv[1:])

    # Run the main asynchronous function
    asyncio.run(main(query_to_run))

    print("✅ Script execution finished.")