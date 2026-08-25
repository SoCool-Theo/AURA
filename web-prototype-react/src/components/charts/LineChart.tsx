import { lineA } from '../../mocks/dashboard.mock';

interface LineChartProps {
  primary?: number[];
  secondary?: number[];
  labels?: string[];
  height?: number;
  negative?: boolean;
  area?: boolean;
}

export function LineChart({
  primary = lineA,
  secondary,
  labels = ['Jan 21', 'Nov 21', 'Sep 22', 'Jul 23', 'May 24', 'May 26'],
  height = 210,
  negative = false,
  area = false,
}: LineChartProps) {
  const all = secondary ? [...primary, ...secondary] : primary;
  const min = Math.min(...all, negative ? -50 : 0);
  const max = Math.max(...all, 10);
  const normalized = (values: number[]) => values.map((value, index) => {
    const x = 14 + (index / Math.max(1, values.length - 1)) * 672;
    const y = 14 + ((max - value) / (max - min || 1)) * (height - 42);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 700 ${height}`} className="line-chart" preserveAspectRatio="none">
        {area && (
          <defs>
            <linearGradient id="performance-area" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#765CFF" stopOpacity=".34" />
              <stop offset="100%" stopColor="#765CFF" stopOpacity=".02" />
            </linearGradient>
          </defs>
        )}
        {[0.25, 0.5, 0.75].map(position => (
          <line
            key={position}
            x1="14"
            y1={height * position}
            x2="686"
            y2={height * position}
            className="grid-line"
          />
        ))}
        {negative && (
          <line
            x1="14"
            y1={14 + (max / (max - min)) * (height - 42)}
            x2="686"
            y2={14 + (max / (max - min)) * (height - 42)}
            className="zero-line"
          />
        )}
        {area && (
          <polygon
            points={`14,${height - 28} ${normalized(primary)} 686,${height - 28}`}
            fill="url(#performance-area)"
          />
        )}
        {secondary && (
          <polyline
            points={normalized(secondary)}
            fill="none"
            className="secondary-line"
            strokeWidth="2.2"
            vectorEffect="non-scaling-stroke"
          />
        )}
        <polyline
          points={normalized(primary)}
          fill="none"
          className="primary-line"
          strokeWidth="3"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <div className="chart-labels">
        {labels.map(label => <span key={label}>{label}</span>)}
      </div>
    </div>
  );
}
