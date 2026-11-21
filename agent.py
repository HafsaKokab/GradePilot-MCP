import os
import sys
import uuid
import asyncio

# Ensure utf-8 output encoding on Windows terminal to avoid UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
from fastmcp import Client as FastMCPClient
from langchain.agents import create_agent as lc_create_agent
from langchain.mcp import MCPAdapter

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
    RemoveMessage,
)

from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from llm import llm


# ==========================================
# ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()

MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:8000/mcp")
FASTMCP_KEY = os.getenv("FASTMCP_KEY")
DB_PATH = "cgpa_memory.db"
RECONNECT_DELAY = 5


# ==========================================
# SYSTEM PROMPT
# ==========================================

SYSTEM_PROMPT = """You are a helpful academic advisor for PUCIT BS(CS) students.

Semester graded credit hours in PUCIT BS(CS):
- Semester 1: 15.5
- Semester 2: 15.5
- Semester 3: 16.5
- Semester 4: 16.5
- Semester 5: 18.5
- Semester 6: 18.5
- Semester 7: 18.5
- Semester 8: 14.5

Total degree credit hours: 134.0.

Rules:
1. Never calculate numbers in your head.
   Always call a tool for every calculation.
2. Never invent or guess missing marks, credit hours, or CGPA.
3. Identify the semester from course names when possible.
4. For marks outside 0 to 100, call marks_to_grade_points
   and return its error.
5. Math Deficiency courses (MD-001, MD-002) are non-credit
   pass/fail and excluded from GPA.
   Quran Translation is 0.5 credit hours and included.
6. If course names are given without credit hours,
   call get_semester_courses.
   Calculate GPA using only courses for which marks were provided.
7. Progressive Target Horizon Rule:
   When a student asks what GPA they need to reach a target CGPA:
   - Start from the current semester.
   - Evaluate the current semester first.
   - Add one semester at a time.
   - Call required_gpa_for_target for every horizon.
   - Mark values above 4.0 as impossible.
   - Stop at the first horizon where required GPA is 4.0 or less.
   - Show every evaluated horizon and its verdict.
   - Never invent or calculate required GPA values yourself.
8. Offer to save a report only after calculating semester GPA,
   projected CGPA, or target GPA advice.
   Never save without permission.
9. Be friendly, encouraging, and clear.
"""


# ==========================================
# CREATE AGENT
# ==========================================

def create_agent(model, tools_list, memory):
    """Create CGPA agent with persistent memory."""

    return lc_create_agent(
        model=model,
        tools=tools_list,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=memory,
    )


# ==========================================
# CLEAN INCOMPLETE TOOL CALLS
# ==========================================

def clean_incomplete_tool_calls(messages):
    """
    Remove incomplete AI tool calls from conversation history.
    Keep only tool calls that have matching ToolMessages,
    and only ToolMessages that match a valid tool call.
    Preserves all valid conversation messages.
    """

    completed_tool_call_ids = {
        message.tool_call_id
        for message in messages
        if isinstance(message, ToolMessage) and getattr(message, "tool_call_id", None)
    }

    retained_messages = []
    valid_retained_tool_call_ids = set()

    for message in messages:

        if isinstance(message, AIMessage) and message.tool_calls:

            valid_tool_calls = [
                call
                for call in message.tool_calls
                if call.get("id") in completed_tool_call_ids
            ]

            # Remove the AI message if none of its tool calls completed.
            if not valid_tool_calls:
                continue

            message = message.model_copy(
                update={
                    "tool_calls": valid_tool_calls,
                    "invalid_tool_calls": [],
                }
            )

            for call in valid_tool_calls:
                valid_retained_tool_call_ids.add(call.get("id"))

            retained_messages.append(message)

        elif isinstance(message, ToolMessage):

            # Keep ToolMessage only if its tool_call_id belongs to a retained AIMessage
            if getattr(message, "tool_call_id", None) in valid_retained_tool_call_ids:
                retained_messages.append(message)

        else:
            retained_messages.append(message)

    return retained_messages


# ==========================================
# RECOVER CONVERSATION MEMORY
# ==========================================

async def recover_conversation(agent, config):
    """Clean incomplete tool calls after an execution failure."""

    try:
        state = await agent.aget_state(config)
        messages = state.values.get("messages", []) if state else []

        if not messages:
            print("No conversation messages need cleaning.")
            return

        cleaned_messages = clean_incomplete_tool_calls(messages)

        if len(cleaned_messages) != len(messages):
            await agent.aupdate_state(
                config,
                {
                    "messages": [
                        RemoveMessage(id=REMOVE_ALL_MESSAGES),
                        *cleaned_messages,
                    ]
                },
            )
            print("Conversation memory cleaned successfully.")
        else:
            print("Conversation memory was already consistent.")

    except Exception as cleanup_error:
        print(f"Memory cleanup warning: {cleanup_error}")


# ==========================================
# LIST SAVED CONVERSATIONS
# ==========================================

async def list_threads(memory):
    """Get all saved conversation IDs."""

    thread_ids = set()

    async for checkpoint in memory.alist(None):
        thread_id = checkpoint.config.get("configurable", {}).get("thread_id")
        if thread_id:
            thread_ids.add(thread_id)

    return sorted(thread_ids)


# ==========================================
# HANDLE CHAT COMMANDS
# ==========================================

async def handle_command(user_input, memory, current_thread, agent=None):

    command = user_input.split()
    cmd_name = command[0].lower()

    if user_input.lower() in ["quit", "exit"]:
        return "exit", current_thread

    if user_input.lower() == "/new":

        current_thread = str(uuid.uuid4())
        print(f"New conversation started: {current_thread}\n")
        return "continue", current_thread

    if user_input.lower() == "/history":

        threads = await list_threads(memory)

        if not threads:
            print("No saved conversations found.\n")
        else:
            print("\nSaved conversations:")
            for index, thread in enumerate(threads, 1):
                marker = " (active)" if thread == current_thread else ""
                print(f"  {index}. {thread}{marker}")
            print()

        return "continue", current_thread

    if cmd_name == "/switch":

        if len(command) != 2:
            print("Usage: /switch THREAD_ID (or number from /history)\n")
            return "continue", current_thread

        target = command[1]
        threads = await list_threads(memory)

        thread_id = None
        if target.isdigit():
            idx = int(target) - 1
            if 0 <= idx < len(threads):
                thread_id = threads[idx]
        elif target in threads:
            thread_id = target

        if not thread_id:
            print("Conversation not found. Run /history to see available conversations.\n")
            return "continue", current_thread

        current_thread = thread_id
        print(f"Switched to conversation: {current_thread}\n")

        # Display restored conversation history if agent is available
        if agent is not None:
            try:
                state = await agent.aget_state({"configurable": {"thread_id": current_thread}})
                messages = state.values.get("messages", []) if state else []
                if messages:
                    print("--- Restored Conversation History ---")
                    for m in messages:
                        if isinstance(m, HumanMessage):
                            print(f"You: {m.content}")
                        elif isinstance(m, AIMessage) and m.content:
                            text = m.content if isinstance(m.content, str) else "".join(
                                c.get("text", "") for c in m.content if isinstance(c, dict)
                            )
                            if text:
                                print(f"Advisor: {text}")
                    print("------------------------------------\n")
            except Exception:
                pass

        return "continue", current_thread

    if cmd_name == "/forget":

        if len(command) != 2:
            print("Usage: /forget THREAD_ID (or number from /history)\n")
            return "continue", current_thread

        target = command[1]
        threads = await list_threads(memory)

        thread_id = None
        if target.isdigit():
            idx = int(target) - 1
            if 0 <= idx < len(threads):
                thread_id = threads[idx]
        elif target in threads:
            thread_id = target

        if not thread_id:
            print("Conversation not found. Run /history to see available conversations.\n")
            return "continue", current_thread

        await memory.adelete_thread(thread_id)

        if thread_id == current_thread:
            current_thread = str(uuid.uuid4())
            print(f"Current conversation deleted. Started new conversation: {current_thread}\n")
        else:
            print(f"Conversation {thread_id} deleted successfully.\n")

        return "continue", current_thread

    return "message", current_thread


# ==========================================
# STREAM AGENT RESPONSE
# ==========================================

async def stream_response(agent, user_input, config):
    """Stream the agent response progressively."""

    print("\nAdvisor: ", end="", flush=True)

    async for chunk in agent.astream(
        {
            "messages": [
                HumanMessage(content=user_input)
            ]
        },
        config=config,
        stream_mode=["updates", "messages"],
        version="v2",
    ):

        if chunk["type"] == "messages":

            message_chunk, metadata = chunk["data"]

            if metadata.get("langgraph_node") == "model":

                content = message_chunk.content

                if isinstance(content, str):
                    print(content, end="", flush=True)

                elif isinstance(content, list):
                    for item in content:
                        if (
                            isinstance(item, dict)
                            and item.get("type") == "text"
                        ):
                            print(
                                item.get("text", ""),
                                end="",
                                flush=True,
                            )

        elif chunk["type"] == "updates":
            # Updates are processed to track graph execution without duplicating messages
            pass

    print("\n")


# ==========================================
# CHAT APPLICATION
# ==========================================

async def talk():

    if not MCP_URL:
        print("Error: MCP_URL is missing from .env")
        return

    print("\nPUCIT BS(CS) Academic Advisor")
    print("Commands: /new, /history, /switch ID, /forget ID, quit\n")

    current_thread = str(uuid.uuid4())

    # Keep SQLite memory open while MCP reconnects.
    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as memory:

        # List saved conversations on startup
        saved_threads = await list_threads(memory)
        if saved_threads:
            print("Saved conversations:")
            for index, tid in enumerate(saved_threads, 1):
                print(f"  {index}. {tid}")
            print()
        else:
            print("No saved conversations found.\n")

        print(f"New conversation ID: {current_thread}")
        print("Persistent memory enabled!\n")

        # ==================================
        # MCP RECONNECTION LOOP
        # ==================================

        while True:

            try:

                # Support authentication using FASTMCP_KEY if provided
                if FASTMCP_KEY:
                    client = FastMCPClient(MCP_URL, auth=FASTMCP_KEY)
                    adapter_cm = MCPAdapter(client)
                else:
                    adapter_cm = MCPAdapter(MCP_URL)

                async with adapter_cm as adapter:

                    tools_list = await adapter.list_tools()

                    print(
                        f"\nConnected to MCP server. "
                        f"Found {len(tools_list)} tools."
                    )

                    agent = create_agent(
                        model=llm,
                        tools_list=tools_list,
                        memory=memory,
                    )

                    # ==================================
                    # MAIN CHAT LOOP
                    # ==================================

                    while True:

                        try:
                            user_input = input("\nYou: ").strip()
                        except (KeyboardInterrupt, EOFError):
                            print("\nSession ended safely.")
                            return

                        if not user_input:
                            continue

                        action, current_thread = await handle_command(
                            user_input,
                            memory,
                            current_thread,
                            agent=agent,
                        )

                        if action == "exit":
                            print("Advisor: Goodbye!")
                            return

                        if action == "continue":
                            continue

                        config = {
                            "configurable": {
                                "thread_id": current_thread
                            }
                        }

                        # ==================================
                        # STREAMING RESPONSE
                        # ==================================

                        try:
                            await stream_response(
                                agent,
                                user_input,
                                config,
                            )

                        except Exception as error:
                            print(f"\nAgent execution error: {error}")
                            print("Attempting to clean conversation memory...")
                            await recover_conversation(agent, config)
                            print(
                                "\nMCP session may have failed. "
                                "Closing connection and attempting to reconnect."
                            )
                            # Exit inner loop to re-establish adapter connection
                            break

            except (KeyboardInterrupt, EOFError):
                print("\nSession ended safely.")
                return

            except Exception as error:
                print(f"\nMCP connection error: {error}")

            print(
                f"\nRetrying MCP connection in "
                f"{RECONNECT_DELAY} seconds..."
            )

            try:
                await asyncio.sleep(RECONNECT_DELAY)
            except (KeyboardInterrupt, EOFError):
                print("\nSession ended safely.")
                return


# ==========================================
# MAIN & EXPORTS
# ==========================================

# Compatibility export for Streamlit GUI (app.py)
try:
    from tools import (
        marks_to_grade_points as _t1,
        calculate_semester_gpa as _t2,
        calculate_new_cgpa as _t3,
        required_gpa_for_target as _t4,
        get_semester_courses as _t5,
        get_remaining_credit_hours as _t6,
        save_report as _t7,
    )
    agent = lc_create_agent(
        model=llm,
        tools=[_t1, _t2, _t3, _t4, _t5, _t6, _t7],
        system_prompt=SYSTEM_PROMPT,
    )
except Exception:
    agent = None


if __name__ == "__main__":
    try:
        asyncio.run(talk())
    except (KeyboardInterrupt, EOFError):
        print("\nApplication stopped safely.")

