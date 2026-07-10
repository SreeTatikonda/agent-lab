import pytest
from pydantic import ValidationError
from schemas import ActionItem, TranscriptSegment, MeetingNotes

def test_action_item_valid():
    """Verify that a valid ActionItem model can be instantiated."""
    item = ActionItem(
        text="Set up database index",
        assignee="David",
        deadline="2026-07-01",
        status="Pending"
    )
    assert item.text == "Set up database index"
    assert item.assignee == "David"
    assert item.deadline == "2026-07-01"
    assert item.status == "Pending"

def test_action_item_defaults():
    """Verify default fields of ActionItem."""
    item = ActionItem(text="Draft roadmap")
    assert item.assignee is None
    assert item.deadline is None
    assert item.status == "Pending"

def test_transcript_segment_valid():
    """Verify TranscriptSegment model fields."""
    segment = TranscriptSegment(
        speaker="Alex",
        text="Hello everyone",
        timestamp=12.5
    )
    assert segment.speaker == "Alex"
    assert segment.text == "Hello everyone"
    assert segment.timestamp == 12.5

def test_meeting_notes_validation():
    """Verify complete validation of MeetingNotes."""
    notes_data = {
        "title": "Weekly Alignment",
        "date": "2026-06-25",
        "summary": "This was a standard alignment meeting.",
        "attendees": ["Alex", "Sarah"],
        "decisions": ["Deploy next Tuesday"],
        "action_items": [
            {"text": "Write tests", "assignee": "Sarah"}
        ],
        "transcript": [
            {"speaker": "Alex", "text": "Are we ready?", "timestamp": 0.0},
            {"speaker": "Sarah", "text": "Yes, I am.", "timestamp": 5.2}
        ]
    }
    
    notes = MeetingNotes.model_validate(notes_data)
    assert notes.title == "Weekly Alignment"
    assert len(notes.attendees) == 2
    assert len(notes.action_items) == 1
    assert notes.action_items[0].text == "Write tests"
    assert notes.action_items[0].status == "Pending"
    assert len(notes.transcript) == 2
    assert notes.transcript[1].speaker == "Sarah"

def test_meeting_notes_missing_required():
    """Verify that missing required fields in MeetingNotes raises validation errors."""
    incomplete_data = {
        "title": "Incomplete Meeting",
        # Missing required fields like date, summary, attendees, decisions, action_items, transcript
    }
    with pytest.raises(ValidationError):
        MeetingNotes.model_validate(incomplete_data)
