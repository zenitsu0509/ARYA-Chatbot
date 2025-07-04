# ARYA - Arya Bhatt Hostel AI Agent

Welcome to **ARYA**, the official AI agent for Arya Bhatt Hostel. This advanced assistant is designed to help students and residents with comprehensive information about hostel facilities, rules, mess menus, and photos, and includes an intelligent complaint registration system.

## 🌟 Features

### Core Architecture
-   **🤖 ReAct Agent Framework**: Built on an advanced Reason and Act (ReAct) agent architecture, allowing the AI to dynamically choose the best tool to respond to user queries.
-   **🚀 High-Performance Backend**: Powered by **Groq** for ultra-low latency LLM inference, ensuring fast and responsive interactions.
-   **🧠 Intelligent Toolset**: Equipped with a suite of specialized tools for:
    -   **🍽️ Mess Menu**: Fetches the daily, weekly, or specific-day mess menu.
    -   **📸 Hostel Photos**: Retrieves photos of rooms, the mess, facilities, and the building exterior.
    -   **📝 Complaint Registration**: Guides users through a multi-step complaint submission process.
    -   **ℹ️ General Information**: Answers all other questions using a vector-based knowledge base.

### User-Facing Features
-   **Smart Complaint Detection**: Automatically identifies complaint-related messages and initiates the registration workflow.
-   **Pre-filled Forms**: Generates URLs with user details pre-filled for the official complaint portal.
-   **User-Friendly Interface**: A clean and intuitive UI built with Streamlit, featuring chat history and dynamic display of text and images.

## 🛠️ Tech Stack

-   **Frontend**: **Streamlit**
-   **LLM Inference**: **Groq**
-   **Vector Database**: **Pinecone**
-   **Embeddings**: **Sentence-Transformers**
-   **Core Framework**: **LangChain** (ReAct Agent, Tools, Chains)
-   **Language**: **Python**

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/zenitsu0509/ARYA_Chatbot.git
cd ARYA_Chatbot
```

### 2. Install Dependencies

Ensure you have Python 3.8+ installed. Install the required packages using:
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the project root and add the following keys:

```
PINECONE_API_KEY=<your-pinecone-api-key>
PINECONE_ENV=<your-pinecone-environment>
GROQ_API_KEY=<your-groq-api-key>
```

### 4. Configure the Pinecone Index

Make sure you have a **Pinecone** index created and populated with the knowledge base documents for Arya Bhatt Hostel.

### 5. Run the Application

You can start the Streamlit app with the following command:

```bash
streamlit run streamlit_app.py
```

The application will be available at `http://localhost:8501`.

## 🤔 How It Works

1.  **User Input**: The user asks a question in the Streamlit interface.
2.  **Agentic Core**: The query is sent to the **LangChain ReAct Agent**.
3.  **Tool Selection**: The agent analyzes the input and decides which tool to use:
    -   For "What's for dinner?", it calls the `get_mess_menu` tool.
    -   For "Show me the rooms", it calls the `get_hostel_photos` tool.
    -   For "What are the library hours?", it uses the `hostel_information_retriever` tool.
    -   For "My fan is broken", it initiates the complaint handling flow.
4.  **Tool Execution**: The selected tool is executed.
5.  **Response Generation**: The **Groq LLM** processes the tool's output and generates a final, user-friendly response.
6.  **Dynamic Output**: The response, whether text or a list of images, is displayed in the UI.

## Project Structure

```bash
arya-hostel-chatbot/
│
├── app.py                # Main application file
├── config.py             # Configuration loader for API keys and settings
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables file
├── README.md             # Project documentation
└── .gitignore            # Files to be ignored in version control
```

## Key Functions

-   **setup_pinecone**: Initializes the Pinecone vector store for document search.
-   **setup_llm**: Configures the Hugging Face language model used for generating responses.
-   **create_qa_chain**: Combines the vector store with the LLM to create the question-answering logic.
-   **main**: Manages the Streamlit interface and user interactions.

## Customization

You can modify the following parameters to customize ARYA:

-   **Language Model**: Change the Hugging Face model by updating the `repo_id` in the `setup_llm` function.
-   **Index Name**: Change the Pinecone index by modifying the `index_name` in `setup_pinecone`.

## Future Enhancements

-   **Admin Interface**: Allow hostel admins to update or add new knowledge base entries.
-   **Multilingual Support**: Support for other languages to assist international students.

## Contributing

If you'd like to contribute to the development of this project:

1.  Fork the repository.
2.  Create a new branch for your feature/bugfix.
3.  Submit a pull request with a detailed explanation of your changes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

* * * * *

💻 Developed and maintained by **Himanshu Gangwar**\
🔄 Last updated: july 2025
