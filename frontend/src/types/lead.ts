/**
 * Shared types mirroring the backend API shapes.
 */

export type LeadState = 'PENDING' | 'REACHED_OUT';

export interface LeadSummary {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  state: LeadState;
  created_at: string;
}

export interface Lead extends LeadSummary {
  resume_filename: string;
  updated_at: string;
}

export interface ApiError {
  detail: string;
  code?: string;
}
