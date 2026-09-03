import type { NavigatorScreenParams } from '@react-navigation/native';

export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
};

export type PortfolioStackParamList = {
  Portfolios: undefined;
  PortfolioDetail: { portfolioId: string };
  CreatePortfolio: undefined;
  AddAsset: { portfolioId: string };
  EditHoldings: { portfolioId: string };
  PortfolioAnalysis: { portfolioId?: string };
  ReportDetail: { portfolioId: string; reportId: string };
};

export type SimulationStackParamList = {
  Simulations: undefined;
  HistoricalScenario: { portfolioId?: string };
  AllocationChange: { portfolioId?: string };
  CombinedSimulation: { portfolioId?: string };
  SimulationResult: { simulationId: string };
  SimulationHistory: undefined;
};

export type MoreStackParamList = {
  More: undefined;
  Analytics: { portfolioId?: string };
  Reports: undefined;
  ReportDetail: { portfolioId: string; reportId: string };
  Watchlist: undefined;
  Learn: undefined;
  LearnDetail: { lessonId: string };
  Settings: undefined;
};

export type MainTabParamList = {
  Home: undefined;
  Portfolio: NavigatorScreenParams<PortfolioStackParamList>;
  Simulate: NavigatorScreenParams<SimulationStackParamList>;
  AI: undefined;
  MoreTab: NavigatorScreenParams<MoreStackParamList>;
};

export type RootStackParamList = {
  Onboarding: undefined;
  Auth: NavigatorScreenParams<AuthStackParamList>;
  Main: NavigatorScreenParams<MainTabParamList>;
};
