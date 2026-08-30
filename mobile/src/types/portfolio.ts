export type Holding = {
  symbol: string;
  name: string;
  weight: number;
  value: number;
  risk: 'Low' | 'Medium' | 'High';
};

export type Portfolio = {
  id: string;
  name: string;
  totalValue: number;
  riskScore: number;
  riskLevel: 'Low' | 'Moderate' | 'High';
  annualizedReturn: number;
  maxDrawdown: number;
  holdings: Holding[];
};
