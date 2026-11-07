// 실험 페이지용 작은 그림들: 플레이 스타일 그래프, 백분위 막대, 기준 범위, 차이 그래프
import { cx, num } from '../ui.jsx'

// 다섯 축 그래프. 축 값은 0~100(기준 판 중 이 판보다 못한 판의 비율). 50 = 기준 중앙값.
export function Radar({ axes }) {
  const W = 320, C = W / 2, R = 108
  const n = axes.length
  const pt = (i, v) => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / n
    return [C + Math.cos(a) * R * (v / 100), C + Math.sin(a) * R * (v / 100)]
  }
  const ring = (v) => axes.map((_, i) => pt(i, v).join(',')).join(' ')
  const have = axes.map((a, i) => [a, i]).filter(([a]) => a.value != null)
  const poly = have.map(([a, i]) => pt(i, a.value).join(',')).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${W}`} className="lab-radar" role="img" aria-label="플레이 스타일 그래프">
      {[25, 75, 100].map((v) => <polygon key={v} points={ring(v)} className="rd-ring" />)}
      <polygon points={ring(50)} className="rd-mid" />
      {axes.map((_, i) => { const [x, y] = pt(i, 100); return <line key={i} x1={C} y1={C} x2={x} y2={y} className="rd-ring" /> })}
      {have.length >= 3 && <polygon points={poly} className="rd-me" />}
      {have.map(([a, i]) => { const [x, y] = pt(i, a.value); return <circle key={i} cx={x} cy={y} r="3.5" className="rd-dot" /> })}
      {axes.map((a, i) => {
        const [x, y] = pt(i, 128)
        return (
          <g key={a.axis} className={cx('rd-label', a.value == null && 'is-none')}>
            <text x={x} y={y - 7} textAnchor="middle" className="rd-axis">{a.axis}</text>
            <text x={x} y={y + 11} textAnchor="middle" className="rd-val num">{a.value == null ? '모으는 중' : `${a.value}`}</text>
          </g>
        )
      })}
    </svg>
  )
}

// 백분위 막대. 방향이 없는 지표(0)는 순위 색 없이 위치만 보여 줘요.
export function PctBar({ m }) {
  const p = m.pct ?? 0
  const tone = m.dir === 0 ? 'is-neutral' : p >= 50 ? 'is-good' : 'is-bad'
  const text = m.dir === 0 ? `기준 판 ${p}%보다 큼` : p >= 50 ? `상위 ${Math.max(1, 100 - p)}%` : `하위 ${Math.max(1, p)}%`
  return (
    <div className={cx('pct-row', tone)}>
      <span className="pct-label">{m.label}</span>
      <div className="pct-track"><span className="pct-fill" style={{ width: `${p}%` }} /><i style={{ left: '25%' }} /><i style={{ left: '50%' }} /><i style={{ left: '75%' }} /></div>
      <span className="pct-text num">{text}</span>
    </div>
  )
}

// 기준 범위(가운데 50%)와 중앙값, 내 값
export function RangeRow({ m, fmt = (v) => num(Math.round(v)) }) {
  const lo = Math.min(m.p25, m.mine), hi = Math.max(m.p75, m.mine)
  const pad = (hi - lo) * 0.15 || 1
  const a = lo - pad, b = hi + pad
  const x = (v) => `${(((v - a) / (b - a)) * 100).toFixed(1)}%`
  const tone = m.band === '상위 25%' ? 'is-good' : m.band === '하위 25%' ? 'is-bad' : ''
  return (
    <div className={cx('rg-row', tone)}>
      <span className="pct-label">{m.label}</span>
      <div className="rg-track">
        <span className="rg-box" style={{ left: x(m.p25), width: `calc(${x(m.p75)} - ${x(m.p25)})` }} />
        <span className="rg-med" style={{ left: x(m.median) }} />
        <span className="rg-me" style={{ left: x(m.mine) }} />
      </div>
      <span className="rg-nums num"><b>{fmt(m.mine)}</b><span className="muted"> / 중앙 {fmt(m.median)}</span></span>
    </div>
  )
}

// 분 단위 차이 그래프. 0 위는 우리 쪽 앞섬(연한 민트), 아래는 상대 앞섬(연한 회색).
export function DiffChart({ values, unit = '' }) {
  const W = 1100, H = 220, P = 36
  const n = values.length
  const mx = Math.max(1, ...values.map((v) => Math.abs(v)))
  const X = (i) => P + (i * (W - 2 * P)) / Math.max(1, n - 1)
  const Y = (v) => H / 2 - (v / mx) * (H / 2 - 14)
  const line = values.map((v, i) => `${X(i)},${Y(v)}`).join(' ')
  const area = `${X(0)},${H / 2} ${line} ${X(n - 1)},${H / 2}`
  const ticks = values.map((_, i) => i).filter((i) => i % 5 === 0)
  return (
    <svg viewBox={`0 0 ${W} ${H + 18}`} className="lab-diff" role="img" aria-label="분 단위 차이 그래프">
      <defs>
        <clipPath id="dc-up"><rect x="0" y="0" width={W} height={H / 2} /></clipPath>
        <clipPath id="dc-dn"><rect x="0" y={H / 2} width={W} height={H / 2} /></clipPath>
      </defs>
      <polygon points={area} clipPath="url(#dc-up)" className="dc-up" />
      <polygon points={area} clipPath="url(#dc-dn)" className="dc-dn" />
      <line x1={P} x2={W - P} y1={H / 2} y2={H / 2} className="dc-zero" />
      <polyline points={line} className="dc-line" />
      <text x={P + 4} y={14} className="dc-ax num">+{num(mx)}{unit}</text>
      <text x={P + 4} y={H - 4} className="dc-ax num">−{num(mx)}{unit}</text>
      {ticks.map((i) => <text key={i} x={X(i)} y={H + 14} textAnchor="middle" className="dc-ax num">{i}분</text>)}
    </svg>
  )
}
