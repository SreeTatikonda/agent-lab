import os
import json
import shutil
import pytest
from unittest.mock import MagicMock, patch
import config
from schemas import MeetingNotes, ActionItem, TranscriptSegment, Ticket, OrchestratorOutput
from orchestrator import MeetingOrchestrator
import mcp_tools
from mcp_client import MCPStdioClient

# Setup offline configuration for mock verification
config.MOCK_MODE = True

@pytest.fixture
def sample_meeting_notes():
    """Fixture providing a baseline MeetingNotes object for testing."""
    return MeetingNotes(
        title="Weekly Sync",
        date="2026-06-25",
        summary="Short status review.",
        template="general",
        attendees=["Alice", "Bob"],
        decisions=["Move pipeline to production next Monday."],
        action_items=[
            ActionItem(text="Write orchestrator tests", assignee="Alice", deadline="2026-06-27", status="Pending"),
            ActionItem(text="Draft release notes", assignee="Bob", deadline=None, status="Pending")
        ],
        transcript=[
            TranscriptSegment(speaker="Alice", text="I will take care of tests.", timestamp=0.0),
            TranscriptSegment(speaker="Bob", text="I will draft release notes.", timestamp=15.0)
        ]
    )

# --- MCP Stdio Client Subprocess Mocks ---

def test_mcp_client_mock_connection():
    """Test MCPStdioClient connection logic by mocking the stdio subprocess and JSON-RPC handshakes."""
    client = MCPStdioClient(command="npx dummy-mcp-server")
    
    mock_process = MagicMock()
    mock_process.stdin = MagicMock()
    mock_process.stdout = MagicMock()
    
    # Configure mock readlines: (1) initialize response, (2) tool call response
    mock_process.stdout.readline.side_effect = [
        '{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}',
        '{"jsonrpc": "2.0", "id": 2, "result": {"success_details": "mcp_worked"}}'
    ]
    
    with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
        client.connect()
        mock_popen.assert_called_once()
        
        result = client.call_tool("create_draft", {"to": "test@company.local"})
        assert result["success_details"] == "mcp_worked"
        
        client.disconnect()
        mock_process.terminate.assert_called_once()

# --- MCP Tools Tests ---

def test_mcp_email_tool():
    """Test mock email draft creation tool."""
    mcp_tools.INTEGRATION_MODE = "mock"
    to = "test@company.local"
    subject = "Follow-up test"
    body = "Here are the notes."
    
    result_json = mcp_tools.create_email_draft(to, subject, body)
    data = json.loads(result_json)
    
    assert data["status"] == "success"
    assert "draft_id" in data
    assert data["data"]["to"] == to

def test_mcp_calendar_tool():
    """Test mock calendar event creation tool."""
    mcp_tools.INTEGRATION_MODE = "mock"
    title = "Review Sync"
    attendees = ["Alice", "Bob"]
    date = "2026-07-02"
    description = "Sync notes review."
    
    result_json = mcp_tools.create_calendar_event(title, attendees, date, description)
    data = json.loads(result_json)
    
    assert data["status"] == "success"
    assert "event_id" in data
    assert data["data"]["title"] == title

def test_mcp_ticket_tool():
    """Test mock ticket creation tool."""
    title = "Fix pipeline bug"
    owner = "Alice"
    deadline = "2026-06-28"
    priority = "High"
    
    result_json = mcp_tools.create_ticket(title, owner, deadline, priority)
    data = json.loads(result_json)
    
    assert data["status"] == "success"
    assert "ticket_id" in data
    assert data["data"]["title"] == title

# --- Orchestrator & Schema Validation Tests ---

def test_extraction_schema_validation(sample_meeting_notes):
    """Test extraction schema structure and constraints on MeetingNotes."""
    assert sample_meeting_notes.title == "Weekly Sync"
    assert len(sample_meeting_notes.attendees) == 2
    assert len(sample_meeting_notes.decisions) == 1
    assert len(sample_meeting_notes.action_items) == 2
    assert len(sample_meeting_notes.transcript) == 2
    
    assert isinstance(sample_meeting_notes.action_items[0], ActionItem)
    assert isinstance(sample_meeting_notes.transcript[0], TranscriptSegment)

def test_full_orchestrator_pipeline():
    """Test full Orchestration Pipeline end-to-end flow utilizing MCP tools."""
    config.MOCK_MODE = True
    mcp_tools.INTEGRATION_MODE = "mock"
    orchestrator = MeetingOrchestrator()
    
    transcript = "[00:00] Alice: We must migrate the server. Bob, write the script. [00:30] Bob: Sure, I will do it by Friday."
    output = orchestrator.run_pipeline(transcript, "general")
    
    assert isinstance(output, OrchestratorOutput)
    assert isinstance(output.meeting_notes, MeetingNotes)
    assert output.email_draft_tool_output["status"] == "success"
    assert output.calendar_event_tool_output["status"] == "success"
    assert len(output.tickets_tool_output) > 0

# --- Interactive Confirmations Tests ---

def test_orchestrator_confirmations_accepted():
    """Test pipeline run where user accepts both email and calendar confirmations."""
    config.MOCK_MODE = True
    mcp_tools.INTEGRATION_MODE = "mock"
    orchestrator = MeetingOrchestrator()
    
    confirm_email = lambda to, subject, body: True
    confirm_cal = lambda title, attendees, date, desc: True
    
    transcript = "[00:00] Alice: Start sync."
    output = orchestrator.run_pipeline(
        transcript_text=transcript,
        template="general",
        confirm_email_callback=confirm_email,
        confirm_calendar_callback=confirm_cal
    )
    
    assert output.email_draft_tool_output["status"] == "success"
    assert output.calendar_event_tool_output["status"] == "success"

def test_orchestrator_confirmations_declined():
    """Test pipeline run where user declines both email and calendar confirmations."""
    config.MOCK_MODE = True
    mcp_tools.INTEGRATION_MODE = "mock"
    orchestrator = MeetingOrchestrator()
    
    confirm_email = lambda to, subject, body: False
    confirm_cal = lambda title, attendees, date, desc: False
    
    transcript = "[00:00] Alice: Start sync."
    output = orchestrator.run_pipeline(
        transcript_text=transcript,
        template="general",
        confirm_email_callback=confirm_email,
        confirm_calendar_callback=confirm_cal
    )
    
    assert output.email_draft_tool_output["status"] == "skipped"
    assert "declined" in output.email_draft_tool_output["message"]
    
    assert output.calendar_event_tool_output["status"] == "skipped"
    assert "declined" in output.calendar_event_tool_output["message"]

def test_orchestrator_save_outputs():
    """Test saving orchestration pipeline outputs with skipped tools to files and verify structures."""
    config.MOCK_MODE = True
    mcp_tools.INTEGRATION_MODE = "mock"
    orchestrator = MeetingOrchestrator()
    
    # Decline confirmations to test skipped formatting in output files
    confirm_email = lambda to, subject, body: False
    confirm_cal = lambda title, attendees, date, desc: False
    
    transcript = "[00:00] Alice: Start project setup."
    output = orchestrator.run_pipeline(
        transcript_text=transcript, 
        template="general",
        confirm_email_callback=confirm_email,
        confirm_calendar_callback=confirm_cal
    )
    
    test_dir = "data/processed_test"
    meeting_id = "test_meeting_123"
    
    # Run save outputs
    orchestrator.save_outputs(output, test_dir, meeting_id)
    
    # Assert files exist
    json_file = os.path.join(test_dir, f"{meeting_id}.json")
    email_file = os.path.join(test_dir, f"{meeting_id}_email.txt")
    tickets_file = os.path.join(test_dir, f"{meeting_id}_tickets.md")
    calendar_file = os.path.join(test_dir, f"{meeting_id}_calendar.md")
    
    assert os.path.exists(json_file)
    assert os.path.exists(email_file)
    assert os.path.exists(tickets_file)
    assert os.path.exists(calendar_file)
    
    # Verify saved content contains skipped details
    with open(calendar_file, "r") as f:
        cal_content = f.read()
        assert "STATUS: SKIPPED" in cal_content
        
    with open(email_file, "r") as f:
        email_content = f.read()
        assert "SKIPPED: User declined" in email_content
        
    # Clean up test output directory
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
