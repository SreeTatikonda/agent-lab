import pytest
import config
from schemas import MeetingNotes, ActionItem, TranscriptSegment
from agent import generate_dynamic_mock_notes, analyze_transcript, chat_with_meeting

def test_generate_dynamic_mock_notes_sample():
    """Verify that sample transcript text triggers high-fidelity kickoff mock notes."""
    sample_text = "Let's use React, Vite, and FastAPI. Also glassmorphic design rules."
    notes = generate_dynamic_mock_notes(sample_text, "general")
    assert notes.title == "Project Echo Kickoff"
    assert "FastAPI" in notes.summary
    assert "Sarah" in notes.attendees or "Alex (PM)" in notes.attendees
    assert len(notes.action_items) > 0

def test_generate_dynamic_mock_notes_generic():
    """Verify that generic custom transcripts generate standard structure dynamically."""
    custom_text = """
    [00:10] John: Hello everyone.
    [00:20] Alice: Hey John. Let's decide to build the monolith first.
    [00:45] John: Yes, write a task for Alice to write the code.
    """
    notes = generate_dynamic_mock_notes(custom_text, "brainstorm")
    assert notes.title == "Analyzed Meeting"
    assert "Alice" in notes.attendees
    assert "John" in notes.attendees
    assert len(notes.action_items) == 1
    assert notes.action_items[0].assignee in ["Alice", "John"]

def test_mock_chat_responses():
    """Test rule-based chat responses when in Mock Mode."""
    # Ensure config points to mock mode for offline testing
    config.MOCK_MODE = True
    
    mock_notes = MeetingNotes(
        title="Testing Sync",
        date="2026-06-25",
        summary="A simple test sync.",
        attendees=["Developer A", "Developer B"],
        decisions=["Test all pipelines"],
        action_items=[
            ActionItem(text="Write python tests", assignee="Developer A", deadline="2026-07-01")
        ],
        transcript=[
            TranscriptSegment(speaker="Developer A", text="I'll write tests", timestamp=0.0)
        ]
    )
    
    history = []
    
    # Test asking about attendees
    resp_attendees = chat_with_meeting(mock_notes, history, "Who attended this meeting?")
    assert "Developer A" in resp_attendees
    assert "Developer B" in resp_attendees
    
    # Test asking about decisions
    resp_decisions = chat_with_meeting(mock_notes, history, "What decisions did they make?")
    assert "Test all pipelines" in resp_decisions
    
    # Test asking about actions
    resp_actions = chat_with_meeting(mock_notes, history, "What are the action items?")
    assert "Write python tests" in resp_actions
    
    # Test fallback message
    resp_other = chat_with_meeting(mock_notes, history, "Why did they build it?")
    assert "Offline Demo Mode" in resp_other
