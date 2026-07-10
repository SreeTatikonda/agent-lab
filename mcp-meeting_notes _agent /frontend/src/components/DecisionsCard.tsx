import React from 'react';

interface DecisionsCardProps {
  decisions: string[];
}

export const DecisionsCard: React.FC<DecisionsCardProps> = ({ decisions }) => {
  return (
    <div className="glass-card">
      <div className="glass-card-header">
        <span>💡 Key Decisions</span>
      </div>

      <div className="decisions-container">
        {decisions.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13.5px' }}>
            No key decisions were explicitly recorded in this meeting.
          </div>
        ) : (
          decisions.map((decision, idx) => (
            <div key={idx} className="decision-item">
              <span>⚡</span>
              <span>{decision}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
