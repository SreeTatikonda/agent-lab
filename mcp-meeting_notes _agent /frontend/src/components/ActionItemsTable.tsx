import React from 'react';
import { ActionItem } from '../types';

interface ActionItemsTableProps {
  actionItems: ActionItem[];
}

export const ActionItemsTable: React.FC<ActionItemsTableProps> = ({ actionItems }) => {
  const getPriorityClass = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
      case 'critical':
        return 'priority-high';
      case 'medium':
        return 'priority-medium';
      default:
        return 'priority-low';
    }
  };

  const getPriorityLabel = (item: ActionItem) => {
    // Map deadline presence to priority if not explicitly set
    if (item.deadline) return 'High';
    return 'Medium';
  };

  return (
    <div className="glass-card full-width">
      <div className="glass-card-header">
        <span>📋 Action Items Checklist</span>
      </div>

      {actionItems.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '13.5px' }}>
          No action items assigned in this meeting.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="action-table">
            <thead>
              <tr>
                <th>Task</th>
                <th>Owner</th>
                <th>Deadline</th>
                <th>Priority</th>
              </tr>
            </thead>
            <tbody>
              {actionItems.map((item, idx) => {
                const priority = getPriorityLabel(item);
                return (
                  <tr key={idx}>
                    <td style={{ fontWeight: 500 }}>{item.text}</td>
                    <td>{item.assignee ? `👤 ${item.assignee}` : 'Unassigned'}</td>
                    <td>{item.deadline ? `📅 ${item.deadline}` : 'None'}</td>
                    <td>
                      <span className={`priority-badge ${getPriorityClass(priority)}`}>
                        {priority}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
