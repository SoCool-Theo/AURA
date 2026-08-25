import type { CSSProperties } from 'react';
import { clamp } from '../../utils/uiCalculations';

interface GaugeChartProps {
  score?: number;
  label?: string;
}

export function GaugeChart({ score = 65, label = 'Moderate' }: GaugeChartProps) {
  const degrees = clamp(score, 0, 100) * 1.8;
  const gaugeStyle = { '--score-deg': `${degrees}deg` } as CSSProperties;

  return (
    <div className="gauge-block">
      <div className="gauge" style={gaugeStyle}>
        <div className="gauge-inner">
          <strong>{score}</strong>
          <small>{label}</small>
        </div>
      </div>
    </div>
  );
}
