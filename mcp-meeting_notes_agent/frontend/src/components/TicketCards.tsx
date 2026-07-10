import React from 'react';

interface TicketCardsProps {
  tickets: Array<{
    status: string;
    message: string;
    ticket_id?: string;
    data: {
      title: string;
      owner: string;
      deadline: string;
      priority: string;
      created_at?: string;
    };
  }>;
}

export const TicketCards: React.FC<TicketCardsProps> = ({ tickets }) => {
  return (
    <div className="glass-card full-width">
      <div className="glass-card-header">
        <span>🎫 Synthesized Jira & GitHub Tickets</span>
      </div>

      {tickets.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '13.5px' }}>
          No project management tickets were generated.
        </div>
      ) : (
        <div className="ticket-list">
          {tickets.map((ticket, idx) => {
            const data = ticket.data;
            const status = ticket.status.toUpperCase();
            
            return (
              <div key={idx} className="ticket-card">
                <div className="ticket-header">
                  <span className="ticket-id">{ticket.ticket_id || `TKT-${100 + idx}`}</span>
                  <span className="ticket-platform" style={{
                    color: status === 'SUCCESS' ? 'var(--color-emerald)' : 'var(--color-amber)',
                    fontSize: '10px'
                  }}>
                    {status}
                  </span>
                </div>
                <div className="ticket-title">{data.title}</div>
                <div className="ticket-desc" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  Task Owner: **{data.owner}** <br/>
                  Target Deadline: **{data.deadline}** <br/>
                  Priority Rating: **{data.priority}**
                </div>
                <div className="ticket-meta">
                  <span>Status: {ticket.message}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
