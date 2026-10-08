import type { ScenarioOption } from '../types/simulation';

export const scenarioOptions: ScenarioOption[] = [
  { id: 'gfc', label: '2008 Financial Crisis', dates: 'Oct 1, 2007 – Mar 2009', returnPct: -37.42, drawdown: -45.61, volatility: 28.73, recovery: 16 },
  { id: 'covid', label: '2020 COVID Crash', dates: 'Feb 19, 2020 – Mar 23, 2020', returnPct: -22.65, drawdown: -30.18, volatility: 42.15, recovery: 5 },
  { id: 'dotcom', label: 'Dot-com Bust', dates: 'Mar 2000 – Oct 2002', returnPct: -41.25, drawdown: -48.34, volatility: 31.08, recovery: 31 },
  { id: 'growth', label: '2016–2019 Growth Period', dates: 'Jan 2016 – Dec 2019', returnPct: 44.2, drawdown: -13.8, volatility: 15.4, recovery: 3 },
];
