interface DonutHolding {
  symbol: string;
  weight: number;
}

interface DonutChartProps {
  holdings: DonutHolding[];
}

const DONUT_COLORS = ['#5844E5', '#1160F8', '#11B89D', '#F2A121', '#A855F7', '#3B82F6'];

export function DonutChart({ holdings }: DonutChartProps) {
  let offset = 0;
  const circles = holdings.slice(0, 6).map((holding, index) => {
    const dash = `${holding.weight} ${100 - holding.weight}`;
    const circle = (
      <circle
        key={holding.symbol}
        cx="50"
        cy="50"
        r="34"
        fill="none"
        stroke={DONUT_COLORS[index % DONUT_COLORS.length]}
        strokeWidth="15"
        strokeDasharray={dash}
        strokeDashoffset={-offset}
        pathLength="100"
      />
    );
    offset += holding.weight;
    return circle;
  });

  return (
    <svg className="donut" viewBox="0 0 100 100" transform="rotate(-90)">
      {circles}
      <circle cx="50" cy="50" r="24" fill="var(--bg-card)" />
    </svg>
  );
}
