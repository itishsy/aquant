export function LineChart(props: {
  values: number[];
  stroke?: string;
  height?: number;
  fill?: boolean;
}) {
  const { values, stroke = "#4b63ee", height = 140, fill = true } = props;
  if (!values.length) {
    return <div className="chart-empty">暂无图表数据</div>;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 320;

  const points = values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * width;
      const y = height - ((value - min) / range) * (height - 18) - 9;
      return `${x},${y}`;
    })
    .join(" ");

  const area = `0,${height} ${points} ${width},${height}`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="line-chart" preserveAspectRatio="none">
      {fill ? <polygon points={area} className="line-chart-fill" /> : null}
      <polyline points={points} fill="none" stroke={stroke} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
