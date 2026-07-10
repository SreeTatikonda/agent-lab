import re
import config
from typing import List
from schemas import MeetingNotes, ActionItem, TranscriptSegment, Ticket, TicketList

# High-fidelity mock notes representing the sample transcript
SAMPLE_MOCK_NOTES = MeetingNotes(
    title="Project Echo Kickoff",
    date="2026-06-25",
    summary="Kickoff meeting for Project Echo. The team discussed and finalized the core tech stack (React, TypeScript, Vite for frontend; FastAPI, PostgreSQL for backend) and agreed on a glassmorphic dark-mode design system. Key initial tasks were assigned to Sarah, David, Emma, and Alex to set up base boilerplates and wireframes.",
    template="general",
    attendees=["Alex (PM)", "Sarah (Frontend Dev)", "David (Backend Dev)", "Emma (Designer)"],
    decisions=[
        "Use React + TypeScript + Vite for the frontend application.",
        "Use Python + FastAPI for the backend API development.",
        "Use PostgreSQL as the primary relational database.",
        "Adopt a glassmorphic dark-mode theme for the UI design."
    ],
    action_items=[
        ActionItem(text="Initialize React project boilerplate with Vite and TypeScript", assignee="Sarah", deadline="2026-06-26", status="Pending"),
        ActionItem(text="Draft initial PostgreSQL database schema design and migrations", assignee="David", deadline="2026-07-05", status="Pending"),
        ActionItem(text="Deliver high-fidelity Figma wireframes and layout designs", assignee="Emma", deadline="2026-06-30", status="Pending"),
        ActionItem(text="Set up Jira board and prepare project roadmap slides", assignee="Alex", deadline="2026-06-26", status="Pending")
    ],
    transcript=[
        TranscriptSegment(speaker="Alex (PM)", text="Hi team, welcome to the kickoff for our new project. Today we need to align on the core features, select our technology stack, and distribute the initial development tasks.", timestamp=0.0),
        TranscriptSegment(speaker="Sarah (Frontend Dev)", text="For the client application, I'm proposing we use React + TypeScript built with Vite.", timestamp=20.0),
        TranscriptSegment(speaker="David (Backend Dev)", text="For the API backend, I suggest Python using FastAPI with PostgreSQL for storage.", timestamp=45.0),
        TranscriptSegment(speaker="Emma (Designer)", text="I will have the Figma wireframes for the dashboard finished by June 30th.", timestamp=75.0),
        TranscriptSegment(speaker="Alex (PM)", text="Great. Sarah, can you initialize the React boilerplate by Friday?", timestamp=110.0),
        TranscriptSegment(speaker="David (Backend Dev)", text="I will draft the initial database schema design by July 5th.", timestamp=135.0)
    ]
)

def generate_dynamic_mock_notes(transcript_text: str, template: str) -> MeetingNotes:
    """
    Parses raw transcript text to construct a realistic MeetingNotes structure offline.
    """
    speakers = set()
    lines = transcript_text.split('\n')
    
    for line in lines:
        line_clean = line.strip()
        match_ts = re.search(r'\]\s*([^:]+):', line_clean)
        if match_ts:
            speakers.add(match_ts.group(1).strip())
        else:
            match_no_ts = re.match(r'^([^:\[]+):', line_clean)
            if match_no_ts:
                speakers.add(match_no_ts.group(1).strip())

    attendees = sorted(list(speakers)) if speakers else ["Speaker 1", "Speaker 2"]
    
    if any(keyword in transcript_text for keyword in ["React", "FastAPI", "glassmorphic"]):
        notes = SAMPLE_MOCK_NOTES.model_copy(deep=True)
        notes.template = template
        return notes

    return MeetingNotes(
        title="Analyzed Meeting",
        date="2026-06-26",
        summary=f"Processed meeting notes based on transcript template: '{template}'. The participants discussed project status, resolved pending issues, and set up next step assignments.",
        template=template,
        attendees=attendees,
        decisions=[
            "Set up recurring review schedule for the team.",
            "Approved the draft project objectives."
        ],
        action_items=[
            ActionItem(text="Review transcript actions and update team log", assignee=attendees[0] if attendees else "Unassigned", deadline="2026-07-01", status="Pending")
        ],
        transcript=[
            TranscriptSegment(speaker=attendees[0], text="Let's make sure we document all action items.", timestamp=5.0)
        ]
    )

def analyze_transcript(transcript_text: str, template: str) -> MeetingNotes:
    """
    Analyzes meeting transcript text using the Gemini API.
    If in Mock Mode, returns mock notes.
    """
    if config.MOCK_MODE:
        return generate_dynamic_mock_notes(transcript_text, template)

    client = config.get_genai_client()
    
    prompt = f"Analyze the following meeting transcript:\n\n{transcript_text}"
    
    system_instruction = f"""
    You are a professional meeting assistant. Analyze the transcript and extract structured meeting notes.
    Adapt your analysis style to the selected template: '{template}'.
    - general: Balanced, high-level summary and general tasks.
    - standup: Focus on updates, progress, blockers, and immediate tasks.
    - brainstorm: Focus on ideas, trade-offs, architecture decisions, and design principles.
    - demo: Focus on client questions, feedback, and sales follow-up items.
    """

    from google.genai import types
    
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MeetingNotes,
            system_instruction=system_instruction
        )
    )
    
    if not response.text:
        raise ValueError("Empty response received from Gemini API.")
        
    return MeetingNotes.model_validate_json(response.text)

def generate_tickets(meeting: MeetingNotes) -> List[Ticket]:
    """
    Converts action items from the meeting notes into software development tickets.
    If in Mock Mode, dynamically builds tickets offline.
    """
    if config.MOCK_MODE:
        tickets = []
        for i, item in enumerate(meeting.action_items):
            platform = "GitHub" if meeting.template in ["brainstorm", "standup"] else "Jira"
            tickets.append(Ticket(
                title=f"Task: {item.text[:40]}...",
                description=f"Action Item: {item.text}\nAssignee: {item.assignee or 'Unassigned'}\nDeadline: {item.deadline or 'None'}\n\nGenerated from meeting '{meeting.title}' on {meeting.date}.",
                assignee=item.assignee,
                priority="High" if item.deadline or i == 0 else "Medium",
                platform=platform
            ))
        return tickets

    client = config.get_genai_client()
    prompt = f"Convert these action items from the meeting '{meeting.title}' into software development tickets:\n\n"
    for item in meeting.action_items:
        prompt += f"- Action: {item.text}, Assignee: {item.assignee}, Deadline: {item.deadline}\n"
    
    from google.genai import types
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TicketList,
            system_instruction="You are a technical project manager. Create structured tickets for each action item. Make the descriptions detailed, containing context, steps, and definition of done based on the meeting context."
        )
    )
    result = TicketList.model_validate_json(response.text)
    return result.tickets

def generate_email_draft(meeting: MeetingNotes) -> str:
    """
    Generates a professional follow-up email summarizing the meeting.
    """
    if config.MOCK_MODE:
        decisions_str = "\n".join([f"- {d}" for d in meeting.decisions])
        action_str = ""
        for item in meeting.action_items:
            due = f" (Due: {item.deadline})" if item.deadline else ""
            assignee = f" [{item.assignee}]" if item.assignee else ""
            action_str += f"- [ ] {item.text}{assignee}{due}\n"
            
        email = f"""Subject: Meeting Follow-up & Action Items: {meeting.title}

Hi Team,

Thank you for joining today's meeting. Here is a summary of what was discussed, decisions made, and next steps.

### Executive Summary
{meeting.summary}

### Key Decisions
{decisions_str if decisions_str else "- No major decisions recorded."}

### Action Items
{action_str if action_str else "- No action items assigned."}

Best regards,
EchoScribe Meeting Assistant
"""
        return email

    client = config.get_genai_client()
    prompt = f"""Generate a professional follow-up email based on these meeting notes:
Title: {meeting.title}
Summary: {meeting.summary}
Attendees: {', '.join(meeting.attendees)}
Decisions: {meeting.decisions}
Action Items: {[item.model_dump() for item in meeting.action_items]}
"""
    from google.genai import types
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction="You are a professional business assistant. Draft a polished, highly clear follow-up email to the meeting attendees summarizing the meeting. Use professional Markdown formatting."
        )
    )
    return response.text or "Follow-up email could not be generated."

def chat_with_meeting(meeting: MeetingNotes, chat_history: list, new_message: str) -> str:
    """
    Chats with the meeting notes context.
    If in Mock Mode, answers basic queries using simple rule matching.
    """
    if config.MOCK_MODE:
        msg_lower = new_message.lower()
        if "attend" in msg_lower or "who was" in msg_lower or "people" in msg_lower:
            return f"The attendees listed in the meeting notes are: {', '.join(meeting.attendees)}."
        elif "decision" in msg_lower or "decided" in msg_lower:
            decisions_str = "\n".join([f"- {d}" for d in meeting.decisions])
            return f"Here are the key decisions made:\n{decisions_str}"
        elif "action" in msg_lower or "todo" in msg_lower or "task" in msg_lower:
            actions_str = "\n".join([f"- {item.text} (Assigned to: {item.assignee or 'Unassigned'}, Deadline: {item.deadline or 'None'})" for item in meeting.action_items])
            return f"Here are the action items:\n{actions_str}"
        elif "summary" in msg_lower or "about" in msg_lower:
            return f"Meeting Summary: {meeting.summary}"
        else:
            return (
                "**Offline Demo Mode Response**:\n"
                "I detected your query, but because you are running in Mock Mode (no API key configured), "
                "I can only answer simple questions about 'attendees', 'decisions', 'action items', or 'summary'.\n\n"
                "To enable full semantic reasoning and search across the entire transcript, please configure a "
                "valid `GEMINI_API_KEY` in your `.env` file."
            )

    client = config.get_genai_client()
    
    transcript_str = "\n".join([f"[{seg.timestamp}s] {seg.speaker}: {seg.text}" for seg in meeting.transcript])
    context = f"""
    MEETING ANALYSIS DATA:
    Title: {meeting.title}
    Date: {meeting.date}
    Summary: {meeting.summary}
    Attendees: {', '.join(meeting.attendees)}
    Decisions:
    {chr(10).join(['- ' + d for d in meeting.decisions])}
    
    TRANSCRIPT:
    {transcript_str}
    """
    
    prompt = f"Meeting Context:\n{context}\n\nChat History:\n"
    for msg in chat_history:
        role = "User" if msg["role"] == "user" else "Assistant"
        prompt += f"{role}: {msg['text']}\n"
    
    prompt += f"User Query: {new_message}\nAssistant:"
    
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt
    )
    
    return response.text or "I'm sorry, I couldn't formulate a response."
