interface RiskPillProps {
  score: number;
}

export function RiskPill({ score }: RiskPillProps) {
  const level = score >= 70 ? 'high' : score >= 55 ? 'moderate' : 'low';

  return (
    <span className={`pill ${level}`}>
      {score} · {level === 'high' ? 'High' : level === 'moderate' ? 'Moderate' : 'Low'}
    </span>
  );
}
