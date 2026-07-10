import React from 'react';

interface SummaryCardProps {
  title: string;
  date: string;
  summary: string;
  attendees: string[];
}

export const SummaryCard: React.FC<SummaryCardProps> = ({
  title,
  date,
  summary,
  attendees,
}) => {
  return (
    <div className="glass-card">
      <div className="glass-card-header">
        <span>📝 Meeting Summary</span>
      </div>
      
      <div style={{ marginBottom: '16px' }}>
        <h3 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)' }}>{title}</h3>
        <span style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>
          Date: {date ? new Date(date).toLocaleDateString() : 'N/A'}
        </span>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h4 style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '6px' }}>Executive Summary</h4>
        <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-primary)' }}>{summary}</p>
      </div>

      <div>
        <h4 style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '8px' }}>Attendees</h4>
        <div className="attendees-container">
          {attendees.map((att, idx) => (
            <span key={idx} className="attendee-tag">👤 {att}</span>
          ))}
        </div>
      </div>
    </div>
  );
};
