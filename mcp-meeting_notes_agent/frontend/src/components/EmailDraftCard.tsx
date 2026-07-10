import React, { useState } from 'react';

interface EmailDraftCardProps {
  emailOutput: {
    status: string;
    message: string;
    draft_id?: string;
    data: {
      to: string;
      subject: string;
      body: string;
      created_at?: string;
    };
  };
}

export const EmailDraftCard: React.FC<EmailDraftCardProps> = ({ emailOutput }) => {
  const [copied, setCopied] = useState(false);
  
  const data = emailOutput.data;
  const isSkipped = emailOutput.status === 'skipped';

  const copyToClipboard = () => {
    navigator.clipboard.writeText(data.body);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-card">
      <div className="glass-card-header" style={{ justifyContent: 'space-between' }}>
        <span>✉️ Email Follow-up Draft</span>
        {!isSkipped && (
          <button className="btn-secondary" onClick={copyToClipboard} style={{ fontSize: '11px', padding: '4px 8px' }}>
            {copied ? 'Copied!' : 'Copy Body'}
          </button>
        )}
      </div>

      {isSkipped ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ color: 'var(--color-rose)', fontWeight: 600, fontSize: '14px' }}>
            ⚠️ STATUS: SKIPPED
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
            {emailOutput.message}
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ color: 'var(--color-emerald)', fontWeight: 600, fontSize: '14px' }}>
            ✅ STATUS: CREATED DRAFT
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
            <strong>To:</strong> <code>{data.to}</code> <br/>
            <strong>Subject:</strong> <code>{data.subject}</code>
          </div>
          <textarea
            className="email-textarea"
            readOnly
            value={data.body}
          />
        </div>
      )}
    </div>
  );
};
