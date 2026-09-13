import type { SVGProps } from 'react';

type IconProps = {
  name: string;
  size?: number;
};

export function Icon({ name, size = 20 }: IconProps) {
  const common: SVGProps<SVGSVGElement> = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
  };

  switch (name) {
    case 'dashboard': return <svg {...common}><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5M9 21v-7h6v7"/></svg>;
    case 'portfolios': return <svg {...common}><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h5"/></svg>;
    case 'analytics': return <svg {...common}><path d="m12 3 9 9-9 9-9-9 9-9Z"/><circle cx="12" cy="12" r="3"/></svg>;
    case 'simulations': return <svg {...common}><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16M15 4v16"/></svg>;
    case 'assistant': return <svg {...common}><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3"/></svg>;
    case 'reports': return <svg {...common}><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h8"/></svg>;
    case 'search': return <svg {...common}><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>;
    case 'bell': return <svg {...common}><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg>;
    case 'chevron-down': return <svg {...common}><path d="m7 9.5 5 5 5-5"/></svg>;
    case 'wallet': return <svg {...common}><path d="M4 7h16v12H4zM7 7V4h9v3M16 12h4"/></svg>;
    case 'calendar': return <svg {...common}><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/></svg>;
    case 'trend': return <svg {...common}><path d="m3 17 6-6 4 4 8-9"/><path d="M15 6h6v6"/></svg>;
    case 'shield': return <svg {...common}><path d="M12 3 4.5 6v5c0 5 3.2 8.3 7.5 10 4.3-1.7 7.5-5 7.5-10V6L12 3Z"/><path d="m9 12 2 2 4-5"/></svg>;
    case 'drawdown': return <svg {...common}><path d="m3 7 6 6 4-4 8 8"/><path d="M15 17h6v-6"/></svg>;
    case 'spark': return <svg {...common}><path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z"/></svg>;
    case 'analysis': return <svg {...common}><circle cx="12" cy="12" r="7"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/><circle cx="12" cy="12" r="2"/></svg>;
    case 'offline': return <svg {...common}><path d="M4.5 9.5A6.5 6.5 0 0 1 15 5l1.5 2A4.5 4.5 0 0 1 19 15H8"/><path d="m3 3 18 18"/></svg>;
    case 'lock': return <svg {...common}><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/></svg>;
    case 'alert': return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 17h.01"/></svg>;
    case 'server': return <svg {...common}><rect x="4" y="4" width="16" height="6" rx="2"/><rect x="4" y="14" width="16" height="6" rx="2"/><path d="M8 7h.01M8 17h.01"/></svg>;
    default: return null;
  }
}
