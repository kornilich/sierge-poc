from dotenv import load_dotenv
import streamlit as st
from agent import SimpleAgent

load_dotenv()

# Initialize the agent
agent = SimpleAgent()
agent.setup()

st.title("🎈 Version 2.x")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)

# Example query
query = "tell me some nice vegan places in Dallas"
result = agent.runnable.invoke({
    "input": query,
    "chat_history": [],
})

st.write(SimpleAgent.build_report(
    output=result["intermediate_steps"][-1].tool_input
))
