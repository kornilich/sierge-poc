from dotenv import load_dotenv
import streamlit as st
from agents.simpleagent import SimpleAgent
from agents.testagent import TestAgent
from PIL import Image
from langchain_core.messages import HumanMessage

# Initialize the agent

def streamlit_config():
    st.set_page_config(page_title='Sierge PoC', layout='wide')
    
    with st.sidebar:
        with st.form("preferences"):
            contextual_preferences = st.text_area(
                ":orange[**Contextual Preferences**]",
                value="""I'm going with my family. 
Looking for a place with:
Atmosphere: Casual, child-friendly, well-lit
Alcohol: Limited or non-alcoholic options
Meals: Family-style sharing platters
Noise level: Moderate, tolerant of children's sounds"""
                , height=72*3)
            fixed_preferences = st.text_area(
                ":orange[**Fixed Preferences**]",
                value="""I'm from Dallas city, 21 years old, single woman.
I love dancing, and prefer vegan food.
Love meeting people but not noisy places.
I'm a new resident in Dallas."""
                , height=72*3)
            submitted = st.form_submit_button(
                "Submit", type="primary", use_container_width=True)

        with st.expander("Agent settings"):
            model = st.selectbox('Model', ('gpt-4o-mini'))
            web_search = st.selectbox('Web search', ('serpapi'))
            
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image("https://media.lordicon.com/icons/wired/flat/2007-dallas-city.svg",
                 use_container_width=True)
    with col2:
        st.subheader(":blue[Sierge PoC]")
        st.write("Tailor recommendations in real time based on logistics, constraints, and external conditions like time availability, budget, location, and weather. They ensure that experiences are practical, feasible, and aligned with current circumstances without altering core user preferences.")
        
    return contextual_preferences, fixed_preferences



contextual_preferences, fixed_preferences = streamlit_config()

load_dotenv()

agent = TestAgent()
agent.setup()


# I want to stat in the morning, take a look at some sight-seen and then get to restaurant 
chat_input = st.chat_input("Describe your situational preferences here...")

if chat_input:
    query = f"{fixed_preferences} and {contextual_preferences}. I have following situation {chat_input}"
    
    messages = [HumanMessage(content=query)]
    result = agent.runnable.invoke({"messages": messages})

    # st.write(SimpleAgent.build_report(
    #     output=result["intermediate_steps"][-1].tool_input
    # ))

    st.write(result["messages"][-1].content)

    with st.chat_message("assistant"):
        st.write(chat_input)
        
else:
    img = agent.runnable.get_graph().draw_png()
    st.image(img, width=400, caption="Agentic AI based venue recommendation")


