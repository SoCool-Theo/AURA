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
    case 'portfolios':
    case 'pie-chart': return <svg {...common}><path d="M11 3a9 9 0 1 0 9 9h-9V3Z"/><path d="M14 3.6A8.5 8.5 0 0 1 20.4 10H14V3.6Z"/></svg>;
    case 'analytics': return <svg {...common}><path d="M4 19V10M10 19V5M16 19v-7M22 19V8"/></svg>;
    case 'simulations':
    case 'pulse': return <svg {...common}><path d="M3 12h4l2.5-6 4.5 12 2.5-6H21"/></svg>;
    case 'assistant':
    case 'sparkles': return <svg {...common}><path d="m12 2 1.6 5.4L19 9l-5.4 1.6L12 16l-1.6-5.4L5 9l5.4-1.6L12 2Z"/><path d="m19 15 .7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7L19 15Z"/><path d="m4.5 3 .6 1.9L7 5.5l-1.9.6L4.5 8l-.6-1.9L2 5.5l1.9-.6L4.5 3Z"/></svg>;
    case 'reports': return <svg {...common}><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h8"/></svg>;
    case 'search': return <svg {...common}><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>;
    case 'bell': return <svg {...common}><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg>;
    case 'chevron-down': return <svg {...common}><path d="m7 9.5 5 5 5-5"/></svg>;
    case 'chevron-up': return <svg {...common}><path d="m7 14.5 5-5 5 5"/></svg>;
    case 'chevron-right': return <svg {...common}><path d="m9.5 7 5 5-5 5"/></svg>;
    case 'wallet': return <svg {...common}><path d="M4 7h16v12H4zM7 7V4h9v3M16 12h4"/></svg>;
    case 'calendar': return <svg {...common}><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/></svg>;
    case 'trend': return <svg {...common}><path d="m3 17 6-6 4 4 8-9"/><path d="M15 6h6v6"/></svg>;
    case 'shield': return <svg {...common}><path d="M12 3 4.5 6v5c0 5 3.2 8.3 7.5 10 4.3-1.7 7.5-5 7.5-10V6L12 3Z"/><path d="m9 12 2 2 4-5"/></svg>;
    case 'drawdown': return <svg {...common}><path d="m3 7 6 6 4-4 8 8"/><path d="M15 17h6v-6"/></svg>;
    case 'speedometer': return <svg {...common}><path d="M4.2 18a9 9 0 1 1 15.6 0"/><path d="m12 14 4-5"/><circle cx="12" cy="14" r="1.5"/><path d="M6.5 15H5M19 15h-1.5M8 9.5 7 8.5M16 9.5l1-1"/></svg>;
    case 'stats-chart': return <svg {...common}><path d="M4 20V10M10 20V4M16 20v-7M22 20V7"/><path d="M2 20h20"/></svg>;
    case 'diversification': return <svg {...common}><circle cx="12" cy="5" r="2"/><circle cx="5" cy="18" r="2"/><circle cx="19" cy="18" r="2"/><path d="m11 7-5 9M13 7l5 9M7 18h10"/></svg>;
    case 'assets': return <svg {...common}><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></svg>;
    case 'time': return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>;
    case 'compare': return <svg {...common}><path d="M7 7h11l-3-3M18 17H7l3 3"/><path d="m18 7-3 3M7 17l3-3"/></svg>;
    case 'eye': return <svg {...common}><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.5"/></svg>;
    case 'school': return <svg {...common}><path d="m3 9 9-5 9 5-9 5-9-5Z"/><path d="M7 12v4c3 2 7 2 10 0v-4M21 9v6"/></svg>;
    case 'settings': return <svg {...common}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/></svg>;
    case 'spark': return <svg {...common}><path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z"/></svg>;
    case 'analysis': return <svg {...common}><circle cx="12" cy="12" r="7"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/><circle cx="12" cy="12" r="2"/></svg>;
    case 'offline': return <svg {...common}><path d="M4.5 9.5A6.5 6.5 0 0 1 15 5l1.5 2A4.5 4.5 0 0 1 19 15H8"/><path d="m3 3 18 18"/></svg>;
    case 'lock': return <svg {...common}><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/></svg>;
    case 'alert': return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 17h.01"/></svg>;
    case 'server': return <svg {...common}><rect x="4" y="4" width="16" height="6" rx="2"/><rect x="4" y="14" width="16" height="6" rx="2"/><path d="M8 7h.01M8 17h.01"/></svg>;
    case 'trash': return <svg {...common}><path d="M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6M14 11v6"/></svg>;
    case 'close': return <svg {...common}><path d="m6 6 12 12M18 6 6 18"/></svg>;
    case 'logout': return <svg {...common}><path d="M10 4H4v16h6M10 12h11m-4-4 4 4-4 4"/></svg>;
    default: return null;
  }
}
