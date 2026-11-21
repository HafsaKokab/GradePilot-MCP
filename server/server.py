import os
import sys
from pathlib import Path
from fastmcp import FastMCP

# Ensure the server directory is on sys.path for importing tools
SERVER_DIR = Path(__file__).resolve().parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from tools import (
    marks_to_grade_points,
    calculate_semester_gpa,
    calculate_new_cgpa,
    required_gpa_for_target,
    get_semester_courses,
    get_remaining_credit_hours,
    save_report,
)

# Optional authentication support using FASTMCP_KEY for deployment
fastmcp_key = os.environ.get("FASTMCP_KEY")
if fastmcp_key:
    from fastmcp.server.auth import TokenVerifier, AccessToken

    class StaticTokenVerifier(TokenVerifier):
        def __init__(self, key: str):
            super().__init__()
            self.key = key

        async def verify_token(self, token: str) -> AccessToken | None:
            if token == self.key:
                return AccessToken(token=token, client_id="authorized-client", scopes=[])
            return None

    mcp = FastMCP("PUCIT-CGPA-Guider", auth=StaticTokenVerifier(fastmcp_key))
else:
    mcp = FastMCP("PUCIT-CGPA-Guider")

# Register all seven tools
mcp.tool()(marks_to_grade_points.func)
mcp.tool()(calculate_semester_gpa.func)
mcp.tool()(calculate_new_cgpa.func)
mcp.tool()(required_gpa_for_target.func)
mcp.tool()(get_semester_courses.func)
mcp.tool()(get_remaining_credit_hours.func)
mcp.tool()(save_report.func)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))

    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=port,
        path="/mcp"
    )
