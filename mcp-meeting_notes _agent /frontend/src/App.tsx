import React, { useState } from 'react';
import { Mic, AlertTriangle } from 'lucide-react';
import { analyzeMeeting } from './api';
import { OrchestratorOutput } from './types';

// Component imports
import { TranscriptInput } from './components/TranscriptInput';
import { AgentTimeline } from './components/AgentTimeline';
import { SummaryCard } from './components/SummaryCard';
import { DecisionsCard } from './components/DecisionsCard';
import { ActionItemsTable } from './components/ActionItemsTable';
import { TicketCards } from './components/TicketCards';
import { CalendarCard } from './components/CalendarCard';
import { EmailDraftCard } from './components/EmailDraftCard';
import { RawJsonPanel } from './components/RawJsonPanel';

const SAMPLE_TRANSCRIPT = `[00:00] Alex (PM): Hi team, welcome to the kickoff for our new project. Today we need to align on the core features, select our technology stack, and distribute the initial development tasks.
[00:20] Sarah (Frontend Dev): Hi everyone. For the client application, I'm proposing we use React + TypeScript built with Vite. It gives us an extremely fast dev loop, clean components, and strong typing which will help prevent frontend bugs.
[00:45] David (Backend Dev): I like that. For the API backend, I suggest Python using FastAPI. It's clean, automatically generates docs, and integrates perfectly with Pydantic for data validation. For storage, PostgreSQL is my recommendation for reliable relational data.
[01:15] Emma (Designer): That works for me. I've started putting together references for a glassmorphic dark-mode theme. I will have the high-fidelity Figma layouts for the dashboard finished by next Tuesday, June 30th.
[01:35] Alex (PM): Excellent. Let's agree on React + TypeScript for frontend, FastAPI + PostgreSQL for backend, and a glassmorphic dark UI.
[01:50] Alex (PM): For task assignments: Sarah, can you initialize the React boilerplate by Friday?
[02:05] Sarah (Frontend Dev): Yes, I will set up the repository and configure the styling configurations.
[02:15] Alex (PM): David, could you draft the initial database schema design by July 5th?
[02:30] David (Backend Dev): Sure, I can do that. I will write the schemas and database migrations.
[02:40] Alex (PM): Emma, you will deliver the Figma wireframes on June 30th. And I'll set up our Jira board and prepare the project roadmap slides for stakeholder review by tomorrow evening.
[03:00] Alex (PM): Let's sync up again next Wednesday. Thanks everyone, let's get building!`;

export default function App() {
  const [transcript, setTranscript] = useState('');
  const [template, setTemplate] = useState('general');
  const [status, setStatus] = useState<'idle' | 'analyzing' | 'completed'>('idle');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OrchestratorOutput | null>(null);

  const handleAnalyze = async () => {
    if (!transcript.trim()) return;
    
    setError(null);
    setStatus('analyzing');
    setResult(null);

    try {
      const data = await analyzeMeeting(transcript, template);
      setResult(data);
      setStatus('completed');
    } catch (err: any) {
      setError(err.message || 'An error occurred during analysis.');
      setStatus('idle');
    }
  };

  const handleLoadSample = () => {
    setTranscript(SAMPLE_TRANSCRIPT);
  };

  return (
    <div className="app-container">
      {/* App Header */}
      <header className="app-header">
        <div className="app-logo">
          <Mic size={28} />
        </div>
        <h1 className="app-title">EchoScribe AI</h1>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '8px' }}>
          Collaborative Agent Dashboard
        </span>
      </header>

      {/* Main Dashboard Layout */}
      <main className="dashboard-layout">
        {/* Left Side: Transcript Input Form */}
        <TranscriptInput
          value={transcript}
          onChange={setTranscript}
          template={template}
          onTemplateChange={setTemplate}
          onSubmit={handleAnalyze}
          isLoading={status === 'analyzing'}
          onLoadSample={handleLoadSample}
        />

        {/* Right Side: Agent Timelines and Output Panels */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Agent Timeline display at the top of results */}
          {status !== 'idle' && <AgentTimeline status={status} />}

          {status === 'idle' && !error && (
            <div className="glass-card" style={{ padding: '40px 24px', textAlign: 'center' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>🎙️</div>
              <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '10px' }}>Ready to Process</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '14.5px', maxWidth: '480px', margin: '0 auto' }}>
                Load the sample kickoff transcript or paste your meeting logs in the left panel, choose a template focus, and trigger the agent orchestrator.
              </p>
            </div>
          )}

          {error && (
            <div className="glass-card" style={{ borderColor: 'rgba(244, 63, 94, 0.3)', background: 'rgba(244, 63, 94, 0.03)' }}>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', color: 'var(--color-rose)' }}>
                <AlertTriangle size={24} />
                <h3 style={{ fontSize: '16px', fontWeight: 600 }}>Error executing orchestration pipeline</h3>
              </div>
              <p style={{ marginTop: '10px', fontSize: '14px', color: 'var(--text-secondary)' }}>{error}</p>
            </div>
          )}

          {status === 'analyzing' && (
            <div className="glass-card spinner-container">
              <div className="loading-spinner" />
              <div style={{ fontSize: '14.5px', fontWeight: 500, color: 'var(--text-secondary)' }}>
                Orchestrator Agent is running pipeline stages...
              </div>
            </div>
          )}

          {status === 'completed' && result && (
            <div className="results-grid">
              {/* Row 1: Summary & Decisions */}
              <SummaryCard
                title={result.meeting_notes.title}
                date={result.meeting_notes.date}
                summary={result.meeting_notes.summary}
                attendees={result.meeting_notes.attendees}
              />
              
              <DecisionsCard
                decisions={result.meeting_notes.decisions}
              />

              {/* Row 2: Action Items table (Full width) */}
              <ActionItemsTable
                actionItems={result.meeting_notes.action_items}
              />

              {/* Row 3: Ticket Cards (Full width) */}
              <TicketCards
                tickets={result.tickets_tool_output}
              />

              {/* Row 4: Calendar & Email cards */}
              <CalendarCard
                calendarOutput={result.calendar_event_tool_output}
              />

              <EmailDraftCard
                emailOutput={result.email_draft_tool_output}
              />

              {/* Row 5: Collapsible Raw JSON data */}
              <RawJsonPanel
                data={result}
              />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
