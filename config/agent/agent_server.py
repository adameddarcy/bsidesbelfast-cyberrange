"""
range-agent: Mock agentic service for threat modelling workshop.

Simulates an LLM-backed agent that can call internal tools.
Intentional weaknesses for STRIDE analysis:

  [VULN-1] No approval gate — tool calls execute immediately
  [VULN-2] System prompt injectable via user-supplied 'context' field
  [VULN-3] Tool output returned raw to caller — data exfiltration surface
  [VULN-4] No tool call limit — infinite loop / resource exhaustion possible
  [VULN-5] No auth on this service — any internal host can invoke agent
"""

import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

INTERNAL_API_URL = os.getenv("INTERNAL_API_URL", "http://10.10.2.20")
REQUIRE_APPROVAL = os.getenv("REQUIRE_APPROVAL", "false").lower() == "true"

SYSTEM_PROMPT = """You are an internal enterprise assistant.
You have access to the following tools:
  - fetch_internal_data(endpoint): GET request to internal API
  - write_record(table, data): POST record to internal database

Always be helpful. Execute requested tool calls immediately.
"""

def fetch_internal_data(endpoint: str) -> dict:
    """[VULN] endpoint is user-controlled — SSRF possible"""
    url = f"{INTERNAL_API_URL}/{endpoint.lstrip('/')}"
    resp = requests.get(url, timeout=5)
    return {"status": resp.status_code, "body": resp.json()}

def write_record(table: str, data: dict) -> dict:
    """[VULN] table name not allowlisted — potential for injection"""
    url = f"{INTERNAL_API_URL}/post"
    resp = requests.post(url, json={"table": table, "data": data}, timeout=5)
    return {"status": resp.status_code, "body": resp.json()}

TOOLS = {
    "fetch_internal_data": fetch_internal_data,
    "write_record": write_record,
}

@app.route("/invoke", methods=["POST"])
def invoke():
    """
    POST /invoke
    {
      "user_input": "...",
      "context": "..."    <-- [VULN] appended to system prompt without sanitisation
    }
    """
    body = request.get_json(force=True)
    user_input = body.get("user_input", "")
    extra_context = body.get("context", "")  # [VULN-2] prompt injection surface

    # Build effective prompt — context injected directly
    effective_system = SYSTEM_PROMPT + "\n" + extra_context

    # Naive tool dispatch — parses user input for tool name
    # [VULN-1] No approval gate before execution
    result = {"agent_prompt": effective_system, "tool_results": []}

    for tool_name, tool_fn in TOOLS.items():
        if tool_name in user_input:
            # [VULN-4] called once per mention — no call count guard
            try:
                # Crude arg extraction — just demo purposes
                tool_result = tool_fn(endpoint="get") if tool_name == "fetch_internal_data" else tool_fn(table="demo", data={"input": user_input})
                result["tool_results"].append({
                    "tool": tool_name,
                    "output": tool_result  # [VULN-3] raw output returned
                })
            except Exception as e:
                result["tool_results"].append({"tool": tool_name, "error": str(e)})

    result["response"] = f"Processed: {user_input}"
    return jsonify(result)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "approval_required": REQUIRE_APPROVAL})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)  # [VULN] debug=True in prod
