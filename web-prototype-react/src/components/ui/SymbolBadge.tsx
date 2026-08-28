interface SymbolBadgeProps {
  symbol: string;
}

export function SymbolBadge({ symbol }: SymbolBadgeProps) {
  const symbolClass = symbol.replace(/[^a-zA-Z]/g, '').slice(0, 3).toLowerCase();

  return <span className={`symbol-badge s-${symbolClass}`}>{symbol.slice(0, 4)}</span>;
}
