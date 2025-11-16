import requests
import os
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types # For creating response content
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from typing import Optional, Dict, Any # For type hints

# Use one of the model constants defined earlier
MODEL_GEMINI_2_0_FLASH = "gemini-2.0-flash"

# @title Define the get_weather Tool
API_KEY = os.environ.get("OPENWEATHERMAP_API_KEY", "OPENWEATHERMAP_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

def get_weather_real(city: str, tool_context: ToolContext) -> dict:
    """Retrieves live weather, converts temp unit based on session state."""
    print(f"--- Tool: get_weather_real called for {city} ---")

    # --- Read preference from state ---
    # Default to Fahrenheit if not set
    preferred_unit = tool_context.state.get("user_preference_temperature_unit", "Fahrenheit")
    print(f"--- Tool: Reading state 'user_preference_temperature_unit': {preferred_unit} ---")

    # OpenWeatherMap uses 'metric' (Celsius) or 'imperial' (Fahrenheit)
    units_param = "imperial" if preferred_unit == "Fahrenheit" else "metric"

    params = {
        'q': city,
        'limit': 1,
        'appid': API_KEY,
        'units': units_param
    }

    try:
        # --- 1. Make the API Request ---
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        print(f"{data}")

        # --- 2. Parse the Live Data ---
        temp_value = data['main']['temp']
        condition = data['weather'][0]['description']

        # Determine the display unit symbol
        temp_unit = "°F" if units_param == "imperial" else "°C"

        # --- 3. Format Report and Update State ---
        report = (
            f"The weather in {city.capitalize()} is **{condition.capitalize()}** "
            f"with a temperature of **{temp_value:.1f}{temp_unit}**."
        )
        result = {"status": "success", "report": report}
        print(f"--- Tool: Generated report in {preferred_unit}. Result: {result} ---")

        # Update state with the city that was successfully checked
        tool_context.state["last_city_checked_stateful"] = city
        return result

    except requests.exceptions.HTTPError as e:
        # Handle specific API errors (e.g., 404 for city not found)
        error_msg = f"Weather API error for '{city}': {e}. Check the city name."
        print(f"--- Tool Error: HTTP Error - {error_msg} ---")
        return {"status": "error", "error_message": error_msg}

    except requests.exceptions.RequestException as e:
        # Handle connection errors (network down, DNS failure, etc.)
        error_msg = f"A network error occurred while fetching weather: {e}"
        print(f"--- Tool Error: Network Error - {error_msg} ---")
        return {"status": "error", "error_message": error_msg}

    except KeyError:
        # Handle unexpected JSON structure if the API response changes
        error_msg = f"Could not parse weather data for {city}. Response structure was unexpected."
        print(f"--- Tool Error: Parsing Error - {error_msg} ---")
        return {"status": "error", "error_message": error_msg}

def say_hello(name: Optional[str] = None) -> str:
    """Provides a simple greeting. If a name is provided, it will be used.

    Args:
        name (str, optional): The name of the person to greet. Defaults to a generic greeting if not provided.

    Returns:
        str: A friendly greeting message.
    """
    if name:
        greeting = f"Hello, {name}!"
        print(f"--- Tool: say_hello called with name: {name} ---")
    else:
        greeting = "Hello there!" # Default greeting if name is None or not explicitly passed
        print(f"--- Tool: say_hello called without a specific name (name_arg_value: {name}) ---")
    return greeting

def say_goodbye() -> str:
    """Provides a simple farewell message to conclude the conversation."""
    print(f"--- Tool: say_goodbye called ---")
    return "Goodbye! Have a great day."


def block_keyword_guardrail(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Inspects the latest user message for 'BLOCK'. If found, blocks the LLM call
    and returns a predefined LlmResponse. Otherwise, returns None to proceed.
    """
    agent_name = callback_context.agent_name # Get the name of the agent whose model call is being intercepted
    print(f"--- Callback: block_keyword_guardrail running for agent: {agent_name} ---")

    # Extract the text from the latest user message in the request history
    last_user_message_text = ""
    if llm_request.contents:
        # Find the most recent message with role 'user'
        for content in reversed(llm_request.contents):
            if content.role == 'user' and content.parts:
                # Assuming text is in the first part for simplicity
                if content.parts[0].text:
                    last_user_message_text = content.parts[0].text
                    break # Found the last user message text

    print(f"--- Callback: Inspecting last user message: '{last_user_message_text[:100]}...' ---") # Log first 100 chars

    # --- Guardrail Logic ---
    keyword_to_block = "BLOCK"
    if keyword_to_block in last_user_message_text.upper(): # Case-insensitive check
        print(f"--- Callback: Found '{keyword_to_block}'. Blocking LLM call! ---")
        # Optionally, set a flag in state to record the block event
        callback_context.state["guardrail_block_keyword_triggered"] = True
        print(f"--- Callback: Set state 'guardrail_block_keyword_triggered': True ---")

        # Construct and return an LlmResponse to stop the flow and send this back instead
        return LlmResponse(
            content=types.Content(
                role="model", # Mimic a response from the agent's perspective
                parts=[types.Part(text=f"I cannot process this request because it contains the blocked keyword '{keyword_to_block}'.")],
            )
            # Note: You could also set an error_message field here if needed
        )
    else:
        # Keyword not found, allow the request to proceed to the LLM
        print(f"--- Callback: Keyword not found. Allowing LLM call for {agent_name}. ---")
        return None # Returning None signals ADK to continue normally

def block_paris_tool_guardrail(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """
    Checks if 'get_weather_real' is called for 'Paris'.
    If so, blocks the tool execution and returns a specific error dictionary.
    Otherwise, allows the tool call to proceed by returning None.
    """
    tool_name = tool.name
    agent_name = tool_context.agent_name # Agent attempting the tool call
    print(f"--- Callback: block_paris_tool_guardrail running for tool '{tool_name}' in agent '{agent_name}' ---")
    print(f"--- Callback: Inspecting args: {args} ---")

    # --- Guardrail Logic ---
    target_tool_name = "get_weather_real" # Match the function name used by FunctionTool
    blocked_city = "paris"

    # Check if it's the correct tool and the city argument matches the blocked city
    if tool_name == target_tool_name:
        city_argument = args.get("city", "") # Safely get the 'city' argument
        if city_argument and city_argument.lower() == blocked_city:
            print(f"--- Callback: Detected blocked city '{city_argument}'. Blocking tool execution! ---")
            # Optionally update state
            tool_context.state["guardrail_tool_block_triggered"] = True
            print(f"--- Callback: Set state 'guardrail_tool_block_triggered': True ---")

            # Return a dictionary matching the tool's expected output format for errors
            # This dictionary becomes the tool's result, skipping the actual tool run.
            return {
                "status": "error",
                "error_message": f"Policy restriction: Weather checks for '{city_argument.capitalize()}' are currently disabled by a tool guardrail."
            }
        else:
             print(f"--- Callback: City '{city_argument}' is allowed for tool '{tool_name}'. ---")
    else:
        print(f"--- Callback: Tool '{tool_name}' is not the target tool. Allowing. ---")


    # If the checks above didn't return a dictionary, allow the tool to execute
    print(f"--- Callback: Allowing tool '{tool_name}' to proceed. ---")
    return None # Returning None allows the actual tool function to run

# --- Redefine Sub-Agents (Ensures they exist in this context) ---
greeting_agent = None
try:
    # Use a defined model constant
    greeting_agent = Agent(
        model=MODEL_GEMINI_2_0_FLASH,
        name="greeting_agent", # Keep original name for consistency
        instruction="You are the Greeting Agent. Your ONLY task is to provide a friendly greeting using the 'say_hello' tool. Do nothing else.",
        description="Handles simple greetings and hellos using the 'say_hello' tool.",
        tools=[say_hello],
    )
    print(f"✅ Sub-Agent '{greeting_agent.name}' redefined.")
except Exception as e:
    print(f"❌ Could not redefine Greeting agent. Check Model/API Key ({greeting_agent.model}). Error: {e}")

farewell_agent = None
try:
    # Use a defined model constant
    farewell_agent = Agent(
        model=MODEL_GEMINI_2_0_FLASH,
        name="farewell_agent", # Keep original name
        instruction="You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message using the 'say_goodbye' tool. Do not perform any other actions.",
        description="Handles simple farewells and goodbyes using the 'say_goodbye' tool.",
        tools=[say_goodbye],
    )
    print(f"✅ Sub-Agent '{farewell_agent.name}' redefined.")
except Exception as e:
    print(f"❌ Could not redefine Farewell agent. Check Model/API Key ({farewell_agent.model}). Error: {e}")


root_agent = Agent(
        name="weather_agent_v6_tool_guardrail", # New version name
        model=MODEL_GEMINI_2_0_FLASH,
        description="Main agent: Handles weather, delegates, includes input AND tool guardrails.",
        instruction="You are the main Weather Agent. Provide weather using 'get_weather_real'. "
                    "Delegate greetings to 'greeting_agent' and farewells to 'farewell_agent'. "
                    "Handle only weather, greetings, and farewells.",
        tools=[get_weather_real],
        sub_agents=[greeting_agent, farewell_agent],
        output_key="last_weather_report",
        before_model_callback=block_keyword_guardrail, # Keep model guardrail
        before_tool_callback=block_paris_tool_guardrail # <<< Add tool guardrail
)

# Sample queries to test the agent:

# # Agent will give weather information for the specified cities.
# # What's the weather in Tokyo?
# # What is the weather like in London?
# # Tell me the weather in New York?

# # Agent will not have information for the specified city.
# # How about Paris?

# # Agent will delegate greetings to the greeting_agent.
# # Hi there!
# # Hello!
# # Hello,  this is alice

# # Agent will delegate farewells to the farewell_agent.
# # Bye!
# # See you later!
# # Thanks, bye!

# # Agent will block any request containing the keyword "BLOCK".
# # What's the weather in BLOCK tokyo?
# # tell me the weather in BLOCK london
# # how about BLOCK new york?

## # Agent will block the get_weather_real tool if called with "Paris".
# # What's the weather in Paris?
# # Tell me the weather in Paris
# # How's the weather in Paris?