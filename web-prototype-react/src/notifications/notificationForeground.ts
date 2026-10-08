// Only poll while the browser page is visible; focus/return refresh immediately.
export function watchNotificationForeground(refresh: () => void) {
  const visibleRefresh = () => { if (document.visibilityState === 'visible') refresh(); };
  const interval = window.setInterval(visibleRefresh, 30000);
  window.addEventListener('focus', visibleRefresh);
  document.addEventListener('visibilitychange', visibleRefresh);
  return () => { window.clearInterval(interval); window.removeEventListener('focus', visibleRefresh); document.removeEventListener('visibilitychange', visibleRefresh); };
}
