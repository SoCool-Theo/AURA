// Daily prices: low-frequency reads only, with no hidden-tab polling.
export function watchMarketDataForeground(refresh: () => void, activity: (active: boolean) => void) {
  let interval: ReturnType<typeof setInterval> | undefined;
  let active = document.visibilityState === 'visible';
  const start = () => { interval = setInterval(refresh, 300000); };
  const change = () => {
    const next = document.visibilityState === 'visible';
    if (next === active) return;
    active = next; activity(active);
    if (active) { start(); refresh(); }
    else { clearInterval(interval); interval = undefined; }
  };
  const focus = () => { if (active) refresh(); };
  activity(active);
  if (active) start();
  document.addEventListener('visibilitychange', change);
  window.addEventListener('focus', focus);
  return () => { clearInterval(interval); document.removeEventListener('visibilitychange', change); window.removeEventListener('focus', focus); };
}
