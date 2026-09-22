interface LineChartProps {
  points: [number, number][];
  width?: number;
  height?: number;
  color?: string;
  unit?: string;
}

const PADDING = 4;

export function LineChart({ points, width = 320, height = 80, color = "#3fd9c7", unit }: LineChartProps) {
  if (points.length === 0) {
    return <div className="linechart linechart--empty">sin datos</div>;
  }
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;

  const toX = (x: number) => PADDING + ((x - minX) / spanX) * (width - PADDING * 2);
  const toY = (y: number) => height - PADDING - ((y - minY) / spanY) * (height - PADDING * 2);

  const path = points.map(([x, y]) => `${toX(x).toFixed(1)},${toY(y).toFixed(1)}`).join(" ");
  const last = points[points.length - 1][1];

  return (
    <div className="linechart">
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} preserveAspectRatio="none" role="img" aria-label="gráfico de línea">
        <polyline points={path} fill="none" stroke={color} strokeWidth="1.5" />
      </svg>
      <div className="linechart__last">
        último: {last.toFixed(1)}
        {unit ? ` ${unit}` : ""}
      </div>
    </div>
  );
}
