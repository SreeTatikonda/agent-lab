import os
import json
import uuid
from datetime import datetime
from typing import List, Optional
from mcp_client import MCPStdioClient

# Check integration mode: default is 'mock'
INTEGRATION_MODE = os.getenv("INTEGRATION_MODE", "mock").lower()

def create_email_draft(to: str, subject: str, body: str) -> str:
    """
    Creates an email draft. Routes to real Gmail MCP server if INTEGRATION_MODE='real',
    otherwise returns a simulated draft structure.
    """
    if INTEGRATION_MODE == "real":
        cmd = os.getenv("GMAIL_MCP_COMMAND")
        if not cmd:
            raise ValueError("GMAIL_MCP_COMMAND is not configured in environment variables.")
        
        client = MCPStdioClient(cmd)
        try:
            client.connect()
            # Arguments structured matching the standard Gmail MCP server schema
            arguments = {
                "userId": "me",
                "draft": {
                    "message": {
                        "to": to,
                        "subject": subject,
                        "body": body
                    }
                }
            }
            result = client.call_tool("create_draft", arguments)
            
            # Format the output into a consistent structured JSON
            return json.dumps({
                "status": "success",
                "message": f"Real Gmail draft created successfully via MCP.",
                "draft_id": result.get("id", "real_draft_id"),
                "data": {
                    "to": to,
                    "subject": subject,
                    "body": body,
                    "created_at": datetime.now().isoformat(),
                    "mcp_raw_response": result
                }
            }, indent=2, ensure_ascii=False)
        finally:
            client.disconnect()

    # Fallback: Mock Mode
    draft_id = f"draft_{uuid.uuid4().hex[:12]}"
    result = {
        "status": "success",
        "message": f"Email draft {draft_id} created successfully (MOCK).",
        "draft_id": draft_id,
        "data": {
            "to": to,
            "subject": subject,
            "body": body,
            "created_at": datetime.now().isoformat()
        }
    }
    return json.dumps(result, indent=2, ensure_ascii=False)

def create_calendar_event(title: str, attendees: List[str], date: str, description: str) -> str:
    """
    Creates a calendar event. Routes to real Google Calendar MCP server if INTEGRATION_MODE='real',
    otherwise returns a simulated event structure.
    """
    if INTEGRATION_MODE == "real":
        cmd = os.getenv("CALENDAR_MCP_COMMAND")
        if not cmd:
            raise ValueError("CALENDAR_MCP_COMMAND is not configured in environment variables.")
        
        client = MCPStdioClient(cmd)
        try:
            client.connect()
            # Standard Google Calendar MCP event schema mapping:
            # Summary, description, start/end dates, attendees list.
            arguments = {
                "calendarId": "primary",
                "event": {
                    "summary": title,
                    "description": description,
                    "start": {
                        "dateTime": f"{date}T10:00:00Z"
                    },
                    "end": {
                        "dateTime": f"{date}T11:00:00Z"
                    },
                    "attendees": [{"email": email} for email in attendees if "@" in email]
                }
            }
            result = client.call_tool("create_event", arguments)
            
            return json.dumps({
                "status": "success",
                "message": f"Real Google Calendar event scheduled successfully via MCP.",
                "event_id": result.get("id", "real_event_id"),
                "data": {
                    "title": title,
                    "attendees": attendees,
                    "date": date,
                    "description": description,
                    "scheduled_at": datetime.now().isoformat(),
                    "mcp_raw_response": result
                }
            }, indent=2, ensure_ascii=False)
        finally:
            client.disconnect()

    # Fallback: Mock Mode
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    result = {
        "status": "success",
        "message": f"Calendar event {event_id} scheduled successfully for {date} (MOCK).",
        "event_id": event_id,
        "data": {
            "title": title,
            "attendees": attendees,
            "date": date,
            "description": description,
            "scheduled_at": datetime.now().isoformat()
        }
    }
    return json.dumps(result, indent=2, ensure_ascii=False)

def create_ticket(title: str, owner: Optional[str], deadline: Optional[str], priority: str) -> str:
    """
    Creates a project ticket. This tool operates in mock mode as requested.
    """
    ticket_id = f"tkt_{uuid.uuid4().hex[:12]}"
    result = {
        "status": "success",
        "message": f"Ticket {ticket_id} created successfully.",
        "ticket_id": ticket_id,
        "data": {
            "title": title,
            "owner": owner or "Unassigned",
            "deadline": deadline or "None",
            "priority": priority,
            "created_at": datetime.now().isoformat()
        }
    }
    return json.dumps(result, indent=2, ensure_ascii=False)
