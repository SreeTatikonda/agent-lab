import React from 'react';

interface CalendarCardProps {
  calendarOutput: {
    status: string;
    message: string;
    event_id?: string;
    data: {
      title: string;
      attendees: string[];
      date: string;
      description: string;
      scheduled_at?: string;
    };
  } | null;
}

export const CalendarCard: React.FC<CalendarCardProps> = ({ calendarOutput }) => {
  if (!calendarOutput) {
    return (
      <div className="glass-card">
        <div className="glass-card-header">
          <span>📅 Calendar Follow-up</span>
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '13.5px' }}>
          No follow-up calendar event scheduled.
        </div>
      </div>
    );
  }

  const data = calendarOutput.data;
  const isSkipped = calendarOutput.status === 'skipped';

  return (
    <div className="glass-card">
      <div className="glass-card-header">
        <span>📅 Calendar Follow-up</span>
      </div>

      {isSkipped ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ color: 'var(--color-rose)', fontWeight: 600, fontSize: '14px' }}>
            ⚠️ STATUS: SKIPPED
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
            {calendarOutput.message}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
            <strong>Proposed Title:</strong> {data.title} <br/>
            <strong>Proposed Date:</strong> {data.date}
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ color: 'var(--color-emerald)', fontWeight: 600, fontSize: '14px' }}>
            ✅ STATUS: SCHEDULED
          </div>
          <div style={{ fontSize: '13.5px', fontWeight: 600 }}>
            {data.title}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            {data.description}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px' }}>
            <strong>Date:</strong> {data.date} <br/>
            <strong>Event ID:</strong> <code>{calendarOutput.event_id}</code> <br/>
            <strong>Attendees:</strong> {data.attendees.join(', ')}
          </div>
        </div>
      )}
    </div>
  );
};
