from dotenv import load_dotenv
import streamlit as st
from agents.simpleagent import SimpleAgent
from PIL import Image


st.title("🎈 Sierge PoC chatbot")
st.info('Setting up the agent...', icon="ℹ️")

# Initialize the agent
load_dotenv()

agent = SimpleAgent()
agent.setup()

st.info('Agent setup complete!', icon="ℹ️")
img = agent.runnable.get_graph().draw_png()
st.image(img)
st.divider()

# Example query
query = "tell me some nice vegan places in Dallas"

st.info(f"Running the agent with the query:\n{query}", icon="ℹ️")

result = agent.runnable.invoke({
    "input": query,
    "chat_history": [],
})

st.write(SimpleAgent.build_report(
    output=result["intermediate_steps"][-1].tool_input
))
