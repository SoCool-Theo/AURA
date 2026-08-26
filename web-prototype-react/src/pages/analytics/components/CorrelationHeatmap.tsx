import { Fragment } from 'react';
import type { CSSProperties } from 'react';
import { correlation } from '../../../mocks/analytics.mock';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

const HEATMAP_LABELS = ['NVDA', 'TSLA', 'AAPL', 'BND', 'GLD'];

function Heatmap() {
  return (
    <div className="heatmap ">
      <div className="heat-empty" />
      {HEATMAP_LABELS.map(label => <b key={label}>{label}</b>)}
      {HEATMAP_LABELS.map((row, rowIndex) => (
        <Fragment key={row}>
          <b>{row}</b>
          {correlation[rowIndex].map((value, columnIndex) => (
            <span
              key={`${rowIndex}-${columnIndex}`}
              style={{ '--heat': Math.abs(value) } as CSSProperties}
              className={value < 0 ? 'negative' : ''}
            >
              {value.toFixed(2)}
            </span>
          ))}
        </Fragment>
      ))}
    </div>
  );
}

export function CorrelationHeatmap() {
  return (
    <Card className="correlation-card">
      <div className="analytics-card-heading">
        <div><h2>Asset Relationships</h2><p>Historical return correlation</p></div>
        <span className="correlation-scale"><i /> Lower <i /> Higher</span>
      </div>
      <Heatmap />
      <div className="correlation-note">
        <Icon name="analysis" size={17} />
        <p>Higher positive values mean assets historically moved together. Lower or negative relationships may improve diversification.</p>
      </div>
    </Card>
  );
}
