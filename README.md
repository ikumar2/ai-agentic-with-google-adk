🛠️ Step-by-Step Setup and Create An Agent and multiple agent using ADK with Python



Install 
Python 3.9 or later
pip for installing packages

Install ADK by running the following command:


pip install google-adk

Create a Python virtual environment:


python -m venv .venv
Activate the Python virtual environment:

On MAC/Linux:

source .venv/bin/activate

on Window:

.venv\Scripts\activate.bat
Create an agent project¶
Run the adk create command to start a new agent project.


adk create ai_agent_with_adk
Option will shown as :

Choose a model for the root agent:
1. gemini-2.5-flash
2. Other models (fill later)
Choose model (1, 2): 
Press 1
1. Google AI
2. Vertex AI

Choose a backend (1, 2):

Press 1


Don't have API Key? Create one in AI Studio: https://aistudio.google.com/apikey

Go to API Studio and create apiKey

Enter Google API key: ****************

Your project would be created with structure like

Agent created in /Users/ai_agent_with_adk/ai_agent_with_adk:
- .env
- __init__.py
- agent.py

Run with command-line interface¶
Run your agent using the adk run command-line tool.

**adk run ai_agent_with_adk**

Run with web interface
The ADK framework provides web interface you can use to test and interact with your agent. You can start the web interface using the following command:

**adk web --port 8000**

Launch the url on browser "http://127.0.0.1:8000"





