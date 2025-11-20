import os
import json
from typing import Dict, List, Optional
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
    SMALLTALK_RESPONSES = [
        (("hi", "hii", "hello", "hey", "hay", "hola", "namaste"),
         "Hi there! I'm Arya, your hostel assistant. How can I help you today?"),
        (("good morning", "good afternoon", "good evening"),
         "Hello! I'm Arya. Let me know how I can assist you with hostel queries."),
        (("thank you", "thanks", "tysm"),
         "You're welcome! If you need anything else about the hostel, just let me know."),
        (("who are you", "who r u", "what are you"),
         "I'm Arya, the Arya Bhatt Hostel AI assistant. Ask me about rooms, mess menu, complaints, or general info!"),
    ]

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
        
    def _handle_smalltalk(self, text: str) -> Optional[Dict[str, str]]:
        """Return canned responses for greetings or small talk to avoid unnecessary tool calls."""
        if not text:
            return None

        normalized = text.lower().strip()
        if not normalized:
            return None

        for phrases, response in self.SMALLTALK_RESPONSES:
            for phrase in phrases:
                if normalized == phrase or normalized.startswith(f"{phrase} "):
                    return {"text": response}
        return None

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
                temperature=0.3,
                max_tokens=2048
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
            # Clean input - remove parameter names if LLM includes them
            cleaned_day = day.strip() if day else "today"
            # Handle cases like "day='today'", "'today'", or "day=today"
            cleaned_day = cleaned_day.replace("day=", "").strip("'\"").strip()
            if not cleaned_day:
                cleaned_day = "today"
            return self.menu_system.get_menu(cleaned_day)

        menu_tool = Tool(
            name="get_mess_menu",
            func=_get_mess_menu,
            description=(
                "Get the mess menu. Input should be just the day name: 'today' for current menu, "
                "'Monday'/'Tuesday'/etc for specific day, or 'week' for full week. "
                "Examples: today, Monday, week"
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

Use this EXACT format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input value (just simple text, no parameter names)
Observation: the result of the action
... (repeat Thought/Action/Input/Observation ONLY if needed)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

CRITICAL RULES:
1. Action Input must be simple: "today" NOT "day='today'".
2. Use at most 2 tool calls per user question. If you are still unsure, answer politely and ask the user to clarify.
3. Once you get a successful Observation, immediately provide Final Answer.
4. ALWAYS end with "Final Answer: <answer>".
5. Don't repeat the same action with the same input.

Examples:
- For "current menu": Action Input is "today"
- For "Monday menu": Action Input is "Monday"
- For "show rooms": Action Input is "rooms"

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

        prompt = PromptTemplate.from_template(template)

        # Custom error handler for parsing errors
        def handle_parse_error(error) -> str:
            """Handle parsing errors by returning a helpful message."""
            error_msg = str(error)
            # Extract the actual LLM output if available
            if "Could not parse LLM output:" in error_msg:
                # The output is usually after this phrase
                import re
                match = re.search(r"Could not parse LLM output: `(.+?)`", error_msg, re.DOTALL)
                if match:
                    llm_output = match.group(1).strip()
                    # Return the output as Final Answer since LLM didn't format correctly
                    return f"Final Answer: {llm_output}"
            return "Final Answer: I apologize, but I encountered an error processing your request. Please try rephrasing your question."

        agent = create_react_agent(self.llm, tools, prompt)
        # Note: this AgentExecutor version does not support early_stopping_method
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            return_intermediate_steps=True,
            max_iterations=10,
            handle_parsing_errors=handle_parse_error,
        )

    def get_response(self, question: str, user_session: str = "default") -> str:
        try:
            # Handle greetings and small talk without invoking the agent
            smalltalk_response = self._handle_smalltalk(question)
            if smalltalk_response:
                return smalltalk_response

            # Very short/unclear inputs are handled directly to avoid wasting tool calls
            if not question or len(question.strip()) < 3:
                return {"text": "Could you please clarify your question a bit more?"}

            # Complaint handling remains a priority
            if self.complaint_handler.is_in_complaint_flow(user_session):
                return self.complaint_handler.process_complaint_step(user_session, question)
            
            if self.complaint_handler.detect_complaint(question):
                return self.complaint_handler.start_complaint_collection(user_session, question)
            
            if not self.agent_executor:
                raise Exception("Chatbot agent not properly initialized. Call setup() first.")

            # Invoke the agent to get a response
            response = self.agent_executor.invoke({"input": question})
            output = response.get('output', '')
            
            # Handle case where agent hit iteration limit
            if not output or "Agent stopped" in str(output):
                # Try to extract useful info from intermediate steps
                intermediate_steps = response.get("intermediate_steps", [])
                if intermediate_steps:
                    last_action, last_observation = intermediate_steps[-1]
                    # If the last observation looks like a valid response, use it
                    if last_observation and len(str(last_observation)) > 20:
                        output = str(last_observation)
                    else:
                        output = "I apologize, but I couldn't complete that request. Please try rephrasing."
                else:
                    output = "I'm sorry, I couldn't process that request."

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