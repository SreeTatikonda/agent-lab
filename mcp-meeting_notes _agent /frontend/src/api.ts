import { OrchestratorOutput } from './types';

const API_BASE_URL = 'http://localhost:8000';

export async function analyzeMeeting(transcript: string, template: string): Promise<OrchestratorOutput> {
  const response = await fetch(`${API_BASE_URL}/api/meeting/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ transcript, template }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorDetail = 'Failed to analyze meeting';
    try {
      const parsed = JSON.parse(errorText);
      errorDetail = parsed.detail || errorDetail;
    } catch {
      errorDetail = errorText || errorDetail;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}
