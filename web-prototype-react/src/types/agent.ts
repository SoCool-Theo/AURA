export type AgentExplainRequest = {
  portfolio_id: string;
  message: string;
  report_id?: string;
  simulation_id?: string;
};

export type AgentSourceReference = {
  type: 'portfolio' | 'report' | 'simulation';
  id: string;
};

export type AgentExplainResponse = {
  answer: string;
  sources: AgentSourceReference[];
  limitations: string[];
};
