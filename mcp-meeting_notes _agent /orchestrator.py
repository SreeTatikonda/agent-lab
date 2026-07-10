import os
import json
from datetime import datetime, timedelta
from typing import Callable, List, Optional
from schemas import OrchestratorOutput, MeetingNotes
import agent
import mcp_tools

class MeetingOrchestrator:
    """
    Orchestrates the full pipeline of transcript analysis and invokes mock/real MCP tools,
    incorporating interactive confirmation loops for email and calendar event creation.
    """
    
    def run_pipeline(
        self, 
        transcript_text: str, 
        template: str = "general",
        confirm_email_callback: Optional[Callable[[str, str, str], bool]] = None,
        confirm_calendar_callback: Optional[Callable[[str, List[str], str, str], bool]] = None
    ) -> OrchestratorOutput:
        """
        Runs the end-to-end meeting notes analysis and integration tool pipeline.
        Prompts for confirmation before calling email and calendar tools.
        """
        # Step 1: Extract meeting notes
        meeting_notes = agent.analyze_transcript(transcript_text, template)
        
        # Step 2: Formulate email
        raw_email_body = agent.generate_email_draft(meeting_notes)
        email_recipient = "team@company.local"
        email_subject = f"Follow-up: {meeting_notes.title}"
        
        # Check email confirmation
        email_confirmed = True
        if confirm_email_callback:
            email_confirmed = confirm_email_callback(email_recipient, email_subject, raw_email_body)
            
        if email_confirmed:
            email_draft_json = mcp_tools.create_email_draft(
                to=email_recipient,
                subject=email_subject,
                body=raw_email_body
            )
            email_draft_output = json.loads(email_draft_json)
        else:
            email_draft_output = {
                "status": "skipped",
                "message": "User declined to create email draft.",
                "data": {
                    "to": email_recipient,
                    "subject": email_subject,
                    "body": raw_email_body
                }
            }
        
        # Step 3: Map action items and call create_ticket tool for each (no confirmation required)
        tickets_output = []
        for item in meeting_notes.action_items:
            priority = "High" if item.deadline or item.status == "Pending" else "Medium"
            ticket_json = mcp_tools.create_ticket(
                title=item.text,
                owner=item.assignee,
                deadline=item.deadline,
                priority=priority
            )
            tickets_output.append(json.loads(ticket_json))
            
        # Step 4: Schedule follow-up calendar event
        meeting_date = datetime.now()
        followup_date = (meeting_date + timedelta(days=7)).strftime("%Y-%m-%d")
        event_title = f"Follow-up Sync: {meeting_notes.title}"
        event_description = f"Action items review and alignment sync for project: {meeting_notes.title}."
        
        # Check calendar confirmation
        calendar_confirmed = True
        if confirm_calendar_callback:
            calendar_confirmed = confirm_calendar_callback(
                event_title,
                meeting_notes.attendees,
                followup_date,
                event_description
            )
            
        if calendar_confirmed:
            calendar_json = mcp_tools.create_calendar_event(
                title=event_title,
                attendees=meeting_notes.attendees,
                date=followup_date,
                description=event_description
            )
            calendar_output = json.loads(calendar_json)
        else:
            calendar_output = {
                "status": "skipped",
                "message": "User declined to schedule calendar event.",
                "data": {
                    "title": event_title,
                    "attendees": meeting_notes.attendees,
                    "date": followup_date,
                    "description": event_description
                }
            }
        
        return OrchestratorOutput(
            meeting_notes=meeting_notes,
            email_draft_tool_output=email_draft_output,
            calendar_event_tool_output=calendar_output,
            tickets_tool_output=tickets_output
        )

    def save_outputs(self, output: OrchestratorOutput, base_dir: str, meeting_id: str):
        """
        Saves the orchestrator results as local files.
        """
        os.makedirs(base_dir, exist_ok=True)
        
        # 1. Save full JSON dataset
        json_path = os.path.join(base_dir, f"{meeting_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output.model_dump(), f, indent=2, ensure_ascii=False)
            
        # 2. Save follow-up email draft body (only if success, otherwise save skipped message)
        email_path = os.path.join(base_dir, f"{meeting_id}_email.txt")
        email_body = output.email_draft_tool_output.get("data", {}).get("body", "")
        if output.email_draft_tool_output.get("status") == "skipped":
            email_body = f"SKIPPED: {output.email_draft_tool_output.get('message')}\n\nOriginal Draft Content:\n{email_body}"
            
        with open(email_path, "w", encoding="utf-8") as f:
            f.write(email_body)
            
        # 3. Save tickets report (Markdown format)
        tickets_path = os.path.join(base_dir, f"{meeting_id}_tickets.md")
        tickets_md = f"# Integration Tickets: {output.meeting_notes.title}\n\n"
        if output.tickets_tool_output:
            for i, ticket in enumerate(output.tickets_tool_output, 1):
                ticket_data = ticket.get("data", {})
                tickets_md += f"## Ticket {i}: {ticket_data.get('title')}\n"
                tickets_md += f"* **ID:** {ticket.get('ticket_id')}\n"
                tickets_md += f"* **Owner:** {ticket_data.get('owner')}\n"
                tickets_md += f"* **Deadline:** {ticket_data.get('deadline')}\n"
                tickets_md += f"* **Priority:** {ticket_data.get('priority')}\n"
                tickets_md += f"* **Status:** {ticket.get('status').upper()}\n"
                tickets_md += f"* **Message:** {ticket.get('message')}\n\n"
                tickets_md += "---\n\n"
        else:
            tickets_md += "*No tickets were created.*\n"
            
        with open(tickets_path, "w", encoding="utf-8") as f:
            f.write(tickets_md)
            
        # 4. Save calendar event metadata report
        if output.calendar_event_tool_output:
            cal_path = os.path.join(base_dir, f"{meeting_id}_calendar.md")
            cal_data = output.calendar_event_tool_output.get("data", {})
            cal_md = f"# Scheduled Calendar Event: {cal_data.get('title')}\n\n"
            
            if output.calendar_event_tool_output.get("status") == "skipped":
                cal_md += f"⚠️ **STATUS: SKIPPED** ({output.calendar_event_tool_output.get('message')})\n\n"
            else:
                cal_md += f"✅ **STATUS: SCHEDULED**\n\n"
                cal_md += f"* **Event ID:** {output.calendar_event_tool_output.get('event_id')}\n"
                
            cal_md += f"* **Proposed Date:** {cal_data.get('date')}\n"
            cal_md += f"* **Description:** {cal_data.get('description')}\n"
            cal_md += f"* **Attendees:** {', '.join(cal_data.get('attendees', []))}\n"
            
            if output.calendar_event_tool_output.get("status") != "skipped":
                cal_md += f"* **Confirmation:** {output.calendar_event_tool_output.get('message')}\n"
            
            with open(cal_path, "w", encoding="utf-8") as f:
                f.write(cal_md)
