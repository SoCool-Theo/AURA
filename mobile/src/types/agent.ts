import type { Uuid } from './api';

export type AgentConversationMessage = {
  role: 'user' | 'assistant';
  content: string;
};

export type AgentExplainRequest = {
  portfolio_id: Uuid;
  message: string;
  report_id?: Uuid;
  simulation_id?: Uuid;
  history?: AgentConversationMessage[];
};

export type AgentSourceReference = {
  type: 'portfolio' | 'report' | 'simulation';
  id: Uuid;
};

export type AgentExplainResponse = {
  answer: string;
  sources: AgentSourceReference[];
  limitations: string[];
};
