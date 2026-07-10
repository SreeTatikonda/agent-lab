import React from 'react';

interface AgentTimelineProps {
  status: 'idle' | 'analyzing' | 'completed';
}

export const AgentTimeline: React.FC<AgentTimelineProps> = ({ status }) => {
  const steps = [
    { name: 'Orchestrator Agent', key: 'orchestrator', desc: 'Coordinates pipeline' },
    { name: 'Extraction Agent', key: 'extraction', desc: 'Analyzes transcript' },
    { name: 'Ticket Agent', key: 'tickets', desc: 'Creates PM tickets' },
    { name: 'Calendar Agent', key: 'calendar', desc: 'Schedules review sync' },
    { name: 'Email Agent', key: 'email', desc: 'Drafts follow-up email' }
  ];

  const getStepState = (idx: number) => {
    if (status === 'idle') return 'idle';
    if (status === 'completed') return 'done';
    
    // During 'analyzing', make orchestrator/extraction active, others waiting
    if (idx <= 1) return 'active';
    return 'idle';
  };

  return (
    <div className="glass-card full-width" style={{ padding: '16px 24px' }}>
      <div className="timeline-container">
        <div className="timeline-line" />
        {steps.map((step, idx) => {
          const stepState = getStepState(idx);
          return (
            <div 
              key={step.key} 
              className={`timeline-step ${stepState === 'active' ? 'active' : ''} ${stepState === 'done' ? 'done' : ''}`}
            >
              <div className="timeline-node">
                {stepState === 'done' ? '✓' : idx + 1}
              </div>
              <div className="timeline-label">{step.name}</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', textAlign: 'center' }}>{step.desc}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
