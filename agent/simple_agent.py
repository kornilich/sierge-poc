
import os

from langchain_core.agents import AgentAction
from langchain_openai import ChatOpenAI
from langchain_core.agents import AgentAction
from langgraph.graph import StateGraph, END

import tools
import prompts

class SimpleAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            openai_api_key=os.environ["OPENAI_API_KEY"],
            temperature=0
        )
        
        self.tools = [
            tools.web_search,
            tools.final_answer
        ]
        
        self.tool_str_to_func = {
            "web_search": tools.web_search,
            "final_answer": tools.final_answer
        }

        self.oracle = (
            {
                "input": lambda x: x["input"],
                "chat_history": lambda x: x["chat_history"],
                "scratchpad": lambda x: self.create_scratchpad(
                    intermediate_steps=x["intermediate_steps"]
                ),
            }
            | prompts.prompt
            | self.llm.bind_tools(self.tools, tool_choice="any")
        )

    # define a function to transform intermediate_steps from list
    # of AgentAction to scratchpad string
    def create_scratchpad(self, intermediate_steps: list[AgentAction]):
        research_steps = []
        for i, action in enumerate(intermediate_steps):
            if action.log != "TBD":
                # this was the ToolExecution
                research_steps.append(
                    f"Tool: {action.tool}, input: {action.tool_input}\n"
                    f"Output: {action.log}"
                )
        return "\n---\n".join(research_steps)


    def run_oracle(self, state: list):
        print("run_oracle")
        print(f"intermediate_steps: {state['intermediate_steps']}")
        out = self.oracle.invoke(state)
        tool_name = out.tool_calls[0]["name"]
        tool_args = out.tool_calls[0]["args"]
        action_out = AgentAction(
            tool=tool_name,
            tool_input=tool_args,
            log="TBD"
        )
        return {
            "intermediate_steps": [action_out]
        }

    def router(self, state: list):
        # return the tool name to use
        if isinstance(state["intermediate_steps"], list):
            return state["intermediate_steps"][-1].tool
        else:
            # if we output bad format go to final answer
            print("Router invalid format")
            return "final_answer"


    def run_tool(self, state: list):
        # use this as helper function so we repeat less code
        tool_name = state["intermediate_steps"][-1].tool
        tool_args = state["intermediate_steps"][-1].tool_input
        print(f"{tool_name}.invoke(input={tool_args})")
        # run tool
        out = self.tool_str_to_func[tool_name].invoke(input=tool_args)
        action_out = AgentAction(
            tool=tool_name,
            tool_input=tool_args,
            log=str(out)
        )
        return {"intermediate_steps": [action_out]}

    def setup(self): 
        graph = StateGraph(tools.AgentState)

        graph.add_node("oracle", self.run_oracle)
        graph.add_node("web_search", self.run_tool)
        graph.add_node("final_answer", self.run_tool)

        graph.set_entry_point("oracle")

        graph.add_conditional_edges(
            source="oracle",  # where in graph to start
            path=self.router,  # function to determine which node is called
        )

        # create edges from each tool back to the oracle
        for tool_obj in self.tools:
            if tool_obj.name != "final_answer":
                graph.add_edge(tool_obj.name, "oracle")

        # if anything goes to final answer, it must then move to END
        graph.add_edge("final_answer", END)

        runnable = graph.compile()

    @staticmethod
    def build_report(output: dict):
        research_steps = output["research_steps"]
        if type(research_steps) is list:
            research_steps = "\n".join([f"- {r}" for r in research_steps])
        sources = output["sources"]
        if type(sources) is list:
            sources = "\n".join([f"- {s}" for s in sources])
        return f"""
    INTRODUCTION
    ------------
    {output["introduction"]}

    RESEARCH STEPS
    --------------
    {research_steps}

    REPORT
    ------
    {output["main_body"]}

    CONCLUSION
    ----------
    {output["conclusion"]}

    SOURCES
    -------
    {sources}
    """

# Image(runnable.get_graph().draw_png())

# out = runnable.invoke({
#     "input": "tell me some nice vegan places in Dallas",
#     "chat_history": [],
# })


# inputs = {
#     "input": "want to visit some nice vegan even in Dallas today",
#     "chat_history": [],
#     "intermediate_steps": [],
# }
# out = oracle.invoke(inputs)
