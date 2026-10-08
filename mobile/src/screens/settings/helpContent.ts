export type HelpArticle = { id: string; question: string; answer: string[] };
export type HelpSection = { id: string; title: string; articles: HelpArticle[] };

// Code-owned product guidance only; never fetch or calculate portfolio data here.
export const helpSections: HelpSection[] = [
  { id: 'getting-started', title: 'Getting started', articles: [
    { id: 'create-portfolio', question: 'How do I create my first portfolio?', answer: [
      'Open Portfolios and choose Create Portfolio. Add a name, choose Current or Planned, and select supported assets.',
      'For a Current Portfolio, enter the shares you actually own. For a Planned Portfolio, enter proposed investment amounts in the selected plan currency. Aura calculates the allocation on the backend; you do not enter portfolio weights manually.',
      'Save the portfolio, then open its analysis to choose a historical date range and run an analysis.',
    ] },
    { id: 'saved-reports', question: 'Where can I find my analysis and simulation results?', answer: [
      'Open Reports for saved portfolio analysis. On mobile, Reports is under More. Open a report to view the results, period, and saved context.',
      'Successful simulation runs are saved in simulation history. Open a saved simulation to revisit that exact result. Editing a portfolio does not rewrite earlier saved reports or simulation snapshots.',
    ] },
    { id: 'watchlist-learn', question: 'What are Watchlist and Learn for?', answer: [
      'Watchlist follows supported assets using saved market observations. Check the date shown for each asset; these prices are not live quotes.',
      'Learn explains portfolio-risk concepts with simple examples. After reading, tap Mark lesson completed. Opening a lesson or its YouTube link does not automatically complete it, and you can undo completion.',
    ] },
  ] },
  { id: 'portfolio-types', title: 'Portfolio types', articles: [
    { id: 'current-planned', question: 'What is the difference between Current and Planned Portfolios?', answer: [
      'A Current Portfolio records shares you own. Aura uses saved market prices to value those shares and derive the current allocation.',
      'A Planned Portfolio models proposed investment amounts in USD or THB. Its target allocation comes from those amounts. It is hypothetical: proposed amounts and estimated shares are not owned assets or orders.',
    ] },
    { id: 'allocation-estimates', question: 'Why do allocation and estimated shares behave differently?', answer: [
      'Current allocation can change as asset prices change, even if your share quantities stay the same. Planned target allocation is based on proposed amounts, not price movements.',
      'Estimated shares in a plan are optional previews using saved price and, when needed, exchange-rate context. Unavailable estimates do not mean your proposed amounts or target allocation were lost.',
    ] },
  ] },
  { id: 'analysis-simulations', title: 'Analysis & simulations', articles: [
    { id: 'risk-metrics', question: 'How should I read the risk metrics?', answer: [
      'Returns describe historical performance. Volatility describes how much returns varied, and maximum drawdown describes the largest historical peak-to-trough decline.',
      'Sharpe ratio summarizes return relative to variability under the analysis assumptions. Concentration and diversification describe how exposure is distributed. A risk score is a summary, not a guarantee or a buy/sell instruction.',
      'Read the analysis period, data coverage, and limitations alongside the metrics. Learn provides fuller explanations and examples.',
    ] },
    { id: 'simulation-types', question: 'Which simulation should I choose?', answer: [
      'Historical Scenario explores how an allocation behaved in a selected past event. Allocation Change compares an original allocation with a hypothetical modified allocation.',
      'Combined Simulation applies a hypothetical allocation change within a historical scenario. All three are educational what-if tools, not forecasts, trades, or edits to your saved portfolio.',
    ] },
    { id: 'original-comparison', question: 'What is the Original result in a simulation comparison?', answer: [
      'The comparison views use the portfolio’s latest saved analysis as the original reference when it is available. Review the reference report and dates shown, and use View latest portfolio analysis to open the details.',
      'This saved-analysis reference is distinct from the backend allocation used to run the simulation: current holdings use the resolved current allocation, while plans use their target allocation.',
      'A historical event and the saved analysis can cover different dates. Their comparison explains historical behavior across those periods, not a matched-period prediction. If a reference is unavailable, follow the message shown rather than assuming a zero result.',
    ] },
    { id: 'saved-simulation', question: 'Will saved simulations change, and can I delete one?', answer: [
      'A saved simulation freezes the successful run and its context. Opening it does not rerun the scenario or refresh its market prices. Create a new run to test different inputs.',
      'Delete Simulation removes the selected saved simulation after confirmation and cannot be undone. It does not delete the portfolio or its analysis reports. Check the selected result before confirming.',
    ] },
  ] },
  { id: 'ai-assistant', title: 'AI Assistant', articles: [
    { id: 'assistant-context', question: 'How do I choose what the Assistant explains?', answer: [
      'Select a portfolio in AI Assistant to discuss its allocation and newest saved analysis when available.',
      'To discuss a specific simulation, choose it from Saved simulations or open the Assistant from that saved result. The selected simulation is exact saved context; the newest portfolio analysis may also provide supporting context.',
      'Check the context label and sources shown before asking a question. Aura does not automatically analyze every past report or simulation in one conversation.',
    ] },
    { id: 'assistant-limits', question: 'What can the Assistant do, and why might the chat be hidden?', answer: [
      'The Assistant explains Aura’s backend-produced analysis and simulation results in plain language. It does not execute trades, predict prices, or provide personalized buy, sell, or hold recommendations.',
      'Hide portfolio values also shields AI questions, answers, context, and the input box. Turn the preference Off in Settings if you want to view or use the chat.',
    ] },
  ] },
  { id: 'privacy-local-data', title: 'Privacy & local data', articles: [
    { id: 'hide-values', question: 'What does Hide portfolio values hide?', answer: [
      'This local preference masks personal monetary amounts and share quantities, protects monetary/share editing fields, and hides AI chat. Percentages, risk scores, normalized charts, public market prices, and Learn examples remain visible.',
      'The choice is remembered for your account in this browser or on this device, including after sign out and sign in. It does not synchronize between web and mobile or other devices. It is screen privacy, not encryption or an account-security lock.',
    ] },
    { id: 'reset-local-data', question: 'What does Reset local data clear?', answer: [
      'After confirmation, Reset local data clears this account’s local Learn progress and turns Hide portfolio values Off. On mobile it also restores device appearance to Dark and removes obsolete demo storage. Account notification preferences and your notification inbox stay unchanged. App notifications controls updates inside Aura; phone push, browser push, email notifications, and price alerts are not enabled.',
      'It does not delete your account, portfolios, holdings, reports, simulations, or watchlist, and it does not sign you out. Other accounts’ local Learn progress and privacy choices remain unchanged.',
      'Reset is not account deletion. If a reset fails partway through, some preferences may already have reset; read the message and retry.',
    ] },
    { id: 'delete-account', question: 'How is deleting an account different from signing out or resetting local data?', answer: [
      'Sign out ends the local session without deleting saved account data. Reset local data changes only the local progress and preferences described above.',
      'Delete Account requires your current password and permanently deletes your Aura account and its owned portfolios, holdings, reports, simulations, and watchlist entries. Shared market data stays unchanged. This cannot be undone.',
    ] },
  ] },
  { id: 'troubleshooting', title: 'Troubleshooting', articles: [
    { id: 'connection-errors', question: 'What should I do if a page will not load or a request fails?', answer: [
      'Check your internet connection and use the page’s retry control. If the problem continues, close and reopen the app or reload the browser, then retry.',
      'If a create or run request timed out, check the saved portfolio or history before submitting again: the operation may have completed before the connection was lost.',
      'Reset local data does not repair a backend outage or refresh market data. Keep the error message and note which page and action failed.',
    ] },
    { id: 'missing-market-data', question: 'Why are market values, analysis, or planned share estimates unavailable?', answer: [
      'Current valuation needs usable saved market observations. Analysis and simulations also need enough aligned historical coverage for the requested dates. Missing, stale, or insufficient data can make results unavailable; Aura does not invent replacement prices.',
      'Check asset and price dates and the message shown. Retry if data becomes available, or use a different supported historical period when appropriate. Refreshing the page does not itself fetch new market prices into the backend.',
      'A plan can still retain its proposed amounts and target allocation when price or exchange-rate data is unavailable for optional share estimates.',
    ] },
    { id: 'sign-in-password', question: 'What should I do if I cannot sign in or change my password?', answer: [
      'Check your email address and password, then read the displayed error before retrying. Changing your password requires the current password and a valid new password.',
      'If your session has expired, sign in again. Password recovery is not offered in this guide, and there is no support reset form here. Never share your password or authentication tokens.',
    ] },
    { id: 'progress-storage', question: 'Why did my Learn progress or privacy preference not save?', answer: [
      'These choices are stored locally per account, not on the backend. Another device or browser starts with its own local settings. Clearing browser/app storage can remove saved choices, and private browsing may not keep them after it closes.',
      'If Aura reports a storage error, use Retry local progress or try saving the privacy preference again. A blocked or full local store can prevent persistence. A failed lesson save is not counted as successful completion.',
      'Use Reset local data only if you intend to clear local progress and reset privacy Off. Older mobile progress without an account identifier is not assigned to an account because its ownership is unknown.',
    ] },
  ] },
  { id: 'support-safety', title: 'Support & safety', articles: [
    { id: 'contact-support', question: 'Can I send a support request from Aura?', answer: [
      'In-app support messaging, live chat, and a published support contact are not available yet. This page is a self-service guide; it does not send a ticket or contact request.',
      'Use the troubleshooting guidance above. A real support channel can be added here when it is available.',
    ] },
    { id: 'safe-details', question: 'What information is useful when reporting an issue safely?', answer: [
      'Note whether you are using web or mobile, the browser or phone platform, the page and action, the approximate time, and the exact error message. A screenshot and short steps to reproduce can help.',
      'Redact balances, holdings, email addresses, and any other personal information from screenshots. Never include passwords, authentication tokens, credentials, or private financial documents.',
    ] },
  ] },
];

export function filterHelpSections(query: string): HelpSection[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return helpSections;
  return helpSections.map(section => ({
    ...section,
    articles: section.articles.filter(article =>
      [section.title, article.question, ...article.answer].join(' ').toLowerCase().includes(normalized)),
  })).filter(section => section.articles.length > 0);
}
