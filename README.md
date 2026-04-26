# CodeNakshatra-the-nexus-knights
DEKU - Your AI FriendThis is a simple AI agent powered by Mistral AI. It can chat with you and use basic tools like web search and checking your system stats.Files•agent.py: The main brain of the AI. Clean and simple.•app.py: The visual interface (GUI) using CustomTkinter.•.env.example: A template for your API keys.•requirements.txt: The list of libraries needed to run the app.How to setup1.Install the requirements:pip install -r requirements.txt2.Create a .env file from the example and add your Mistral API key.3.Run the app:python app.py
 1. We import all libraries (some are optional — app still works without them)
  2. We load API keys from .env file using python-dotenv
  3. We connect to Mistral AI for the chat brain
  4. We define 75 tools the AI can use
  5. We run the chat loop
