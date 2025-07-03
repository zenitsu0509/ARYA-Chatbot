# config.py

import os
import streamlit as st
from dotenv import load_dotenv

def load_config():
    """
    Load configuration from environment variables or Streamlit secrets.
    Returns dict with configuration values.
    """
    # First try loading from .env file
    load_dotenv()

    # Dictionary to store our configuration
    config = {}

    # List of required environment variables
    required_vars = [
        'PINECONE_API_KEY',
        'PINECONE_ENV',
        'GROQ_API_KEY'
    ]

    # Try getting variables from different sources
    for var in required_vars:
        # First check Streamlit secrets (for deployment)
        if hasattr(st.secrets, var):
            config[var] = st.secrets[var]
        # Then check environment variables
        elif os.getenv(var):
            config[var] = os.getenv(var)
        else:
            config[var] = None

    # Validate configuration
    missing_vars = [var for var, value in config.items() if value is None]
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            "Please set them in .env file for local development or in Streamlit secrets for deployment."
        )

    return config