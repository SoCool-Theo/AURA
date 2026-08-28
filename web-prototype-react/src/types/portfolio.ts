export type Holding = {
  symbol: string;
  name: string;
  type: string;
  weight: number;
  value: number;
  dailyChange: number;
  price: number;
  shares: number;
};

export type Portfolio = {
  id: string;
  name: string;
  created: string;
  value: number;
  totalReturn: number;
  annualizedReturn?: number;
  riskScore: number;
  riskLevel: string;
  cash: number;
  holdings: Holding[];
};
