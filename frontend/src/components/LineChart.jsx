export default function LineChart({
  participants = [30, 38, 45, 50, 55, 62, 70, 80, 88, 95, 105, 118, 130, 145],
  submissions = [0, 2, 4, 5, 8, 10, 14, 18, 22, 26, 30, 35, 40, 42],
  engagement = [20, 25, 30, 35, 42, 48, 52, 58, 63, 68, 72, 76, 80, 85]
}) {
  const W = 600,
    H = 160,
    PAD = { top: 12, right: 8, bottom: 4, left: 28 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const days = Math.max(participants.length, submissions.length, engagement.length, 14);

  const allVals = [...participants, ...submissions, ...engagement];
  const maxV = Math.max(...allVals);
  const minV = 0;
  const range = maxV - minV || 1;

  const xPos = (i) => PAD.left + (i / (days - 1)) * innerW;
  const yPos = (v) => PAD.top + innerH - ((v - minV) / range) * innerH;

  const polyline = (data) =>
    data.map((v, i) => `${xPos(i).toFixed(1)},${yPos(v).toFixed(1)}`).join(" ");
  const area = (data) =>
    `${xPos(0).toFixed(1)},${(PAD.top + innerH).toFixed(1)} ` +
    polyline(data) +
    ` ${xPos(days - 1).toFixed(1)},${(PAD.top + innerH).toFixed(1)}`;

  // Y-axis gridlines
  const gridLines = [0, 0.25, 0.5, 0.75, 1].map((t) => ({
    y: PAD.top + innerH - t * innerH,
    label: Math.round(minV + t * range),
  }));

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      style={{ height: 120 }}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id="gradParticipants" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#818cf8" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#818cf8" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="gradSubmissions" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#a78bfa" stopOpacity="0.2" />
          <stop offset="100%" stopColor="#a78bfa" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="gradEngagement" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#34d399" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#34d399" stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* Horizontal grid lines */}
      {gridLines.map((g, i) => (
        <g key={i}>
          <line
            x1={PAD.left}
            y1={g.y}
            x2={PAD.left + innerW}
            y2={g.y}
            stroke="rgba(148,163,184,0.08)"
            strokeWidth="1"
          />
          <text
            x={PAD.left - 6}
            y={g.y + 4}
            textAnchor="end"
            fontSize="9"
            fill="rgba(148,163,184,0.4)"
          >
            {g.label}
          </text>
        </g>
      ))}

      {/* Filled areas */}
      <polygon points={area(participants)} fill="url(#gradParticipants)" />
      <polygon points={area(submissions)} fill="url(#gradSubmissions)" />
      <polygon points={area(engagement)} fill="url(#gradEngagement)" />

      {/* Lines */}
      <polyline
        points={polyline(participants)}
        fill="none"
        stroke="#818cf8"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <polyline
        points={polyline(submissions)}
        fill="none"
        stroke="#a78bfa"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <polyline
        points={polyline(engagement)}
        fill="none"
        stroke="#34d399"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Endpoint dots */}
      {[
        [participants, "#818cf8"],
        [submissions, "#a78bfa"],
        [engagement, "#34d399"],
      ].map(([data, color], si) => (
        <circle
          key={si}
          cx={xPos(days - 1)}
          cy={yPos(data[days - 1])}
          r="3.5"
          fill={color}
          stroke="#0f172a"
          strokeWidth="2"
        />
      ))}
    </svg>
  );
}
