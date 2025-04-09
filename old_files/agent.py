import os
from typing import Annotated, Literal
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, RemoveMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools.tavily_search import TavilySearchResults

class ChatAgent:
    def __init__(self, anthropic_api_key, tavily_api_key, base_prompt):
        self.tool_node = None
        self.graph = None
        anthropic_api_key=anthropic_api_key,
        tavily_api_key=tavily_api_key,
        base_prompt=base_prompt

    
    def initialize_graph(self, model_name: str, temperature: float, summarization_threshold: int):
        class State(MessagesState):
            summary: str

        graph_builder = StateGraph(State)

        search = TavilySearchResults(name="tavily_search", max_results=2)
        tools = [search]
        tool_node = ToolNode(tools=tools)

        llm = ChatAnthropic(
            model=model_name,
            temperature=temperature,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        llm_with_tools = llm.bind_tools(tools)
        
        def chatbot(state: State):
            summary = state.get("summary", "")
            if summary:
                system_message = f"Summary of conversation earlier: {summary}"
                messages = [SystemMessage(content=system_message)] + state["messages"]
            else:
                messages = state["messages"]
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}

        def summarize_conversation(state: State):
            summary = state.get("summary", "")
            if summary:
                summary_message = (
                    f"This is summary of the conversation to date: {summary}\n\n"
                    "Extend the summary by taking into account the new messages above:"
                )
            else:
                summary_message = "Create a summary of the conversation above:"

            messages = state["messages"][:-summarization_threshold] + [HumanMessage(content=summary_message)]
            response = llm_with_tools.invoke(messages)

            delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-summarization_threshold]]
            return {"summary": response.content, "messages": delete_messages}

        def should_continue(state: State) -> Literal["summarize_conversation", "tools", END]:
            messages = state["messages"]
            
            if isinstance(state, list):
                ai_message = state[-1]
            elif messages := state.get("messages", []):
                ai_message = messages[-1]
            else:
                raise ValueError(f"No messages found in input state to tool_edge: {state}")
            
            if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
                return "tools"
        
            if len(messages) > summarization_threshold:
                return "summarize_conversation"
            
            return END

        graph_builder.add_node("chatbot", chatbot)
        graph_builder.add_node("tools", tool_node)
        graph_builder.add_node("summarize_conversation", summarize_conversation)

        graph_builder.add_conditional_edges("chatbot", tools_condition)
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.set_entry_point("chatbot")
        
        graph_builder.add_conditional_edges(
            "chatbot",
            should_continue,
            {
                "tools": "tools",
                "summarize_conversation": "summarize_conversation",
                END: END
            },
        )

        memory = MemorySaver()
        self.graph = graph_builder.compile(checkpointer=memory)
        self.tool_node = tool_node
        return self.graph, self.tool_node