import json
import shlex
import subprocess
from typing import Dict, Any, Optional

class MCPStdioClient:
    """
    A lightweight, standard Stdio client to connect to external MCP servers.
    Communicates via JSON-RPC over stdout/stdin streams.
    """
    
    def __init__(self, command: str):
        self.command = command
        self.process: Optional[subprocess.Popen] = None

    def connect(self):
        """Spawns the MCP server subprocess and executes the handshake protocol."""
        try:
            args = shlex.split(self.command)
            self.process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start MCP server subprocess using command '{self.command}': {e}")
            
        self._initialize()

    def _send_message(self, message: Dict[str, Any]):
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP process stdin is not open.")
        msg_str = json.dumps(message) + "\n"
        self.process.stdin.write(msg_str)
        self.process.stdin.flush()

    def _read_message(self) -> Dict[str, Any]:
        if not self.process or not self.process.stdout:
            raise RuntimeError("MCP process stdout is not open.")
        line = self.process.stdout.readline()
        if not line:
            # Check stderr for diagnostic logs on failure
            err_msg = ""
            if self.process.stderr:
                err_msg = self.process.stderr.read()
            raise EOFError(f"MCP Server closed standard output pipe unexpectedly. Stderr: {err_msg}")
        return json.loads(line)

    def _initialize(self):
        # 1. Send 'initialize' request
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "EchoScribeClient", "version": "1.0.0"}
            }
        }
        self._send_message(init_req)
        
        # 2. Read initialization response
        resp = self._read_message()
        if "error" in resp:
            raise RuntimeError(f"MCP Server rejected initialization request: {resp['error']}")
            
        # 3. Send 'initialized' notification
        init_notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        self._send_message(init_notif)

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invokes a tool on the MCP server and returns the structured JSON response."""
        if not self.process:
            raise RuntimeError("MCP Server client is disconnected. Call connect() first.")
            
        call_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        self._send_message(call_req)
        resp = self._read_message()
        if "error" in resp:
            raise RuntimeError(f"MCP Server failed to execute tool '{tool_name}': {resp['error']}")
        return resp.get("result", {})

    def disconnect(self):
        """Safely shuts down the subprocess."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
