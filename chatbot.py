import os
import json
from typing import Dict, List
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, PineconeException
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_groq import ChatGroq

# Import agent utilities with fallbacks to support multiple LangChain versions.
try:
    from langchain.agents import AgentExecutor
except ImportError:  # pragma: no cover
    from langchain.agents.agent import AgentExecutor  # type: ignore

try:
    from langchain.agents import create_react_agent
except ImportError:  # pragma: no cover
    from langchain.agents.react.agent import create_react_agent  # type: ignore

try:
    from langchain.tools import Tool
except ImportError:  # pragma: no cover
    from langchain.agents import Tool  # type: ignore
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools.retriever import create_retriever_tool
import re
from menu import MessMenu
from hostel_photos import HostelPhotos
from complaint_handler import ComplaintHandler
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AryaChatbot:
    def __init__(self, pinecone_api_key: str, pinecone_env: str, groq_api_key: str):
        """Initialize the chatbot with necessary credentials."""
        self.pinecone_api_key = pinecone_api_key
        self.pinecone_env = pinecone_env
        self.groq_api_key = groq_api_key
        self.vector_store = None
        self.llm = None
        self.agent_executor = None  # Changed from qa_chain
        self.menu_system = MessMenu()
        self.photo_system = HostelPhotos()
        self.complaint_handler = ComplaintHandler()
        
    def setup(self):
        """Set up all components of the chatbot."""
        try:
            self.vector_store = self.setup_pinecone()
            self.llm = self.setup_llm()
            self.agent_executor = self.create_agent()  # Changed from create_qa_chain
        except Exception as e:
            raise Exception(f"Failed to initialize chatbot: {str(e)}")
        
    def setup_pinecone(self, index_name: str = "arya-index-o") -> PineconeVectorStore:
        """Initialize Pinecone and return vector store."""
        try:
            pc = Pinecone(api_key=self.pinecone_api_key, environment=self.pinecone_env)
            index = pc.Index(index_name)
            
            embeddings = SentenceTransformerEmbeddings(
                model_name="intfloat/multilingual-e5-large",
                encode_kwargs={'normalize_embeddings': True}
            )
            
            return PineconeVectorStore(
                index=index,
                embedding=embeddings,
                namespace="ns1"
            )
        except PineconeException as e:
            raise Exception(f"Failed to initialize Pinecone: {str(e)}")

    def setup_llm(self) -> ChatGroq:
        """Initialize the language model."""
        try:
            return ChatGroq(
                groq_api_key=self.groq_api_key,
                model_name="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=512
            )
                
        except Exception as e:
            raise Exception(f"Failed to initialize language model: {str(e)}")

    def create_agent(self) -> AgentExecutor:
        """Create an agent that can use tools to answer questions."""
        
        retriever = self.vector_store.as_retriever(search_kwargs={'k': 3})

        # Create a tool for general knowledge retrieval
        retriever_tool = create_retriever_tool(
            retriever,
            "hostel_information_retriever",
            "Searches and returns information about Arya Bhatt Hostel. Use it for questions about hostel rules, facilities, contact information, etc."
        )

        def _get_mess_menu(day: str = "today") -> str:
            """Return formatted mess menu details for the requested day."""
            cleaned_day = day.strip() if day else None
            return self.menu_system.get_menu(cleaned_day)

        menu_tool = Tool(
            name="get_mess_menu",
            func=_get_mess_menu,
            description=(
                "Use this to retrieve the hostel mess menu. "
                "Pass a day of the week (e.g., 'Monday'), 'today', or 'week' to get the appropriate menu."
            )
        )

        def _get_hostel_photos(request: str) -> str:
            """Return JSON with photo paths related to the user's request."""
            query = request or ""
            photos = self.photo_system.handle_photo_query(query)
            if not photos:
                photos = []
            return json.dumps({"photos": photos})

        photos_tool = Tool(
            name="get_hostel_photos",
            func=_get_hostel_photos,
            description=(
                "Use this to fetch hostel photo paths. Provide the user's request (e.g., 'show rooms photos'). "
                "The tool returns JSON containing the photo paths."
            )
        )

        tools = [retriever_tool, menu_tool, photos_tool]

        # Use PromptTemplate for ReAct agent (required by create_react_agent)
        from langchain_core.prompts import PromptTemplate
        
        template = """You are Arya, a helpful AI assistant for the Arya Bhatt Hostel.

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Guidelines:
- For photo requests, call the `get_hostel_photos` tool and include the returned photo paths in the final answer.
- For menu-related queries, call `get_mess_menu`.
- For all other hostel information, rely on `hostel_information_retriever`.
- If the information is unavailable, politely say you don't know.
- Always provide clean, user-friendly responses without internal reasoning tags.

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

        prompt = PromptTemplate.from_template(template)

        agent = create_react_agent(self.llm, tools, prompt)
        return AgentExecutor(agent=agent, tools=tools, verbose=True, return_intermediate_steps=True)

    def get_response(self, question: str, user_session: str = "default") -> str:
        try:
            # Complaint handling remains a priority
            if self.complaint_handler.is_in_complaint_flow(user_session):
                return self.complaint_handler.process_complaint_step(user_session, question)
            
            if self.complaint_handler.detect_complaint(question):
                return self.complaint_handler.start_complaint_collection(user_session, question)
            
            if not self.agent_executor:
                raise Exception("Chatbot agent not properly initialized. Call setup() first.")

            # Invoke the agent to get a response
            response = self.agent_executor.invoke({"input": question})
            output = response['output']

            # Look for any photo tool usage to surface actual image paths
            intermediate_steps = response.get("intermediate_steps", [])
            for action, observation in reversed(intermediate_steps):
                try:
                    if getattr(action, "tool", "") == "get_hostel_photos":
                        payload = json.loads(observation)
                        photos = payload.get("photos") if isinstance(payload, dict) else None
                        if photos:
                            return {"photos": photos, "text": str(output)}
                except json.JSONDecodeError:
                    continue
            
            return {"text": str(output)}

        except Exception as e:
            logger.error(f"Error in get_response: {e}")
            # Providing a more user-friendly error message
            return {"text": "Sorry, I encountered an error while processing your request. Please try again."}

    def handle_complaint_command(self, command: str, user_session: str = "default") -> Dict:
        """Handle specific complaint-related commands."""
        command_lower = command.lower().strip()
        
        if command_lower in ['cancel complaint', 'stop complaint', 'cancel']:
            response = self.complaint_handler.cancel_complaint(user_session)
            return {"text": response}
        
        return {"text": "I didn't understand that command. You can say 'cancel complaint' to stop the current complaint registration."}

if __name__ == "__main__":
    # You might want to update this for testing the agent
    pass