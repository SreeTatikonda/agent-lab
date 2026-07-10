from pydantic import BaseModel, Field
from typing import List, Optional

class ActionItem(BaseModel):
    text: str = Field(description="Clear, actionable task description")
    assignee: Optional[str] = Field(None, description="Name of the person responsible for the task, or None if unassigned")
    deadline: Optional[str] = Field(None, description="Due date in YYYY-MM-DD format, or None if not specified")
    status: str = Field("Pending", description="Status of the action item, e.g. Pending, In Progress, Completed")

class TranscriptSegment(BaseModel):
    speaker: str = Field(description="Name or ID of the speaker")
    text: str = Field(description="The exact or summarized text spoken by the speaker")
    timestamp: float = Field(description="Approximate timestamp in seconds from the beginning of the meeting")

class MeetingNotes(BaseModel):
    title: str = Field(description="Descriptive and professional title for the meeting")
    date: str = Field(description="Date and time of the meeting (e.g. YYYY-MM-DD or standard ISO format)")
    summary: str = Field(description="Detailed executive summary highlighting the primary purpose, discussions, and outcomes")
    template: str = Field("general", description="The meeting template used: general, standup, brainstorm, or demo")
    attendees: List[str] = Field(description="List of all unique participants identified in the meeting")
    decisions: List[str] = Field(description="List of key decisions made during the meeting")
    action_items: List[ActionItem] = Field(description="List of action items generated during the meeting")
    transcript: List[TranscriptSegment] = Field(description="Chronological transcript of the meeting conversation with speaker tagging and timestamps")

class Ticket(BaseModel):
    title: str = Field(description="Short, descriptive title for the ticket task")
    description: str = Field(description="Detailed explanation of the task, context, and definition of done")
    assignee: Optional[str] = Field(None, description="Assignee username or profile handle, or None if unassigned")
    priority: str = Field("Medium", description="Task priority: Low, Medium, High, or Critical")
    platform: str = Field("Jira", description="Target platform for the ticket, e.g. Jira, GitHub, Linear")

class TicketList(BaseModel):
    tickets: List[Ticket] = Field(description="List of tickets generated")

class OrchestratorOutput(BaseModel):
    meeting_notes: MeetingNotes = Field(description="Extracted structured meeting notes and transcript")
    email_draft_tool_output: dict = Field(description="Structured JSON response from the create_email_draft tool")
    calendar_event_tool_output: Optional[dict] = Field(None, description="Structured JSON response from the create_calendar_event tool, if called")
    tickets_tool_output: List[dict] = Field(description="List of structured JSON responses from the create_ticket tool")
