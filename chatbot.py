import os
from typing import Dict, List
from langchain.vectorstores import VectorStore
from langchain_pinecone import PineconeVectorStore
from langchain_pinecone import PineconeEmbeddings
from pinecone import Pinecone, PineconeException
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
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
        self.qa_chain = None
        self.menu_system = MessMenu()
        self.photo_system = HostelPhotos()
        self.complaint_handler = ComplaintHandler()
        
    def setup(self):
        """Set up all components of the chatbot."""
        try:
            self.vector_store = self.setup_pinecone()
            self.llm = self.setup_llm()
            self.qa_chain = self.create_qa_chain()
        except Exception as e:
            raise Exception(f"Failed to initialize chatbot: {str(e)}")
        
    def setup_pinecone(self, index_name: str = "arya-index-o") -> VectorStore:
        """Initialize Pinecone and return vector store."""
        try:
            pc = Pinecone(api_key=self.pinecone_api_key, environment=self.pinecone_env)
            index = pc.Index(index_name)
            
            embeddings = HuggingFaceEmbeddings(
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
                model_name="llama-3.1-70b-versatile",
                temperature=0.7,
                max_tokens=512
            )
                
        except Exception as e:
            raise Exception(f"Failed to initialize language model: {str(e)}")

    def create_qa_chain(self) -> RetrievalQA:
        """Create the question-answering chain with custom prompt."""
        try:
            template = """
            You are Arya, the official bot of Arya Bhatt Hostel. Your role is to provide accurate and helpful information about the hostel.

            Context information from the knowledge base:
            {context}

            Guidelines:
            - Provide concise, accurate answers based on the given context
            - If information is not available in the context, politely say you don't know
            - Be friendly and professional in your responses
            - Keep responses brief but informative

            Question: {question}
            Answer:
            """
            
            prompt = PromptTemplate(template=template, input_variables=["context", "question"])
            
            return RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vector_store.as_retriever(search_kwargs={'k': 3}),
                return_source_documents=False,
                chain_type_kwargs={"prompt": prompt}
            )
        except Exception as e:
            raise Exception(f"Failed to create QA chain: {str(e)}")

    def handle_menu_query(self, question: str) -> str:
        """Handle questions related to the mess menu."""
        try:
            question_lower = question.lower()
            logger.debug(f"Handling menu query: {question_lower}")

            # Handle current menu query
            if re.search(r"(current menu|today menu|what's for|what is for|what are we eating|mess menu|food|"
                        r"today's food|what's being served|what is on the menu|what are we having|"
                        r"what are we eating today|what's on today's menu|what's on the menu for today|"
                        r"what are we getting in the mess|what food is in the mess|what is for lunch|"
                        r"what is for dinner|today's lunch menu|today's dinner menu)", question_lower):
                logger.debug("Fetching current menu")
                return self.menu_system.get_current_menu()

            # Handle weekly menu query
            if re.search(r"week(ly)? menu", question_lower):
                logger.debug("Fetching weekly menu")
                weekly_menu = self.menu_system.get_full_week_menu()
                if weekly_menu:
                    return self.menu_system.format_full_menu(weekly_menu)
                return "Sorry, I couldn't retrieve the weekly menu at the moment."

            # Handle specific day and time query
            days_of_week = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
            meals = ['breakfast', 'lunch', 'dinner', 'dessert', 'morning', 'night']
            
            day_found = None
            meal_found = None

            # Search for day and meal in the question
            for day in days_of_week:
                if day in question_lower:
                    day_found = day.capitalize()
                    break

            for meal in meals:
                if meal in question_lower:
                    meal_found = meal
                    break

            if day_found:
                logger.debug(f"Fetching menu for {day_found}")
                day_menu = self.menu_system.get_menu_for_day(day_found)
                if day_menu:
                    # If a specific meal is mentioned
                    if meal_found:
                        logger.debug(f"Fetching {meal_found} for {day_found}")
                        meal_map = {
                            'breakfast': 'morning_menu',
                            'morning': 'morning_menu',  
                            'lunch': 'evening_menu',
                            'dinner': 'night_menu',
                            'night': 'night_menu',  
                            'dessert': 'dessert'
                        }
                        specific_meal = day_menu.get(meal_map.get(meal_found))
                        if specific_meal and specific_meal != 'OFF':
                            return f"📅 {day_found.capitalize()}'s {meal_found.capitalize()}: {specific_meal}"
                        return f"Sorry, no {meal_found} is available for {day_found}."

                    # If no specific meal is mentioned, return the full day's menu
                    response = [
                        f"📅 Menu for {day_menu['day_of_week']}:",
                        f"🌅 Breakfast: {day_menu['morning_menu']}",
                        f"🌞 Lunch: {day_menu['evening_menu']}",
                        f"🌙 Dinner: {day_menu['night_menu']}"
                    ]
                    
                    if day_menu['dessert'] != 'OFF':
                        response.append(f"🍨 Dessert: {day_menu['dessert']}")

                    return "\n".join(response)
                
                return f"Sorry, I couldn't retrieve the menu for {day_found}."

        except Exception as e:
            logger.error(f"Error handling menu query: {str(e)}")
            return "Sorry, I couldn't retrieve the menu at the moment."

        return None


    def get_response(self, question: str, user_session: str = "default") -> str:
        try:
            # Check if user is in complaint collection flow
            if self.complaint_handler.is_in_complaint_flow(user_session):
                complaint_response = self.complaint_handler.process_complaint_step(user_session, question)
                return complaint_response
            
            # Check if the message contains a complaint
            if self.complaint_handler.detect_complaint(question):
                complaint_response = self.complaint_handler.start_complaint_collection(user_session, question)
                return complaint_response
            
            # Check if the question is related to the mess menu
            menu_response = self.handle_menu_query(question)
            if menu_response:
                return {"text": menu_response}
            
            # Check if the question is related to photos
            photo_paths = self.photo_system.handle_photo_query(question)
            if photo_paths:
                # Return as list of image paths
                return {"photos": photo_paths}
            
            # Handle regular QA response
            if not self.qa_chain:
                raise Exception("Chatbot not properly initialized. Call setup() first.")
            
            response = self.qa_chain.invoke(question)
            return {"text": response['result']}
            
        except Exception as e:
            raise Exception(f"Error getting response: {str(e)}")

    def handle_complaint_command(self, command: str, user_session: str = "default") -> Dict:
        """Handle specific complaint-related commands."""
        command_lower = command.lower().strip()
        
        if command_lower in ['cancel complaint', 'stop complaint', 'cancel']:
            response = self.complaint_handler.cancel_complaint(user_session)
            return {"text": response}
        
        return {"text": "I didn't understand that command. You can say 'cancel complaint' to stop the current complaint registration."}

 



if __name__ == "__main__":
    test_handle_menu_query()