from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from agno.agent import Agent
# from agno.memory.v2.db.sqlite import SqliteMemoryDb
# from agno.memory.v2.memory import Memory
from agno.models.google import Gemini
from agno.tools import tool

from tool import get_total_workers

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Initialize Agno Memory
# memory = Memory(
#     model=Gemini(id="gemini-1.5-flash"), # Use the specified model for memory management
#     db=SqliteMemoryDb(table_name="user_memories", db_file="tmp/agent.db"),
#     delete_memories=True,
#     clear_memories=True,
# )

# Initialize Agno agent
agent = Agent(
    instructions=[
        """
        You are a worker estimation chatbot. Your goal is to determine the total number of workers required for a project based on the number of floors, gardens, and toilets.

        You must obtain three specific numerical values from the user: 'num_of_floors', 'num_of_gardens', and 'num_of_toilets'.
        These values can be provided by the user in a single message or across multiple messages (chained input).

        You must use your internal memory to remember the values provided by the user across turns.

        If any of these numbers are missing from the current input AND are not already stored in your memory, you must politely ask the user for the specific missing information. For example, if 'num_of_floors' is missing, you should ask "What is the number of floors?".

        Once all three numbers are successfully obtained (either from the current input or retrieved from your memory), you must call the 'SurveyorTool' with these three values.

        After calling the 'SurveyorTool', you should generate a natural language response, clearly stating the total number of workers required based on the tool's output.
        """
    ],
    tools=[get_total_workers],
    model=Gemini(id="gemini-1.5-flash"), # Use the specified model for the agent
    user_id="worker_estimation_bot", # A unique user ID for the agent
    # memory=memory,
    enable_agentic_memory=True,
    markdown=True,
)

class ChatInput(BaseModel):
    session_id: str
    message: str

@app.post("/chat")
async def chat_endpoint(chat_input: ChatInput):
    session_id = chat_input.session_id
    user_message = chat_input.message
    
    # The Agno agent will handle parsing, remembering, asking for missing info,
    # and calling the tool based on its instructions and memory.
    response = agent.run(
        message=user_message,
        session_id=session_id
    )
    response_text = response.get_content_as_string()

    return {"response": response_text}
