# PUCIT BS(CS) Academic Advisor & CGPA Guider (Assignment 3)

An intelligent, production-ready academic advising assistant built for PUCIT BS(CS) students. The project features an asynchronous **FastMCP** server providing degree calculation tools, a conversational **LangChain / LangGraph** agent powered by Groq LLMs, SQLite persistent memory surviving application restarts, token-by-token streaming, and resilient automatic reconnection with memory cleanup.

---

## 1. Project Overview

The PUCIT CGPA Guider assists students with:
- Converting numeric marks to PUCIT grade points according to official grade bands.
- Calculating semester credit-weighted GPAs.
- Projecting cumulative GPAs (CGPAs) based on completed and current credits.
- Computing target semester GPAs across progressive semester horizons.
- Looking up official semester course outlines and remaining credit hours.
- Generating and saving calculation summary reports upon student request.

---

## 2. Technologies

- **Python 3.12+**
- **FastMCP 4.2.3**: High-performance Model Context Protocol (MCP) server & client.
- **LangChain / LangGraph**: Agent execution, tool binding via `MCPAdapter`, and checkpointing.
- **AsyncSqliteSaver & SQLite**: Asynchronous persistent thread storage across application restarts.
- **Groq LLM**: `openai/gpt-oss-20b` (or other Groq-hosted chat models).
- **python-dotenv**: Environment configuration management.

---

## 3. Installation & Setup

1. **Clone the repository** (or navigate to the project directory):
   ```bash
   cd AI_BCSF24M051
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r server/requirements.txt
   ```

---

## 4. Environment Variables

Create a `.env` file in the project root directory (refer to `.env.example`):

```env
GROQ_API_KEY=your_groq_api_key_here
MCP_URL=http://127.0.0.1:8000/mcp
FASTMCP_KEY=your_optional_secret_token_here
```

| Variable | Description | Default |
|---|---|---|
| `GROQ_API_KEY` | Your Groq Cloud API key | *Required* |
| `MCP_URL` | FastMCP server endpoint URL | `http://127.0.0.1:8000/mcp` |
| `FASTMCP_KEY` | Optional bearer authentication token for production/hosted FastMCP | *Optional* |
| `PORT` | MCP server listen port (for server startup) | `8000` |

> **Note:** Never commit or expose your actual `.env` file or API keys.

---

## 5. MCP Server Startup

Start the FastMCP server from the project root:

```bash
python server/server.py
```

The server binds to `http://0.0.0.0:8000/mcp` and exposes all 7 academic calculation tools.

---

## 6. Agent Startup

In a separate terminal (with `.venv` activated):

```bash
python agent.py
```

### Supported Interactive Commands:
- `/new`: Starts a new conversation thread with a fresh unique ID.
- `/history`: Displays all saved conversation threads stored in SQLite.
- `/switch <THREAD_ID or NUMBER>`: Restores and switches to the specified conversation.
- `/forget <THREAD_ID or NUMBER>`: Permanently deletes the selected conversation from memory.
- `quit` or `exit`: Safely terminates the session.

---

## 7. The Seven MCP Tools & Their Purposes

All seven academic tools run on the FastMCP server without requiring direct LLM or Groq dependencies:

1. **`marks_to_grade_points(marks: int) -> float`**  
   Converts course marks (0–100) to PUCIT grade points according to official grade bands (85+ = 4.0, 80–84 = 3.7, 75–79 = 3.3, 70–74 = 3.0, 65–69 = 2.7, 61–64 = 2.3, 58–60 = 2.0, 55–57 = 1.7, 50–54 = 1.0, <50 = 0.0). Validates input range.

2. **`calculate_semester_gpa(grade_points: list[float], credit_hours: list[float]) -> float`**  
   Calculates one semester's credit-weighted GPA using the formula $\sum(\text{grade\_point} \times \text{credit\_hours}) / \sum(\text{credit\_hours})$.

3. **`calculate_new_cgpa(current_cgpa: float, completed_credit_hours: float, semester_gpa: float, semester_credit_hours: float) -> float`**  
   Projects new cumulative CGPA after completing a semester with given credit hours.

4. **`required_gpa_for_target(target_cgpa: float, current_cgpa: float, completed_credit_hours: float, remaining_credit_hours: float) -> float`**  
   Calculates required GPA across remaining credit hours to hit a target CGPA. Used progressively horizon by horizon.

5. **`get_semester_courses(semester: int) -> str`**  
   Retrieves official course codes, course names, and credit hours for semesters 1 through 8.

6. **`get_remaining_credit_hours(current_semester: int) -> float`**  
   Calculates the total graded credit hours remaining in the degree from `current_semester + 1` to 8 (134.0 total degree credits).

7. **`save_report(filename: str, content: str) -> str`**  
   Saves calculation summaries and advising advice to a text file only upon explicit student confirmation.

---

## 8. Persistent Memory

Persistent conversational memory is implemented with **`AsyncSqliteSaver`** backed by `cgpa_memory.db`:
- **Thread Isolation**: Every conversation thread has a unique UUID.
- **Startup Listing**: All previously saved conversation threads are listed when `agent.py` starts.
- **Crash / Restart Survival**: Closing the agent application and restarting restores previous conversations with full message history and context intact.
- **Thread Management**: Direct switching (`/switch`) and deletion (`/forget`) with input validation.

---

## 9. Streaming

Token streaming is implemented using `agent.astream()` with the required configuration:
- `stream_mode=["updates", "messages"]`
- `version="v2"`
- Tokens are printed progressively in real-time using `flush=True`.
- The system handles both message chunks and graph update events cleanly, eliminating duplicate output.

---

## 10. Error Handling & Recovery

- **Server Disconnection & Auto-Reconnection**: If the FastMCP server disconnects or crashes, the agent gracefully logs the disconnection and enters an automated reconnection loop with configurable retry delay (`RECONNECT_DELAY=5s`).
- **Orphaned / Incomplete Tool Call Cleanup**: If an MCP tool call fails or is interrupted, `recover_conversation()` identifies `AIMessage`s lacking matching `ToolMessage`s and safely removes only the incomplete calls from SQLite state using `RemoveMessage(id=REMOVE_ALL_MESSAGES)`. Valid conversation messages remain intact, completely preventing Groq 400 Bad Request errors.
- **Graceful Shutdown**: `KeyboardInterrupt` (Ctrl+C) and `EOFError` (Ctrl+Z/D) are caught at all layers for a clean, non-crashing terminal exit.

---

## 11. Testing Commands

### Independent FastMCP Tools Test (No LLM required)
Ensure UTF-8 encoding in PowerShell:
```powershell
$env:PYTHONIOENCODING="utf-8"
fastmcp list http://127.0.0.1:8000/mcp
```

Call individual tools directly:
```powershell
fastmcp call http://127.0.0.1:8000/mcp marks_to_grade_points marks=85
fastmcp call http://127.0.0.1:8000/mcp calculate_semester_gpa --input-json '{\"grade_points\": [4.0, 3.7], \"credit_hours\": [3.0, 3.0]}'
fastmcp call http://127.0.0.1:8000/mcp get_semester_courses semester=5
```

### Full Automated Test Suite
All test scripts verify syntax, FastMCP tools, agent tool execution, persistent memory across restarts, streaming, and the exact 10-step Task 6 failure recovery scenario:
```bash
python .gemini/antigravity/brain/cb8c4c70-a073-43ea-91b7-d2a4b88fe924/scratch/test_tools_and_server.py
python .gemini/antigravity/brain/cb8c4c70-a073-43ea-91b7-d2a4b88fe924/scratch/test_agent_memory_streaming.py
python .gemini/antigravity/brain/cb8c4c70-a073-43ea-91b7-d2a4b88fe924/scratch/test_task6_scenario.py
```

---

## 12. Deployment Instructions

### Deploying the FastMCP Server
The FastMCP server is container-ready and can be hosted on platforms such as Render, Railway, Fly.io, or Prefect Horizon:

1. **Root Directory**: `server/`
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `python server.py`
4. **Environment Variables**:
   - `PORT`: Set by hosting provider (default: `8000`).
   - `FASTMCP_KEY`: (Optional) Set a secret authentication token if required.

### Updating Client Configuration
Once deployed, set the public server URL in your `.env`:
```env
MCP_URL=https://your-public-mcp-server-domain.com/mcp
FASTMCP_KEY=your_secret_token_if_configured
```

---

## 13. Submission & Links

- **Public MCP Server URL**: https://compatible-olive-pheasant.fastmcp.app/mcp
- **GitHub Repository**: [GradePilot-MCP](https://github.com/HafsaKokab/GradePilot-MCP)
- **Roll Number**: `BCSF24M051`
