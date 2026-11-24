// 01 요약, 02 경기 흐름 새 배치 시안(11-24, 계획 문서 '칸 다시 묶기' 탭의 새 배치 표대로).
// artifact 한 파일(window.__DRAFT__)에서만 보여요. 나머지 섹션은 본 리포트 그대로예요.
// 사용자가 확인하면 sections/Summary.jsx, sections/Flow.jsx로 옮겨요.
// 03~07 시안은 DraftRest.jsx(11-24, 5단계). Soft Y2K 실험 세 곳은 쓰지 않기로 해서 뺐어요(11-24 사용자).
import { useMemo, useState } from 'react'
import Report from '../Report.jsx'
import { Section, Lede, Pending, Gi, signed, num, mmss, fix, cx } from '../ui.jsx'
import { styleAxes } from '../sections/Extra.jsx'
import { Radar } from './charts.jsx'
import { Lane2, Team2, Build2, Check2 } from './DraftRest.jsx'
import { Summary3, Flow3, Lane3, DeathHead } from './Draft3.jsx'
import './draft.css'

const Xm = () => <i className="xm" aria-hidden="true" />

// ================================================================ 01 요약
function StyleBars({ axes, on, setOn }) {
  return (
    <div className="s2-bars">
      {axes.map((a, i) => (
        <div key={a.axis} className={cx('s2-bar', on === i && 'on', a.value == null && 'is-none')}
          onPointerEnter={() => setOn(i)} onPointerLeave={() => setOn(null)}>
          <b className="s2-ax">{a.axis}</b>
          <div className="s2-track">
            {a.value != null && <span className={cx('s2-fill', a.x >= 1 ? 'is-good' : 'is-low')} style={{ width: `${a.value}%` }} />}
            <i className="s2-avg" />
          </div>
          <span className="s2-x num">{a.text ?? '–'}</span>
          <span className="s2-raw small num">
            {a.value == null ? '숫자를 아직 모으는 중이에요' : <>나 {+a.me.toFixed(1)} / 평균 {+a.avg.toFixed(1)}<span className="muted"> {a.keys.join(' + ')}</span></>}
            {a.dir < 0 && <em className="s2-note">적게 죽을수록 길어요</em>}
          </span>
        </div>
      ))}
    </div>
  )
}

function FocusNums({ fo, text }) {
  const items = [
    ['죽고 2분 안에 또 죽음', <><b className={cx('num', fo.chain && 'death')}>{fo.chain}</b><small>번</small></>],
    [fo.cut ? `분당 CS, ${fo.cut}분 전과 후` : '분당 CS 전과 후', fo.cut
      ? <><b className="num">{fix(fo.before, 1)}</b><i>→</i><b className="num">{fix(fo.after, 1)}</b></>
      : <b className="num muted">–</b>],
    ['혼자 잡힌 죽음', <><b className={cx('num', fo.alone && 'death')}>{fo.alone}</b><small>번</small></>],
  ]
  return (
    <div className="s2-focus">
      <span className="label">집중력</span>
      <dl>{items.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
      {text && <p className="s2-focus-t">{text}</p>}
    </div>
  )
}

export function Summary2({ fb, d }) {
  const axes = styleAxes(d?.plus?.site)
  const [on, setOn] = useState(null)
  const fo = d.flow.focus
  return (
    <Section no="01">
      <div className="bento s2">
        {fb ? (
          <>
            <div className="cell s2-lede"><Xm /><Lede text={fb.summary} /></div>
            <div className="cell s2-fixes"><Xm />
              <p className="s2-goal"><span className="chip chip-pos">다음 판 목표</span><b>{fb.takeaway}</b></p>
              <ol className="fixes">
                {fb.keyFixes.map((f, i) => (
                  <li key={i} className="fix"><span className="fix-no">{i + 1}</span><div><h3>{f.title}</h3><p>{f.body}</p></div></li>
                ))}
              </ol>
            </div>
          </>
        ) : (
          <div className="cell s2-none"><Xm /><Pending text="이 판은 피드백 글이 아직 없어요. 아래 숫자 기록을 먼저 보여 드려요." /></div>
        )}
        {axes ? (
          <>
            <div className="cell s2-radar"><Xm />
              <div className="s2-head"><span className="label">플레이 스타일, 14분까지</span>
                <span className="s2-key"><i className="s2-key-avg" />{d.me.n} 평균(에메랄드 이상) <i className="s2-key-end" />평균의 2배</span></div>
              <Radar axes={axes} plain on={on} />
            </div>
            <div className="cell s2-barcell"><Xm />
              <div className="s2-head"><span className="label">축마다 나와 평균</span><span className="s2-scale small num"><span>0</span><span>평균</span><span>2배</span></span></div>
              <StyleBars axes={axes} on={on} setOn={setOn} />
            </div>
          </>
        ) : (
          <div className="cell s2-noaxes"><Xm /><p className="lab-empty">이 챔피언은 사이트 평균 숫자를 아직 가져오지 않아서 플레이 스타일을 그리지 못했어요.</p></div>
        )}
        <div className="cell s2-focuscell"><Xm /><FocusNums fo={fo} text={fb && fb.focus} /></div>
      </div>
    </Section>
  )
}

// ================================================================ 02 경기 흐름
const TABS = [['team', '팀 골드'], ['lane', '맞라인 골드'], ['cs', 'CS'], ['lv', '레벨']]
const OB_LEGEND = [['dragon', '드래곤'], ['grub', '공허 유충'], ['herald', '전령'], ['baron', '바론'], ['tower', '포탑'], ['inhib', '억제기']]
const mlab = (m) => (Number.isInteger(m) ? `${m}분` : `${Math.floor(m)}:${String(Math.round((m % 1) * 60)).padStart(2, '0')}`)
const toMin = (t) => { const [m, s] = String(t).split(':').map(Number); return m + (s || 0) / 60 }
const kfmt = (v) => (v === 0 ? '0' : `${v > 0 ? '+' : '−'}${Math.abs(v) >= 1000 ? `${+(Math.abs(v) / 1000).toFixed(1)}k` : Math.abs(v)}`)
const niceStep = (span, want = 5) => {
  const raw = span / want, p = 10 ** Math.floor(Math.log10(raw))
  return [1, 2, 2.5, 5, 10].map((k) => k * p).find((s) => s >= raw) || 10 * p
}
// 한 줄에 넣다가 겹치면 아래 줄로 내려요.
const lanes = (xs, gap) => {
  const last = []
  return xs.map((x) => {
    let r = 0
    while (last[r] != null && x - last[r] < gap) r++
    last[r] = x
    return r
  })
}

function seriesOf(tab, d) {
  const f = d.flow, mins = d.plus?.minute || []
  if (tab === 'team') return { pts: f.points.map((p) => [p.min, p.team]), sub: f.points.map((p) => [p.min, p.bot]), unit: 'gold' }
  const key = { lane: 'gold', cs: 'cs', lv: 'lv' }[tab]
  return { pts: mins.map((r) => [r.m, r[key][0] - r[key][1]]), raw: mins.map((r) => r[key]), unit: key }
}

function FlowChart({ d, fb, tab, hl, setHl, band, setBand }) {
  const f = d.flow, dur = d.hero.durationSec, xmax = dur / 60
  const phases = d.plus?.phases || []
  const moments = (fb && fb.moments) || []
  const S = useMemo(() => seriesOf(tab, d), [tab, d])
  const W = 1480, L = 64, R = 24
  const X = (m) => L + (W - L - R) * Math.min(m, xmax) / xmax
  // 위에서부터: 주요 순간 번호 줄, 킬, 죽음, 구간 머리, 그래프, 오브젝트, 시간
  const moX = moments.map((m) => X(toMin(m.t)))
  const moRow = lanes(moX, 22)
  const moRows = Math.max(1, ...moRow.map((r) => r + 1))
  const yMo = 8, yKill = yMo + moRows * 24 + 6, yDeath = yKill + 18, yBand = yDeath + 20, headH = 70
  const T = yBand + headH + 10, ch = 300
  const objX = f.objs.map((o) => X(o.t / 60000))
  const objRow = lanes(objX, 21)
  const nobj = Math.max(1, ...objRow.map((r) => r + 1))
  const oy = T + ch + 10, H = oy + nobj * 22 + 26
  const vals = S.pts.map((p) => p[1]).concat(S.sub ? S.sub.map((p) => p[1]) : [])
  const lo0 = Math.min(0, ...vals), hi0 = Math.max(0, ...vals)
  const step = S.unit === 'lv' ? 1 : niceStep(Math.max(hi0 - lo0, S.unit === 'cs' ? 10 : 1000))
  const vmax = Math.max(step, Math.ceil(hi0 / step) * step), vmin = Math.min(-step, Math.floor(lo0 / step) * step)
  const Y = (v) => T + ch * (vmax - v) / (vmax - vmin)
  const P = (m, v) => `${X(m).toFixed(1)},${Y(v).toFixed(1)}`
  const pts = S.pts.map(([m, v]) => [Math.min(m, xmax), v])
  const line = pts.map(([m, v]) => P(m, v)).join(' ')
  const area = `${P(0, 0)} ${line} ${P(pts[pts.length - 1][0], 0)}`
  const grid = []
  for (let v = vmin; v <= vmax + 1e-9; v += step) grid.push(+v.toFixed(4))
  const fmt = (v) => (S.unit === 'gold' ? kfmt(v) : signed(Math.round(v)))
  const full = (v) => (S.unit === 'gold' ? signed(Math.round(v)) : signed(Math.round(v)))
  const unitName = { gold: '', cs: ' CS', lv: '레벨' }[S.unit]

  // 이름표: 14분, 25분, 가장 높은 점, 가장 낮은 점. 같은 분이면 하나로 합쳐요.
  const at = (m) => { const p = pts.find((q) => q[0] === m); return p ? p[1] : null }
  const tags = new Map()
  const addTag = (m, text, side) => {
    if (m == null || m > xmax) return
    const v = at(m); if (v == null) return
    const t = tags.get(m)
    if (t) { t.text.push(text); if (side === 'low') t.side = 'low'; return }
    tags.set(m, { m, v, text: [text], side })
  }
  const inner = pts.filter(([m]) => m > 0)
  if (inner.length) {
    const hi = inner.reduce((a, b) => (b[1] > a[1] ? b : a)), lo = inner.reduce((a, b) => (b[1] < a[1] ? b : a))
    ;[14, 25].forEach((m) => addTag(m, `${m}분`, at(m) < 0 ? 'low' : 'high'))
    if (hi[1] > 0) addTag(hi[0], tags.has(hi[0]) ? '가장 앞섬' : `${mlab(hi[0])} 가장 앞섬`, 'high')
    if (lo[1] < 0) addTag(lo[0], tags.has(lo[0]) ? '가장 밀림' : `${mlab(lo[0])} 가장 밀림`, 'low')
  }

  // 마우스: 그 분의 값과 점선 십자선
  const [hov, setHov] = useState(null)
  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect()
    const y = (e.clientY - r.top) * H / r.height
    if (y < T - 4 || y > T + ch + 4) return setHov(null)
    const m = ((e.clientX - r.left) * W / r.width - L) / (W - L - R) * xmax
    if (m < -0.5 || m > xmax + 0.5) return setHov(null)
    let best = 0
    pts.forEach((p, i) => { if (Math.abs(p[0] - m) < Math.abs(pts[best][0] - m)) best = i })
    setHov(best)
  }
  const hp = hov != null ? pts[hov] : null
  const hx = hp ? X(hp[0]) : 0, hy = hp ? Y(hp[1]) : 0
  const tipW = 196, tipH = S.sub || S.raw ? 70 : 50
  const tipX = hp ? (hx + 14 + tipW > W - R ? hx - 14 - tipW : hx + 14) : 0
  const tipY = hp ? Math.min(Math.max(hy - tipH / 2, T + 4), T + ch - tipH - 4) : 0

  const bands = phases.filter((p) => p.from < xmax).map((p) => ({ ...p, x0: X(p.from), x1: X(p.to == null ? xmax : Math.min(p.to, xmax)) }))
  const [bh, setBh] = useState(null)
  const bp = bh != null ? bands[bh] : null
  const tipB = bp && { w: 250, x: Math.min(bp.x0 + 6, W - R - 250) }

  return (
    <svg className={cx('chart f2-chart', hp && 'is-hover', band != null && 'has-band')} viewBox={`0 0 ${W} ${H}`} role="img"
      aria-label="분당 차이 그래프" onPointerMove={onMove} onPointerLeave={() => setHov(null)}>
      <defs>
        <clipPath id="f2-pos"><rect x="0" y="0" width={W} height={Y(0).toFixed(1)} /></clipPath>
        <clipPath id="f2-neg"><rect x="0" y={Y(0).toFixed(1)} width={W} height={H} /></clipPath>
      </defs>
      {bands.map((p, i) => (
        <rect key={p.name} className={cx('band', i % 2 === 1 && 'band-alt')} x={p.x0.toFixed(1)} y={yBand} width={(p.x1 - p.x0).toFixed(1)} height={T + ch - yBand} />
      ))}
      {grid.map((v) => (
        <g key={v}>
          <line className={v === 0 ? 'grid grid-zero' : 'grid'} x1={L} x2={W - R} y1={Y(v).toFixed(1)} y2={Y(v).toFixed(1)} />
          <text className="ax" x={L - 8} y={(Y(v) + 4).toFixed(1)} textAnchor="end">{fmt(v)}</text>
        </g>
      ))}
      {[0, 5, 10, 15, 20, 25, 30, 35, 40].filter((m) => m <= xmax).map((m) => <text key={m} className="ax" x={X(m).toFixed(1)} y={H - 6} textAnchor="middle">{m}:00</text>)}
      <g key={tab}>
        <polygon className="area-pos" points={area} clipPath="url(#f2-pos)" />
        <polygon className="area-neg" points={area} clipPath="url(#f2-neg)" />
        {S.sub && <polyline className="ln-bot" points={S.sub.map(([m, v]) => P(Math.min(m, xmax), v)).join(' ')} />}
        <polyline className="ln-team" points={line} pathLength="1" />
      </g>
      {/* 고른 구간만 밝게: 나머지 구간을 흰 막으로 덮어요 */}
      {band != null && bands.map((p, i) => i !== band && (
        <rect key={i} className="f2-veil" x={p.x0.toFixed(1)} y={yBand} width={(p.x1 - p.x0).toFixed(1)} height={T + ch - yBand} />
      ))}
      {[...tags.values()].map((t) => {
        // 위쪽 이름표가 구간 머리에 닿으면 점 아래로, 아래쪽 이름표가 오브젝트 줄에 닿으면 점 위로 옮겨요.
        const x = X(t.m), y = Y(t.v)
        const up = t.side !== 'low' ? y - 30 > T : y + 42 > T + ch
        const anchor = x > W - R - 120 ? 'end' : x < L + 80 ? 'start' : 'middle'
        return (
          <g key={t.m} className="f2-tag" pointerEvents="none">
            <circle className="f2-tag-dot" cx={x.toFixed(1)} cy={y.toFixed(1)} r="4" />
            <text className="f2-tag-k" x={x.toFixed(1)} y={(up ? y - 28 : y + 22).toFixed(1)} textAnchor={anchor}>{t.text.join(', ')}</text>
            <text className={cx('f2-tag-v', t.v < 0 && 'neg')} x={x.toFixed(1)} y={(up ? y - 11 : y + 39).toFixed(1)} textAnchor={anchor}>{full(t.v)}{unitName}</text>
          </g>
        )
      })}
      {/* 구간 머리: 이름, 팀 골드 변화, 내 킬/죽음/도움. 마우스를 올리면 나머지 숫자, 누르면 그 구간만 밝게 */}
      {bands.map((p, i) => (
        <g key={p.name} className={cx('f2-head', band === i && 'on')} onPointerEnter={() => setBh(i)} onPointerLeave={() => setBh(null)}
          onClick={() => setBand(band === i ? null : i)} role="button" tabIndex="0" aria-label={`${p.name} 구간만 보기`}
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setBand(band === i ? null : i)}>
          <rect className="f2-head-hit" x={p.x0.toFixed(1)} y={yBand} width={(p.x1 - p.x0).toFixed(1)} height={headH} />
          <line className="f2-head-rule" x1={p.x0.toFixed(1)} x2={p.x1.toFixed(1)} y1={yBand + headH} y2={yBand + headH} />
          <text className="f2-head-n" x={(p.x0 + 8).toFixed(1)} y={yBand + 17}>{p.name} <tspan className="f2-head-r">{p.to == null ? `${p.from}분~` : `${p.from}~${p.to}분`}</tspan></text>
          <text className={cx('f2-head-v', p.teamGold < 0 ? 'neg' : 'pos')} x={(p.x0 + 8).toFixed(1)} y={yBand + 41}>{signed(p.teamGold)}</text>
          <text className="f2-head-kda" x={(p.x0 + 8).toFixed(1)} y={yBand + 59}>{p.k} / <tspan className="death">{p.d}</tspan> / {p.a}</text>
        </g>
      ))}
      {f.myKills.map((t, i) => {
        const x = X(t / 60000)
        return <rect key={i} className="mk-kill" x={(x - 1.5).toFixed(1)} y={yKill} width="3" height="12"><title>{mmss(t)} 내 킬</title></rect>
      })}
      {f.myDeaths.map((t, i) => {
        const x = X(t / 60000)
        return (
          <g key={i}>
            <line className="mk-death-line" x1={x.toFixed(1)} x2={x.toFixed(1)} y1={yDeath + 10} y2={T + ch} />
            <rect className="mk-death" x={(x - 5).toFixed(1)} y={yDeath} width="10" height="10"><title>{mmss(t)} {i + 1}번째 죽음</title></rect>
          </g>
        )
      })}
      <text className="ax-k" x={L - 8} y={yMo + 13} textAnchor="end">순간</text>
      <text className="ax-k" x={L - 8} y={yKill + 11} textAnchor="end">킬</text>
      <text className="ax-k" x={L - 8} y={yDeath + 10} textAnchor="end">죽음</text>
      <text className="ax-k" x={L - 8} y={oy + 14} textAnchor="end">오브젝트</text>
      {f.objs.map((o, i) => (
        <g key={i}>
          <title>{mmss(o.t)} {o.name} ({o.ours ? '우리 팀' : '상대 팀'})</title>
          <use className={o.ours ? 'ob-ours' : 'ob-theirs'} href={`#i-${o.icon}`} x={(objX[i] - 10).toFixed(1)} y={oy + objRow[i] * 22} width="20" height="20" />
        </g>
      ))}
      {/* 주요 순간 번호: 글은 아래 격자에만 있어요. 서로 마우스를 올리면 같이 강조돼요 */}
      {hl != null && <line className="f2-mo-line" x1={moX[hl].toFixed(1)} x2={moX[hl].toFixed(1)} y1={yMo + moRow[hl] * 24 + 18} y2={T + ch} />}
      {moments.map((m, i) => (
        <g key={i} className={cx('f2-mo', m.key && 'key', m.crit && `crit-${m.crit}`, hl === i && 'on')}
          onPointerEnter={() => setHl(i)} onPointerLeave={() => setHl(null)}>
          <title>{m.t} {m.text}</title>
          <rect x={(moX[i] - 9).toFixed(1)} y={yMo + moRow[i] * 24} width="18" height="18" />
          <text x={moX[i].toFixed(1)} y={yMo + moRow[i] * 24 + 13} textAnchor="middle">{i + 1}</text>
        </g>
      ))}
      {hp && (
        <g className="hov" pointerEvents="none">
          <line className="f2-cross" x1={hx.toFixed(1)} x2={hx.toFixed(1)} y1={T} y2={T + ch} />
          <line className="f2-cross" x1={L} x2={W - R} y1={hy.toFixed(1)} y2={hy.toFixed(1)} />
          {S.sub && <circle className="hov-dot hov-bot" cx={hx.toFixed(1)} cy={Y(S.sub[hov][1]).toFixed(1)} r="4" />}
          <circle className="hov-dot" cx={hx.toFixed(1)} cy={hy.toFixed(1)} r="5" />
          <g transform={`translate(${tipX.toFixed(1)},${tipY.toFixed(1)})`}>
            <rect className="hov-box" width={tipW} height={tipH} />
            <text className="hov-t" x="12" y="20">{Number.isInteger(hp[0]) ? `${hp[0]}:00` : mlab(hp[0])}</text>
            {S.sub ? (
              <>
                <text className="hov-k" x="12" y="39">팀 전체</text><text className={cx('hov-v', hp[1] < 0 && 'neg')} x={tipW - 12} y="39" textAnchor="end">{signed(hp[1])}</text>
                <text className="hov-k" x="12" y="57">바텀 2대2</text><text className={cx('hov-v', S.sub[hov][1] < 0 && 'neg')} x={tipW - 12} y="57" textAnchor="end">{signed(S.sub[hov][1])}</text>
              </>
            ) : (
              <>
                <text className="hov-k" x="12" y="39">차이</text><text className={cx('hov-v', hp[1] < 0 && 'neg')} x={tipW - 12} y="39" textAnchor="end">{signed(hp[1])}</text>
                {S.raw && <><text className="hov-k" x="12" y="57">나 : {d.opp.n}</text><text className="hov-v plain" x={tipW - 12} y="57" textAnchor="end">{num(S.raw[hov][0])} : {num(S.raw[hov][1])}</text></>}
              </>
            )}
          </g>
        </g>
      )}
      {bp && (
        <g className="hov" pointerEvents="none" transform={`translate(${tipB.x.toFixed(1)},${yBand + headH + 6})`}>
          <rect className="hov-box" width={tipB.w} height="78" />
          <text className="hov-k" x="12" y="22">{d.opp.n}와 골드 차이 변화</text><text className={cx('hov-v', bp.laneGold < 0 && 'neg')} x={tipB.w - 12} y="22" textAnchor="end">{signed(bp.laneGold)}</text>
          <text className="hov-k" x="12" y="44">CS 나 : 상대</text><text className="hov-v plain" x={tipB.w - 12} y="44" textAnchor="end">{bp.cs[0]} : {bp.cs[1]}</text>
          <text className="hov-k" x="12" y="66">팀 킬 : 데스</text><text className="hov-v plain" x={tipB.w - 12} y="66" textAnchor="end">{bp.teamK} : {bp.teamD}</text>
        </g>
      )}
    </svg>
  )
}

// 변곡 구간: 그래프와 같은 시간 축에 얇은 괄호 + 골드 변화 + 한 줄 주석. 좁은 구간은 글 칸을 넓히고 겹치면 아래 줄로 내려요.
function Swings({ f, dur, fb }) {
  const xmax = dur / 60, W = 1480, L = 64, R = 24
  const pct = (m) => ((L + (W - L - R) * Math.min(m, xmax) / xmax) / W) * 100
  const notes = (fb && fb.swings) || {}
  const keys = Object.keys(notes).map(Number)
  // 피드백 글의 키가 구간 시작 분과 조금 다른 판이 있어서(예: 9~25분 구간에 "12"), 그 구간 안에 있는 키를 찾아요.
  const noteOf = (w) => notes[String(w.m0)] ?? (() => { const k = keys.find((x) => x >= w.m0 && x < w.m1); return k != null ? notes[String(k)] : '' })()
  // 글 칸 너비: 괄호 너비를 따르되 16%~40% 사이. 왼쪽부터 놓고, 오른쪽 끝을 넘으면 오른쪽부터 밀어 넣어요.
  const MINW = 16, MAXW = 40, GAP = 0.8, LEFT = (L / W) * 100, RIGHT = 100 - (R / W) * 100
  const items = f.swings.map((w) => {
    const a = pct(w.m0), b = pct(w.m1)
    return { w, a, b, width: Math.min(MAXW, Math.max(b - a, MINW)), note: noteOf(w), row: 0 }
  })
  let end = LEFT
  items.forEach((it) => { it.left = Math.max(it.a, end); end = it.left + it.width + GAP })
  let bound = RIGHT
  for (let i = items.length - 1; i >= 0; i--) { items[i].left = Math.min(items[i].left, bound - items[i].width); bound = items[i].left - GAP }
  items.forEach((it) => { if (it.left < LEFT - 0.5) { it.row = 1; it.left = Math.min(it.a, RIGHT - it.width) } else it.left = Math.max(LEFT, it.left) })
  return (
    <div className="f2-sw">
      <span className="f2-sw-k ax-k">유불리</span>
      <div className="f2-sw-brs">
        {items.map((it, i) => <span key={i} className={cx('f2-sw-br', it.w.delta > 0 ? 'up' : 'down')} style={{ left: `${it.a}%`, width: `${it.b - it.a}%` }} />)}
      </div>
      <div className="f2-sw-row">
        {items.map((it, i) => (
          <div key={i} className={cx('f2-sw-txt', it.w.delta > 0 ? 'up' : 'down')} style={{ left: `${it.left}%`, width: `${it.width}%`, gridRow: it.row + 1 }}>
            <b className="num">{it.w.m0}~{Math.min(it.w.m1, Math.floor(xmax))}분 {it.w.delta > 0 ? '따라잡음' : '벌어짐'} <span className={it.w.delta < 0 ? 'neg' : 'pos'}>{signed(it.w.delta)}</span></b>
            {it.note && <span>{it.note}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}

// 4열이 기본이고, 순간이 9개 이상이면 5열로 줄 수를 줄여요. 마지막 칸은 남은 칸을 채워요.
function Moments({ moments, hl, setHl }) {
  const cols = moments.length > 8 ? 5 : 4
  return (
    <ol className={cx('bento f2-mo-grid', `cols-${cols}`)}>
      {moments.map((m, i) => (
        <li key={i} className={cx('cell', m.key && 'm-key', m.crit && `m-crit-${m.crit}`, hl === i && 'on')}
          style={i === moments.length - 1 && moments.length % cols ? { gridColumn: `span ${cols - (moments.length - 1) % cols}` } : undefined}
          onPointerEnter={() => setHl(i)} onPointerLeave={() => setHl(null)}>
          <Xm />
          <span className="f2-mo-no num">{i + 1}</span>
          <time className="num">{m.t}</time>
          <span className="f2-mo-t">{m.text}</span>
        </li>
      ))}
    </ol>
  )
}

export function Flow2({ d, fb }) {
  const f = d.flow
  const dur = d.hero.durationSec
  const [tab, setTab] = useState('team')
  const [hl, setHl] = useState(null)
  const [band, setBand] = useState(null)
  const shown = new Set(f.objs.map((o) => o.icon))
  const moments = (fb && fb.moments) || []
  const tabs = d.plus?.minute ? TABS : TABS.slice(0, 1)
  const title = { team: '분당 팀 골드 차이', lane: `${d.oppWith} 골드 차이`, cs: `${d.oppWith} CS 차이`, lv: `${d.oppWith} 레벨 차이` }[tab]
  return (
    <Section no="02">
      <div className="panel f2">
        <div className="f2-top">
          <h3>{title} {tab === 'team' && <span className="h-final">(최종 <b className={cx('num', f.final < 0 && 'neg')}>{signed(f.final)}</b>)</span>}</h3>
          <div className="lab-tabs f2-tabs" role="tablist">
            {tabs.map(([k, n]) => <button key={k} role="tab" aria-selected={tab === k} className={cx(tab === k && 'on')} onClick={() => setTab(k)}>{n}</button>)}
          </div>
          <ul className="legend">
            <li><span className="lg lg-pos" />{tab === 'team' ? '우리 팀 앞섬' : '내가 앞섬'}</li>
            <li><span className="lg lg-neg" />{tab === 'team' ? '상대 팀 앞섬' : `${d.opp.n} 앞섬`}</li>
            {tab === 'team' && <><li><span className="lg lg-team" />팀 전체</li><li><span className="lg lg-bot" />바텀 2대2</li></>}
            <li><span className="lg lg-death" />내가 죽음</li>
            <li><span className="lg lg-kill" />내 킬</li>
          </ul>
        </div>
        <p className="f2-hint small muted">구간 머리 숫자는 그 구간 동안 바뀐 팀 골드와 내 킬 / 죽음 / 도움이에요. 머리를 누르면 그 구간만 밝게 보여요.</p>
        <div className="chart-wrap">
          <FlowChart d={d} fb={fb} tab={tab} hl={hl} setHl={setHl} band={band} setBand={setBand} />
          <Swings f={f} dur={dur} fb={fb} />
        </div>
        <ul className="ob-legend f2-ob">
          {OB_LEGEND.filter(([i]) => shown.has(i)).map(([i, n]) => <li key={i}><Gi name={i} />{n}</li>)}
          <li className="sep" aria-hidden="true" />
          <li className="lg-ours"><Gi name="tower" /><span className="muted">우리 팀</span></li>
          <li className="lg-theirs"><Gi name="tower" /><span className="muted">상대 팀</span></li>
        </ul>
      </div>
      {moments.length > 0 && <Moments moments={moments} hl={hl} setHl={setHl} />}
    </Section>
  )
}

export default function Draft({ data }) {
  // 11-24 저녁: 정보 위계 탭대로 01~03과 04 머리를 Draft3.jsx로 바꿨어요. 이전 시안(Summary2, Flow2, Lane2)은 비교용으로 남겨 둬요.
  return <Report data={data} over={{ Summary: Summary3, Flow: Flow3, Lane: Lane3, Team: Team2, Build: Build2, Checklist: Check2, deaths: { autoOpen: true, head: DeathHead, noStrip: true } }} />
}
