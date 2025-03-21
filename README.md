# Persistent Memory Agent UI

A demonstration project that combines LangGraph with memory features, assistant-stream, and FastAPI to create an AI agent with persistent memory and a modern UI. The project uses [assistant-ui](https://www.assistant-ui.com/) and Next.js for the frontend interface.

## Overview

This project showcases:

- A LangGraph agent with persistent memory using MemorySaver
- Thread-based conversation tracking that persists between sessions
- Real-time response streaming to the frontend using assistant-stream
- A modern chat UI built with assistant-ui and Next.js
- Integration of mathematical tools (add, multiply, divide) with contextual memory

## Prerequisites

- Python 3.11 or later
- Node.js v20.18.0
- npm v10.9.2
- Yarn v1.22.22

## Project Structure

```
persistent-memory-agent/
├── backend/         # FastAPI + assistant-stream + LangGraph server with memory
└── frontend/        # Next.js + assistant-ui client
```

## How It Works

The agent uses LangGraph's memory features to maintain context between conversations:

1. Each conversation is assigned a unique `thread_id`
2. The agent's state is checkpointed after each interaction using MemorySaver
3. Previous context is loaded when returning to a conversation
4. The agent can reference previous calculations and conversations

This implementation is based on the approach from LangChain Academy's agent-memory module, where memory allows the agent to understand references to previous results (like "multiply that by 2").

## Setup Instructions

### Set up environment variables

Go to `./backend` and create `.env` file with the following variables:

```
GOOGLE_API_KEY=your_google_api_key  # For Gemini model
OPENAI_API_KEY=your_openai_api_key  # Alternative model option
LANGCHAIN_API_KEY=your_langsmith_api_key  # Optional for tracing
LANGCHAIN_TRACING_V2=true  # Optional for tracing
LANGCHAIN_PROJECT=memory-agent  # Optional for tracing
```

### Backend Setup

The backend is built using FastAPI and LangGraph's memory features.

```bash
cd backend
poetry install
poetry run python -m app.server
```

### Frontend Setup

The frontend is built with assistant-ui and Next.js.

```bash
cd frontend
yarn install
yarn dev
```

## Usage Examples

- Ask the agent to perform math: "Add 3 and 4"
- Then refer to previous results: "Multiply that by 2"
- The agent will maintain context across the conversation
- Start a new conversation with a different thread_id to begin fresh

## Credits

Based on the LangChain Academy Module 1 agent-memory examples and inspired by the langgraph-memory implementation.