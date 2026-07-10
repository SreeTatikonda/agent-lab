export interface ActionItem {
  text: string;
  assignee: string | null;
  deadline: string | null;
  status: string;
}

export interface TranscriptSegment {
  speaker: string;
  text: string;
  timestamp: number;
}

export interface MeetingNotes {
  title: string;
  date: string;
  summary: string;
  template: string;
  attendees: string[];
  decisions: string[];
  action_items: ActionItem[];
  transcript: TranscriptSegment[];
}

export interface OrchestratorOutput {
  meeting_notes: MeetingNotes;
  email_draft_tool_output: {
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
  calendar_event_tool_output: {
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
  tickets_tool_output: Array<{
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
