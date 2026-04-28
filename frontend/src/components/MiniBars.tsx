export function MiniBars(props: { values: number[] }) {
  const { values } = props;
  if (!values.length) {
    return <div className="chart-empty">暂无图表数据</div>;
  }

  const max = Math.max(...values) || 1;

  return (
    <div className="mini-bars">
      {values.map((value, index) => (
        <div key={`${value}-${index}`} className="mini-bar-col">
          <div className="mini-bar-track">
            <div className="mini-bar-fill" style={{ height: `${Math.max((value / max) * 100, 8)}%` }} />
          </div>
          <span>{index + 1}</span>
        </div>
      ))}
    </div>
  );
}
