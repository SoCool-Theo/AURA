export type ScenarioDefinition = {
  id: string;
  name: string;
  period: string;
  baseImpact: number;
  description: string;
};

export const scenarioCatalog: ScenarioDefinition[] = [
  {
    id: 'covid-19-shock-2020',
    name: 'COVID-19 Market Shock',
    period: 'Feb 2020 – Apr 2020',
    baseImpact: -23,
    description: 'A rapid global selloff followed by a sharp rebound.'
  },
  {
    id: 'inflation-rate-shock-2022',
    name: '2022 Inflation and Rate Shock',
    period: 'Jan 2022 – Dec 2022',
    baseImpact: -15,
    description: 'Rising inflation and interest rates pressured stocks and bonds.'
  },
  {
    id: 'dot-com-bust-2000-2002',
    name: 'Dot-Com Bust',
    period: 'Mar 2000 – Oct 2002',
    baseImpact: -31,
    description: 'Technology-heavy portfolios experienced a prolonged drawdown.'
  },
  {
    id: 'global-financial-crisis-2007-2009',
    name: 'Global Financial Crisis',
    period: 'Oct 2007 – Mar 2009',
    baseImpact: -36,
    description: 'A severe global financial crisis with broad market losses.'
  },
  {
    id: 'q4-market-selloff-2018',
    name: 'Q4 2018 Market Selloff',
    period: 'Oct 2018 – Dec 2018',
    baseImpact: -13,
    description: 'A fast risk-off selloff across major equity markets.'
  }
];
