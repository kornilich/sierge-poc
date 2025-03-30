import streamlit as st

from typing import TypedDict, Annotated, List, Union
import operator

import os
from serpapi import GoogleSearch

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import ToolCall, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

serpapi_params = {
    "engine": "google",
    "api_key": os.getenv("SERPAPI_KEY")
}

st.title("🎈 Version 2.x")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)


class AgentState(TypedDict):
    input: str
    chat_history: list[BaseMessage]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]

search = GoogleSearch({
    **serpapi_params,
    "q": "Dallas",
    "num": 3
})

# results = search.get_dict()["organic_results"]

# contexts = "\n---\n".join(
#     ["\n".join([x["title"], x["snippet"], x["link"]]) for x in results]
# )
 

st.write("Hello, world!")
