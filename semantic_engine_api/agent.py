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
        self.anthropic_api_key = anthropic_api_key
        self.tavily_api_key = tavily_api_key
        self.base_prompt = base_prompt

    
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
            api_key=self.anthropic_api_key
        )
        
        llm_with_tools = llm.bind_tools(tools)
        
        def chatbot(state: State):
            summary = state.get("summary", "")
            config = {"configurable": {"thread_id": "1"}}

            if summary:
                system_message = f"{self.base_prompt}\n\nSummary of conversation earlier: {summary}"
                messages = [SystemMessage(content=system_message)] + state["messages"]
            else:
                system_message = self.base_prompt
                messages = [SystemMessage(content=system_message)] + state["messages"]
            response = llm_with_tools.invoke(messages, config=config)
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
        
    def run_with_message(self, message, username=None):
        """Run the agent with a single message and return the response
        
        Args:
            message (str): Message content
            username (str, optional): Username of the message author
            
        Returns:
            str: Response from the agent
        """
        if not self.graph:
            raise ValueError("Graph not initialized. Call initialize_graph first.")
            
        # Create HumanMessage with username if provided
        if username:
            formatted_message = f"{username}: {message}"
        else:
            formatted_message = message
            
        human_message = HumanMessage(content=formatted_message)
        
        # Run the graph with the message
        config = {"configurable": {"thread_id": "1"}}
        result = self.graph.invoke({"messages": [human_message]}, config=config)
        
        # Extract the response from the result
        if result and "messages" in result and len(result["messages"]) > 0:
            return result["messages"][-1].content
        return "No response generated." 