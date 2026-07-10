import React from 'react';

interface TranscriptInputProps {
  value: string;
  onChange: (val: string) => void;
  template: string;
  onTemplateChange: (val: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
  onLoadSample: () => void;
}

export const TranscriptInput: React.FC<TranscriptInputProps> = ({
  value,
  onChange,
  template,
  onTemplateChange,
  onSubmit,
  isLoading,
  onLoadSample,
}) => {
  return (
    <div className="glass-card">
      <div className="glass-card-header">
        <span>🎙️ Meeting Transcript Input</span>
      </div>

      <div className="form-group" style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '12px' }}>
        <button 
          className="btn-secondary" 
          onClick={onLoadSample}
          disabled={isLoading}
          style={{ fontSize: '12px', padding: '6px 12px' }}
        >
          Load Kickoff Sample
        </button>
      </div>

      <div className="form-group">
        <label className="form-label">Raw Transcript Text</label>
        <textarea
          className="form-textarea"
          placeholder="Paste meeting transcript here... E.g.:&#10;[00:00] Alex: Hi team.&#10;[00:15] Sarah: Hello."
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={isLoading}
        />
      </div>

      <div className="form-group">
        <label className="form-label">Analysis Template Focus</label>
        <select
          className="form-select"
          value={template}
          onChange={(e) => onTemplateChange(e.target.value)}
          disabled={isLoading}
        >
          <option value="general">General Meeting (Roadmaps & Details)</option>
          <option value="standup">Standup (Updates & Immediate Tasks)</option>
          <option value="brainstorm">Brainstorming (Architecture & Ideas)</option>
          <option value="demo">Sales Demo (Client feedback & Objections)</option>
        </select>
      </div>

      <button
        className="btn-primary"
        onClick={onSubmit}
        disabled={isLoading || !value.trim()}
      >
        {isLoading ? 'Running Agents...' : 'Analyze Meeting'}
      </button>
    </div>
  );
};
