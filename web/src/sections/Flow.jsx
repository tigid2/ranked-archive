import { Section, Gi, signed, mmss, fix, cx } from '../ui.jsx'

const OB_LEGEND = [['dragon', '드래곤'], ['grub', '공허 유충'], ['herald', '전령'], ['baron', '바론'], ['tower', '포탑'], ['inhib', '억제기']]

function GoldChart({ f, dur }) {
  const xmax = dur / 60
  const W0 = 1120, L = 64, R = 16
  // 오브젝트 아이콘이 겹치면 아래로 쌓아요. 3줄 이상이면 그만큼 차트를 늘려서 시간 글자와 겹치지 않게 해요.
  const rowsOf = () => {
    const last = {}
    return f.objs.map((o) => {
      const x = L + (W0 - L - R) * (o.t / 60000) / xmax
      let r = 0
      while (Math.abs((last[r] ?? -99) - x) < 21) r++
      last[r] = x
      return r
    })
  }
  const objRows = rowsOf()
  const nrows = Math.max(1, ...objRows.map((r) => r + 1))
  const extra = Math.max(0, nrows - 2) * 22
  const W = W0, H = 380 + extra, T = 66, B = 84 + extra
  const ch = H - T - B
  const vals = f.points.flatMap((p) => [p.team, p.bot])
  const step = 2500
  const vmax = Math.max(step, Math.ceil(Math.max(...vals) / step) * step)
  const vmin = Math.min(-step, Math.floor(Math.min(...vals) / step) * step)
  const X = (m) => L + (W - L - R) * m / xmax
  const Y = (v) => T + ch * (vmax - v) / (vmax - vmin)
  const p2 = (m, v) => `${X(m).toFixed(1)},${Y(v).toFixed(1)}`
  const pts = f.points.map((p) => [Math.min(p.min, xmax), p.team])
  pts[pts.length - 1] = [xmax, pts[pts.length - 1][1]]
  const line = pts.map(([m, v]) => p2(m, v)).join(' ')
  const area = `${p2(0, 0)} ${line} ${p2(xmax, 0)}`
  const bot = f.points.map((p) => p2(Math.min(p.min, xmax), p.bot)).join(' ')
  const grid = []
  for (let v = vmin; v <= vmax; v += step) grid.push(v)
  const ticks = []
  for (let m = 0; m <= Math.floor(xmax); m += 5) ticks.push(m)
  const oy = T + ch + 10
  const k = (v) => (v === 0 ? '0' : v > 0 ? `+${v / 1000}k` : `−${Math.abs(v) / 1000}k`)
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="분당 팀 골드 차이와 바텀 2대2 골드 차이">
      <defs>
        <clipPath id="cp-pos"><rect x="0" y="0" width={W} height={Y(0).toFixed(1)} /></clipPath>
        <clipPath id="cp-neg"><rect x="0" y={Y(0).toFixed(1)} width={W} height={H} /></clipPath>
      </defs>
      {[[0, 14, '라인전'], [14, 25, '중반부'], [25, xmax, '후반부']].filter(([a]) => a < xmax).map(([a, b0, lab]) => [a, Math.min(b0, xmax), lab]).map(([a, b, lab]) => (
        <g key={lab}>
          <rect className={cx('band', lab === '중반부' && 'band-alt')} x={X(a).toFixed(1)} y={T} width={(X(b) - X(a)).toFixed(1)} height={ch} />
          <text className="ax-phase" x={(X(a) + 8).toFixed(1)} y={T + 16}>{lab}</text>
        </g>
      ))}
      {grid.map((v) => (
        <g key={v}>
          <line className={v === 0 ? 'grid grid-zero' : 'grid'} x1={L} x2={W - R} y1={Y(v).toFixed(1)} y2={Y(v).toFixed(1)} />
          <text className="ax" x={L - 8} y={(Y(v) + 4).toFixed(1)} textAnchor="end">{k(v)}</text>
        </g>
      ))}
      {ticks.map((m) => <text key={m} className="ax" x={X(m).toFixed(1)} y={H - 6} textAnchor="middle">{m}:00</text>)}
      <polygon className="area-pos" points={area} clipPath="url(#cp-pos)" />
      <polygon className="area-neg" points={area} clipPath="url(#cp-neg)" />
      <polyline className="ln-bot" points={bot} />
      <polyline className="ln-team" points={line} />
      {f.myKills.map((t, i) => {
        const x = X(t / 60000)
        return <rect key={i} className="mk-kill" x={(x - 1.5).toFixed(1)} y={T - 52} width="3" height="12"><title>{mmss(t)} 내 킬</title></rect>
      })}
      {f.myDeaths.map((t, i) => {
        const x = X(t / 60000)
        return (
          <g key={i}>
            <line className="mk-death-line" x1={x.toFixed(1)} x2={x.toFixed(1)} y1={T - 19} y2={T + ch} />
            <rect className="mk-death" x={(x - 5).toFixed(1)} y={T - 29} width="10" height="10"><title>{mmss(t)} {i + 1}번째 죽음</title></rect>
          </g>
        )
      })}
      <text className="ax-k" x={L - 8} y={T - 42} textAnchor="end">킬</text>
      <text className="ax-k" x={L - 8} y={T - 20} textAnchor="end">죽음</text>
      <text className="ax-k" x={L - 8} y={oy + 14} textAnchor="end">오브젝트</text>
      {f.objs.map((o, i) => {
        const x = X(o.t / 60000)
        return (
          <g key={i}>
            <title>{mmss(o.t)} {o.name} ({o.ours ? '우리 팀' : '상대 팀'})</title>
            <use className={o.ours ? 'ob-ours' : 'ob-theirs'} href={`#i-${o.icon}`} x={(x - 10).toFixed(1)} y={oy + objRows[i] * 22} width="20" height="20" />
          </g>
        )
      })}
    </svg>
  )
}

function FlowExtra({ f, dur, fb }) {
  const total = dur / 60
  const notes = (fb && fb.swings) || {}
  const fo = f.focus
  return (
    <div className="flow-extra">
      <div className="panel">
        <div className="panel-head">
          <h3>유불리 운영</h3>
          <span className="label">가장 앞섰을 때 <b className="num">{signed(f.peak.v)}</b> ({f.peak.min}분)</span>
        </div>
        <div className="sw-strip">
          {f.swings.map((w, i) => (
            <span key={i} className={cx('sw-seg', w.delta > 0 ? 'up' : 'down')}
              style={{ width: `${((Math.min(w.m1, total) - w.m0) / total * 100).toFixed(2)}%` }}
              title={`${w.m0}~${w.m1}분 ${signed(w.delta)}`} />
          ))}
        </div>
        <ol className="sw-list">
          {f.swings.map((w, i) => (
            <li key={i} className={w.delta > 0 ? 'up' : 'down'}>
              <span className="sw-time num">{w.m0}~{Math.min(w.m1, Math.floor(dur / 60))}분</span>
              <span className="sw-kind">{w.delta > 0 ? '따라잡음' : '벌어짐'} <b className="num">{signed(w.delta)}</b></span>
              <span className="sw-me">킬 <b className={cx('num', w.kills && 'k')}>{w.kills}</b> 죽음 <b className={cx('num', w.deaths && 'd')}>{w.deaths}</b></span>
              <span className="sw-note">{notes[String(w.m0)] || ''}</span>
            </li>
          ))}
        </ol>
      </div>
      <div className="panel focus">
        <div className="panel-head"><h3>집중력</h3></div>
        <dl className="focus-stats">
          <div><dt>죽고 2분 안에 또 죽음</dt><dd><b className={cx('num', fo.chain && 'd')}>{fo.chain}</b>번</dd></div>
          <div>
            <dt>{fo.cut ? `분당 CS, ${fo.cut}분 전과 후` : '분당 CS'}</dt>
            <dd>{fo.cut ? <><b className="num">{fix(fo.before, 1)}</b><i>→</i><b className="num">{fix(fo.after, 1)}</b></> : <b className="num">-</b>}</dd>
          </div>
          <div><dt>혼자 잡힌 죽음</dt><dd><b className={cx('num', fo.alone && 'd')}>{fo.alone}</b>번</dd></div>
        </dl>
        <p className="body">{(fb && fb.focus) || ''}</p>
      </div>
    </div>
  )
}

export default function Flow({ d, fb }) {
  const f = d.flow
  const dur = d.hero.durationSec
  const shown = new Set(f.objs.map((o) => o.icon))
  const moments = (fb && fb.moments) || []
  return (
    <Section no="02">
      <div className="panel">
        <div className="panel-head">
          <h3>분당 골드 차이 <span className="h-final">(최종 <b className={cx('num', f.final < 0 && 'neg')}>{signed(f.final)}</b>)</span></h3>
          <ul className="legend">
            <li><span className="lg lg-pos" />우리 팀 앞섬</li>
            <li><span className="lg lg-neg" />상대 팀 앞섬</li>
            <li><span className="lg lg-team" />팀 전체</li>
            <li><span className="lg lg-bot" />바텀 2대2</li>
            <li><span className="lg lg-death" />내가 죽음</li>
            <li><span className="lg lg-kill" />내 킬</li>
          </ul>
        </div>
        <div className="chart-wrap"><GoldChart f={f} dur={dur} /></div>
        <div className="flow-foot">
          <div className="mini-stats">
            {[['14분 팀 골드', f.gd14], ['25분 팀 골드', f.gd25], ['가장 크게 밀렸을 때', f.gdMin]].filter(([, v]) => v != null).map(([lab, v]) => (
              <div key={lab}><span className="label">{lab}</span><span className={cx('ms-val', v < 0 && 'neg')}>{signed(v)}</span></div>
            ))}
          </div>
          <ul className="ob-legend">
            {OB_LEGEND.filter(([i]) => shown.has(i)).map(([i, n]) => <li key={i}><Gi name={i} />{n}</li>)}
            <li className="sep" aria-hidden="true" />
            <li className="lg-ours"><Gi name="tower" /><span className="muted">우리 팀</span></li>
            <li className="lg-theirs"><Gi name="tower" /><span className="muted">상대 팀</span></li>
          </ul>
        </div>
      </div>
      <FlowExtra f={f} dur={dur} fb={fb} />
      {moments.length > 0 && (
        <>
          <h3 className="sub-h">주요 순간</h3>
          <ol className="moments">
            {moments.map((m, i) => (
              <li key={i} className={cx(m.key && 'm-key', m.crit && `m-crit-${m.crit}`)}><time>{m.t}</time><span>{m.text}</span></li>
            ))}
          </ol>
        </>
      )}
    </Section>
  )
}
