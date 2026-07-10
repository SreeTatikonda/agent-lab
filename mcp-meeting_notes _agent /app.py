import os
import json
from datetime import datetime
import streamlit as st
import config
import agent
from schemas import MeetingNotes, ActionItem, TranscriptSegment, OrchestratorOutput
from orchestrator import MeetingOrchestrator

# Set page configurations
st.set_page_config(
    page_title="EchoScribe AI - Meeting Notes Agent",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .reportview-container {
        background: #0b0f19;
    }
    .stDeployButton {
        display: none;
    }
    /* Custom tag styling */
    .attendee-tag {
        display: inline-block;
        padding: 4px 12px;
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        font-size: 13px;
        margin: 4px;
        color: #f3f4f6;
    }
    .decision-box {
        padding: 12px;
        background-color: rgba(16, 185, 129, 0.05);
        border-left: 4px solid #10b981;
        border-radius: 0 8px 8px 0;
        margin-bottom: 10px;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Ensure directories exist
os.makedirs("data/samples", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)

# Initialize Session States
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pipeline_output" not in st.session_state:
    st.session_state.pipeline_output = None
if "processing_step" not in st.session_state:
    st.session_state.processing_step = "input"  # input, confirm, done
if "selected_meeting_id" not in st.session_state:
    st.session_state.selected_meeting_id = None

# Sidebar - Workspace and History
st.sidebar.title("🎙️ EchoScribe AI")
st.sidebar.write("Meeting Notes Agent Dashboard")

# Workspace Mode Indicator
if config.MOCK_MODE:
    st.sidebar.warning("⚠️ Running in Offline Mock Mode")
else:
    st.sidebar.success("🟢 Connected to Gemini API")

st.sidebar.markdown("---")

# List processed files
processed_files = [f for f in os.listdir("data/processed") if f.endswith(".json")]
meeting_list = []
for f in processed_files:
    path = os.path.join("data/processed", f)
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
            notes_data = data.get("meeting_notes", data)
            meeting_list.append({
                "id": f[:-5],
                "title": notes_data.get("title", "Untitled"),
                "date": notes_data.get("date", "")[:10]
            })
    except:
        pass

# Sort meetings by date descending
meeting_list.sort(key=lambda x: x["id"], reverse=True)

# Select Meeting from history
st.sidebar.subheader("Meeting History")
if st.sidebar.button("➕ Process New Meeting", use_container_width=True):
    st.session_state.selected_meeting_id = None
    st.session_state.processing_step = "input"
    st.session_state.pipeline_output = None
    st.session_state.chat_history = []
    st.rerun()

st.sidebar.write("")
for meeting in meeting_list:
    btn_label = f"📁 {meeting['title']} ({meeting['date']})"
    if st.sidebar.button(btn_label, key=f"sel_{meeting['id']}", use_container_width=True):
        st.session_state.selected_meeting_id = meeting["id"]
        st.session_state.processing_step = "done"
        st.session_state.chat_history = []
        # Load the selected file
        path = os.path.join("data/processed", f"{meeting['id']}.json")
        with open(path, "r", encoding="utf-8") as file:
            notes_dict = json.load(file)
            
            # Migrate older legacy structures to OrchestratorOutput schemas in-memory
            if "meeting_notes" not in notes_dict:
                # Case 1: Legacy flat MeetingNotes format
                notes_dict = {
                    "meeting_notes": notes_dict,
                    "email_draft_tool_output": {
                        "status": "success",
                        "message": "Loaded legacy email draft.",
                        "draft_id": "legacy_draft",
                        "data": {"body": "Email draft details not saved in legacy structure.", "to": "team@company.local", "subject": "Follow-up"}
                    },
                    "calendar_event_tool_output": None,
                    "tickets_tool_output": []
                }
            else:
                # Case 2: Legacy OrchestratorOutput format with flat 'email_draft' and 'tickets' lists
                if "email_draft" in notes_dict and "email_draft_tool_output" not in notes_dict:
                    notes_dict["email_draft_tool_output"] = {
                        "status": "success",
                        "message": "Loaded legacy email draft.",
                        "draft_id": "legacy_draft",
                        "data": {"body": notes_dict["email_draft"], "to": "team@company.local", "subject": "Follow-up"}
                    }
                if "tickets" in notes_dict and "tickets_tool_output" not in notes_dict:
                    tickets_tool_output = []
                    for t in notes_dict.get("tickets", []):
                        tickets_tool_output.append({
                            "status": "success",
                            "message": "Loaded legacy ticket details.",
                            "ticket_id": "legacy_ticket",
                            "data": {
                                "title": t.get("title", ""),
                                "owner": t.get("assignee", "Unassigned"),
                                "deadline": t.get("deadline", "None"),
                                "priority": t.get("priority", "Medium")
                            }
                        })
                    notes_dict["tickets_tool_output"] = tickets_tool_output

            # Reconstruct OrchestratorOutput
            st.session_state.pipeline_output = OrchestratorOutput.model_validate(notes_dict)
        st.rerun()

# --- Main Panel ---
st.title("Meeting-to-Action Dashboard")

if st.session_state.processing_step == "input" and not st.session_state.selected_meeting_id:
    st.subheader("Process a New Meeting Transcript")
    
    # Transcript input options
    input_method = st.radio("Choose input method:", ["Paste Transcript Text", "Load Sample Transcript"])
    
    transcript_text = ""
    if input_method == "Load Sample Transcript":
        sample_path = "data/samples/sample_transcript.txt"
        if os.path.exists(sample_path):
            with open(sample_path, "r", encoding="utf-8") as f:
                transcript_text = f.read()
            st.text_area("Sample Transcript Preview:", value=transcript_text, height=250, disabled=True)
        else:
            st.error("Sample transcript file not found.")
    else:
        transcript_text = st.text_area("Paste your timestamped transcript here:", height=300, placeholder="[00:00] Speaker: Hello...")

    col1, col2 = st.columns(2)
    with col1:
        template = st.selectbox("Meeting Template Focus:", ["general", "standup", "brainstorm", "demo"])
    
    if st.button("Start Pipeline Analysis", type="primary", use_container_width=True):
        if not transcript_text.strip():
            st.error("Please enter or load a transcript first.")
        else:
            with st.spinner("Analyzing transcript and preparing follow-ups..."):
                # Step 1: Run extraction and generate raw proposals
                orchestrator = MeetingOrchestrator()
                # Run the pipeline without confirmation callbacks first to generate proposals
                output = orchestrator.run_pipeline(transcript_text, template)
                st.session_state.pipeline_output = output
                st.session_state.processing_step = "confirm"
                st.rerun()

elif st.session_state.processing_step == "confirm":
    st.subheader("⚠️ Interactive Confirmation Required")
    st.write("Please review the proposed drafts and events before executing integration integrations.")

    output = st.session_state.pipeline_output
    notes = output.meeting_notes

    st.markdown(f"### Meeting Title: **{notes.title}**")
    st.info(f"Summary: {notes.summary}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📧 Proposed Follow-up Email")
        email_data = output.email_draft_tool_output.get("data", {})
        st.text_input("To:", value=email_data.get("to"), disabled=True)
        st.text_input("Subject:", value=email_data.get("subject"), disabled=True)
        st.text_area("Body:", value=email_data.get("body"), height=250, disabled=True)
        approve_email = st.checkbox("Approve Email Draft Creation", value=True)

    with col2:
        st.markdown("### 📅 Proposed Calendar Sync Event")
        cal_data = output.calendar_event_tool_output.get("data", {})
        st.text_input("Event Title:", value=cal_data.get("title"), disabled=True)
        st.text_input("Date:", value=cal_data.get("date"), disabled=True)
        st.text_area("Description:", value=cal_data.get("description"), height=100, disabled=True)
        st.write(f"Attendees: {', '.join(cal_data.get('attendees', []))}")
        approve_calendar = st.checkbox("Approve Calendar Event Creation", value=True)

    if st.button("Finalize and Save Actions", type="primary", use_container_width=True):
        with st.spinner("Running tool integrations..."):
            # Update outputs based on user confirmation checks
            if not approve_email:
                output.email_draft_tool_output = {
                    "status": "skipped",
                    "message": "User declined to create email draft.",
                    "data": output.email_draft_tool_output.get("data", {})
                }
            if not approve_calendar:
                output.calendar_event_tool_output = {
                    "status": "skipped",
                    "message": "User declined to schedule calendar event.",
                    "data": output.calendar_event_tool_output.get("data", {})
                }

            # Create unique meeting ID and save files
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c for c in notes.title if c.isalnum() or c in (" ", "_", "-")).rstrip()
            safe_title = safe_title.replace(" ", "_").lower()
            meeting_id = f"meeting_{timestamp_str}_{safe_title}"

            orchestrator = MeetingOrchestrator()
            orchestrator.save_outputs(output, "data/processed", meeting_id)

            st.session_state.selected_meeting_id = meeting_id
            st.session_state.processing_step = "done"
            st.success("🎉 Integration outputs processed and saved successfully!")
            st.rerun()

elif st.session_state.processing_step == "done" and st.session_state.pipeline_output:
    output = st.session_state.pipeline_output
    notes = output.meeting_notes

    # Header Card
    st.subheader(f"📊 Dashboard: {notes.title}")
    st.write(f"**Meeting Date:** {notes.date[:10]} | **Attendees:** {', '.join(notes.attendees)}")

    # Tabs
    tab_summary, tab_tickets, tab_email, tab_calendar, tab_chat = st.tabs([
        "📝 Summary & Decisions", 
        "🎫 PM Tickets", 
        "✉️ Email Draft", 
        "📅 Calendar Event", 
        "💬 Interactive Meeting Agent"
    ])

    with tab_summary:
        st.markdown("### Executive Summary")
        st.write(notes.summary)
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Attendees")
            for att in notes.attendees:
                st.markdown(f'<span class="attendee-tag">👤 {att}</span>', unsafe_allow_html=True)
        with col2:
            st.markdown("### Key Decisions")
            if notes.decisions:
                for d in notes.decisions:
                    st.markdown(f'<div class="decision-box">💡 {d}</div>', unsafe_allow_html=True)
            else:
                st.write("*No major decisions recorded.*")

    with tab_tickets:
        st.markdown("### Generated Action Items & Tickets")
        if output.tickets_tool_output:
            for i, ticket in enumerate(output.tickets_tool_output, 1):
                ticket_data = ticket.get("data", {})
                status = ticket.get("status", "success").upper()
                
                exp_label = f"Ticket {i}: {ticket_data.get('title')} [{status}]"
                with st.expander(exp_label):
                    st.markdown(f"**Ticket ID:** `{ticket.get('ticket_id')}`")
                    st.markdown(f"**Assignee:** `{ticket_data.get('owner')}`")
                    st.markdown(f"**Deadline:** `{ticket_data.get('deadline')}`")
                    st.markdown(f"**Priority:** `{ticket_data.get('priority')}`")
                    st.markdown(f"**Confirmation Msg:** {ticket.get('message')}")
        else:
            st.write("*No action items/tickets assigned.*")

    with tab_email:
        st.markdown("### Follow-up Email Draft")
        email_status = output.email_draft_tool_output.get("status")
        
        if email_status == "skipped":
            st.warning("⚠️ This draft was SKIPPED based on your confirmation choice.")
        else:
            st.success("✅ Email Draft created successfully.")
            
        email_body = output.email_draft_tool_output.get("data", {}).get("body", "")
        st.text_area("Draft Text:", value=email_body, height=350)

    with tab_calendar:
        st.markdown("### Calendar Sync Event")
        cal_status = output.calendar_event_tool_output.get("status")
        cal_data = output.calendar_event_tool_output.get("data", {})
        
        if cal_status == "skipped":
            st.warning("⚠️ This calendar event was SKIPPED based on your confirmation choice.")
        else:
            st.success(f"✅ Event Scheduled Successfully! ID: `{output.calendar_event_tool_output.get('event_id')}`")
            
        st.write(f"**Title:** {cal_data.get('title')}")
        st.write(f"**Scheduled Date:** {cal_data.get('date')}")
        st.write(f"**Description:** {cal_data.get('description')}")
        st.write(f"**Attendees:** {', '.join(cal_data.get('attendees', []))}")

    with tab_chat:
        st.markdown("### Chat with the Meeting Agent")
        st.write("Ask questions regarding transcript segments, details, or decisions.")
        
        # Display history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["text"])
                
        # User input
        if user_msg := st.chat_input("Ask a question about this meeting:"):
            with st.chat_message("user"):
                st.write(user_msg)
            st.session_state.chat_history.append({"role": "user", "text": user_msg})
            
            with st.spinner("Analyzing transcript context..."):
                # Compile history for agent
                agent_history = [{"role": "user" if m["role"] == "user" else "model", "text": m["text"]} for m in st.session_state.chat_history[:-1]]
                response = agent.chat_with_meeting(notes, agent_history, user_msg)
                
            with st.chat_message("assistant"):
                st.write(response)
            st.session_state.chat_history.append({"role": "assistant", "text": response})
            st.rerun()
