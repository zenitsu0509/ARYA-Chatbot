import os
from typing import Dict, List
from langchain.vectorstores import VectorStore
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, PineconeException
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.agents import AgentExecutor, create_react_agent, tool
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
        
    def setup_pinecone(self, index_name: str = "arya-index-o") -> VectorStore:
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

        # Create a tool for the mess menu
        menu_tool = tool(
            name="get_mess_menu",
            func=self.menu_system.get_menu,
            description=""":
            A tool to get the hostel mess menu.
            :param day: The day to get the menu for. Can be a day of the week (e.g., 'Monday'), 'today', 'week', or None.
                        If None or 'today', returns the current meal's menu.
                        If 'week', returns the full weekly menu.
            :return: A string containing the requested menu information.
            """
        )

        # Create a tool for hostel photos
        photos_tool = tool(
            name="get_hostel_photos",
            func=self.photo_system.get_photos,
            description=""":
            A tool to get paths to hostel photos.
            :param category: The category of photos to get. Must be one of ['rooms', 'mess', 'facilities', 'exterior'].
            :param subcategory: The optional subcategory of photos.
                                For 'mess', can be ['dining'].
                                For 'facilities', can be ['sports'].
                                For 'exterior', can be ['building', 'entrance', 'garden'].
            :return: A list of photo paths.
            """
        )

        tools = [retriever_tool, menu_tool, photos_tool]

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are Arya, a helpful AI assistant for the Arya Bhatt Hostel.

You have access to the following tools:
- `get_mess_menu`: To get the mess menu for a specific day, the current meal, or the whole week.
- `get_hostel_photos`: To get photos of the hostel, including rooms, mess, facilities, and exterior.
- `hostel_information_retriever`: To get general information about the hostel.

Your primary goal is to assist users by answering their questions accurately.
- For photo requests, call the `get_hostel_photos` tool and return the list of photo paths.
- For menu requests, call the `get_mess_menu` tool.
- For all other questions about the hostel, use the `hostel_information_retriever` tool.
- If you don't know the answer or the tool doesn't provide the right information, just say that you don't know.
"""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        agent = create_react_agent(self.llm, tools, prompt)
        return AgentExecutor(agent=agent, tools=tools, verbose=True)

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
            
            # The agent's output might be a string or a list of photo paths
            output = response['output']

            # Check if the output from the agent is a list of photo paths
            if isinstance(output, list) and all(isinstance(item, str) and ('.jpg' in item or '.png' in item) for item in output):
                return {"photos": output}
            
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