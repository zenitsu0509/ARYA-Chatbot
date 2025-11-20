import streamlit as st
import warnings
from config import load_config
from chatbot import AryaChatbot
import gc
import functools
from PIL import Image
import os

# Cache decorators remain the same
@st.cache_data
def cached_load_config():
    """Cache configuration loading to reduce disk reads."""
    return load_config()

@st.cache_resource
def initialize_chatbot(config):
    """Initialize and cache the chatbot instance."""
    try:
        chatbot = AryaChatbot(
            pinecone_api_key=config['PINECONE_API_KEY'],
            pinecone_env=config['PINECONE_ENV'],
            groq_api_key=config['GROQ_API_KEY']
        )
        chatbot.setup()
        return chatbot
    except Exception as e:
        st.error(f"Failed to initialize chatbot: {str(e)}")
        # Log the full error for debugging
        import traceback
        st.error(f"Full error details: {traceback.format_exc()}")
        return None

@st.cache_data(max_entries=100, ttl=3600)
def get_cached_response(question: str, user_session_id: str) -> str:
    """Cache chatbot responses to reduce API calls and computation."""
    chatbot = st.session_state.chatbot
    if chatbot is None:
        raise ValueError("Chatbot not initialized")
    
    try:
        return chatbot.get_response(question, user_session_id)
    except Exception as e:
        # Clear cache on LLM errors to force reinitialization
        if "max_length" in str(e) or "InferenceClient" in str(e):
            st.cache_resource.clear()
            st.session_state.chatbot = None
        raise e

def init_session_state():
    """Initialize all session state variables."""
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""
    if "user_session_id" not in st.session_state:
        import uuid
        st.session_state.user_session_id = str(uuid.uuid4())

def clear_chat_history():
    """Clear chat history and session state."""
    st.session_state.chat_history = []
    get_cached_response.clear()
    gc.collect()

def manage_chat_history(history, max_length=50):
    """Manage chat history length to prevent memory bloat."""
    if len(history) > max_length:
        history = history[-max_length:]
    return history

def display_images(photo_paths):
    """Display images in a grid layout."""
    try:
        cols = st.columns(min(3, len(photo_paths)))
        for idx, path in enumerate(photo_paths):
            if os.path.exists(path):
                try:
                    with Image.open(path) as img:
                        cols[idx % 3].image(img, caption=f"Image {idx + 1}", use_container_width=True)
                except Exception as e:
                    cols[idx % 3].error(f"Error loading image: {str(e)}")
            else:
                cols[idx % 3].error(f"Image not found: {path}")
    except Exception as e:
        st.error(f"Error displaying images: {str(e)}")

def handle_input():
    """Handle the submission of user input."""
    if st.session_state.user_input.strip():
        user_question = st.session_state.user_input
        try:
            with st.spinner('Processing your question...'):
                response = get_cached_response(user_question, st.session_state.user_session_id)
                result = {'question': user_question}
                
                # Handle different response types
                if isinstance(response, dict):
                    if "photos" in response:
                        result['response'] = "Here are the photos you requested:"
                        result['photos'] = response["photos"]
                    elif "complaint_url" in response:
                        # Handle complaint responses
                        result['response'] = response["message"]
                        result['complaint_url'] = response["complaint_url"]
                        result['is_complaint'] = True
                        if 'user_details' in response:
                            result['user_details'] = response['user_details']
                        if 'complaint_info' in response:
                            result['complaint_info'] = response['complaint_info']
                    elif "text" in response:
                        result['response'] = response["text"]
                    elif "message" in response:
                        result['response'] = response["message"]
                    else:
                        result['response'] = str(response)
                else:
                    result['response'] = response if isinstance(response, str) else str(response)
                
                st.session_state.chat_history.append(result)
                st.session_state.chat_history = manage_chat_history(st.session_state.chat_history)
                
        except Exception as e:
            st.error(f"Error processing your question: {str(e)}")
    
    st.session_state.user_input = ""

def main():
    try:
        # Initialize session state first
        init_session_state()
        
        # Suppress warnings
        warnings.filterwarnings("ignore", message=".*torch.classes.*")
        
        # Setup page configuration
        st.set_page_config(
            page_title="ARYA - Arya Bhatt Chat Bot",
            page_icon="🏢",
            layout="centered"
        )
        
        # Load cached config
        config = cached_load_config()
        
        # Initialize chatbot if not already done
        if st.session_state.chatbot is None:
            st.session_state.chatbot = initialize_chatbot(config)
        
        st.title("🏢 ARYA - Hostel AI Chatbot")
        st.markdown("""
        Welcome to the Arya Bhatt Hostel chatbot! I'm here to help you🤗
        """)
        
        # Add a sample queries section
        with st.expander("💡 Sample Questions You Can Ask"):
            st.markdown("""
            - "What's today's menu?"
            - "Show me photos of the rooms"
            - "My room fan is not working" (for complaints)
            - "What are the hostel rules?"
            - "Wi-Fi is not working in my room"
            - "Show me the mess photos"
            """)
        
        # Add clear chat button
        if st.button("Clear Chat History"):
            clear_chat_history()
        
        # Display chat history ABOVE the input box
        if st.session_state.chat_history:
            st.write("### Recent Conversations")
            for chat in reversed(st.session_state.chat_history[-5:]):
                with st.container():
                    st.write(f"**You:** {chat['question']}")
                    st.write(f"**ARYA:** {chat['response']}")
                    
                    # Handle different response types
                    if 'photos' in chat:
                        display_images(chat['photos'])
                    
                    if 'is_complaint' in chat and chat['is_complaint']:
                        if 'complaint_url' in chat:
                            st.markdown(f"🔗 [**Click here to open the complaint portal**]({chat['complaint_url']})")
                            
                            # Create an expander with form details for easy copy-paste
                            with st.expander("📋 Your Details for Manual Entry (Click to expand)"):
                                if 'user_details' in chat:
                                    details = chat['user_details']
                                    st.markdown("**Copy these details to fill the form manually:**")
                                    st.code(f"""Email Address: {details['email']}
Full Name: {details['name']}
Phone Number: {details['phone']}""")
                                
                                if 'complaint_info' in chat:
                                    info = chat['complaint_info']
                                    st.markdown("**Problem Details:**")
                                    st.code(f"""Problem Summary: Room {info['room']} - {info['description']}
Location: Room {info['room']}
Category: {info['category']}""")
                            
                            st.info("💡 If the form fields are not pre-filled automatically, please copy the details from the expandable section above and paste them manually into the complaint form.")
                    
                    st.markdown("---")
        
        # Create input form AT THE BOTTOM
        with st.form(key='chat_form', clear_on_submit=True):
            user_input = st.text_input(
                "Your Question:",
                key="user_input",
                placeholder="Type your message here..."
            )
            submit_button = st.form_submit_button("Send", on_click=handle_input)
        
        # Footer
        st.markdown("""
        ---
        💻 Developed and maintained by **Himanshu**  
        🔄 Last updated: November 2025
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        st.info("Please contact the administrator for assistance.")
        
    finally:
        gc.collect()

if __name__ == "__main__":
    main()
