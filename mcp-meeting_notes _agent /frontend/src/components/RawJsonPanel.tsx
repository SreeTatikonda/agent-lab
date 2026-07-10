import React, { useState } from 'react';

interface RawJsonPanelProps {
  data: any;
}

export const RawJsonPanel: React.FC<RawJsonPanelProps> = ({ data }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="glass-card full-width">
      <div 
        className="collapsible-header" 
        onClick={() => setIsOpen(!isOpen)}
      >
        <span style={{ fontSize: '15px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
          📦 Raw JSON Pipeline Dataset
        </span>
        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          {isOpen ? 'Collapse ▲' : 'Expand ▼'}
        </span>
      </div>

      {isOpen && (
        <pre className="collapsible-content">
          <code>{JSON.stringify(data, null, 2)}</code>
        </pre>
      )}
    </div>
  );
};
