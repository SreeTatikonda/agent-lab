# EchoScribe AI - Meeting Notes Agent

A lightweight, local command-line agent that processes meeting transcripts into structured notes (executive summary, decisions, action items) using the Google Gemini API (via the modern `google-genai` SDK) and Pydantic schemas. It also includes an interactive CLI chat interface to ask questions about the meeting.

---

## Key Features

* **Structured Analysis**: Leverages Gemini's structured JSON outputs matched directly to Pydantic schemas (`schemas.py`) to guarantee consistent results.
* **Dual Reports**: Generates both clean, parseable JSON files and user-friendly, pre-formatted Markdown documents (`.md`) for every meeting.
* **Semantic Chat**: Launches a terminal chat loop allowing you to query decisions, speaker segments, or overall goals using the meeting transcript as context.
* **Offline Mock Mode**: Runs fully offline using a dynamic simulator if no Gemini API Key is configured, making it instantly testable out-of-the-box.
* **Automated Test Suite**: Built-in test coverage using `pytest` for validation and agent processing logic.

---

## Directory Structure

```text
meeting-notes-agent/
├── README.md               # Documentation
├── requirements.txt         # Package dependencies
├── .env.example            # Configuration template
├── config.py               # SDK and environment loading
├── schemas.py              # Pydantic schemas (Action items, transcript segments, notes)
├── agent.py                # Core Gemini API and Offline Simulator engine
├── main.py                 # Command Line Interface (CLI) entry point
├── data/
│   ├── samples/
│   │   └── sample_transcript.txt  # Default input transcript for testing
│   └── processed/          # Saved JSON and Markdown outputs
└── tests/
    ├── test_schemas.py     # Schema validation tests
    └── test_agent.py       # Offline agent/chat logic tests
```

---

## Setup Instructions

### 1. Initialize Virtual Environment & Dependencies
Open your terminal in the project directory:

```bash
# Create a virtual environment
python -m venv venv

# Activate it (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Open `.env` and set your key:
```env
GEMINI_API_KEY=AIzaSy...your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
```
*Note: If `GEMINI_API_KEY` is left blank or set to default placeholder, the application automatically launches in **Offline Mock Mode** using pre-configured mock data.*

---

## CLI Usage Guide

The CLI operates on three primary sub-commands: `process`, `list`, and `chat`.

### 1. Process a Transcript
Analyze a raw text transcript and output structured files.
```bash
python main.py process --file data/samples/sample_transcript.txt --template general
```
Options:
* `--file` or `-f` (Required): Path to transcript file.
* `--template` or `-t` (Optional): Analysis focus. Options: `general` (default), `standup`, `brainstorm`, `demo`.

This will save two files in `data/processed/`:
* `data/processed/meeting_<timestamp>_<title>.json`
* `data/processed/meeting_<timestamp>_<title>.md`

### 2. List Processed Meetings
List all available processed meetings in the system.
```bash
python main.py list
```

### 3. Chat with a Meeting Agent
Launch an interactive CLI chat session about the meeting.
```bash
python main.py chat --meeting-id <meeting_id>
```
*Tip: You only need to type a partial match of the meeting ID.*

During the chat:
* Type your question and press `Enter`.
* Type `exit` or `quit` to end the session.

---

## Running Tests

Verify code validation and fallback mechanisms:

```bash
pytest
```
All unit tests should pass successfully.
