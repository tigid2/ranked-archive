// 정보 위계(11-24 저녁, 계획 문서 '정보 위계' 탭)에 맞춘 두 번째 시안: 01 요약, 02 경기 흐름, 03 라인전, 04 죽음 머리.
// 원칙: 판을 가른 것만 크게. 글을 여기저기 붙이지 않고 그림이 직접 말하게. 인터랙션은 안 보이던 걸 보여 줄 때만.
// 레퍼런스: Opta 매치 모멘텀(세로축을 말로), FT 주석 차트(글은 그래프 안 빈 곳에), 편집 인포그래픽의 단위 칸, 재무 리포트의 브리지 차트.
import { useMemo, useState } from 'react'
import { Section, Lede, Pending, Ci, Ii, Gi, signed, num, mmss, cx } from '../ui.jsx'
import { styleAxes, sec } from '../sections/Extra.jsx'
import { Radar } from './charts.jsx'
import './draft3.css'

const Xm = () => <i className="xm" aria-hidden="true" />
const toSec = (t) => { const [m, s] = String(t).split(':').map(Number); return m * 60 + (s || 0) }
const k1 = (v) => (Math.abs(v) >= 1000 ? `${v < 0 ? '−' : '+'}${(Math.abs(v) / 1000).toFixed(1)}k` : signed(v))
const gapTxt = (s) => (s >= 60 ? `${Math.floor(s / 60)}분 ${s % 60 ? `${s % 60}초` : ''}`.trim() : `${s}초`)
const fmt1 = (v) => (Number.isInteger(v) ? num(v) : v.toFixed(1))

// ================================================================ 01 요약
// 1줄: 요약 글 + 개선점(그대로). 2줄: 플레이 스타일 레이더 + 14분 숫자 표(03에 있던 점 그래프를 여기로 합침).
function StyleTable({ d, rows, axes, on, setOn }) {
  const axisOf = (label) => axes.findIndex((a) => (a.keys || []).includes(label))
  const pos = (v, avg) => Math.min(100, Math.max(0, (avg ? v / avg : 1) * 50))
  return (
    <div className="s3-tb">
      <div className="s3-tr s3-th">
        <span /><span className="s3-scale small num"><span>0</span><span>평균</span><span>2배</span></span>
        <span className="label">나</span><span className="label">평균</span><span className="label">{d.opp.n}</span>
      </div>
      {rows.map((r) => {
        const ai = axisOf(r.label)
        const good = (r.me - r.avg) * r.dir > 0
        return (
          <div key={r.label} className={cx('s3-tr', ai >= 0 && on === ai && 'on')}
            onPointerEnter={() => ai >= 0 && setOn(ai)} onPointerLeave={() => setOn(null)}>
            <span className="s3-k">{r.label}{r.dir < 0 && <small>적을수록 좋아요</small>}</span>
            <div className="s3-track">
              <i className="s3-avg" />
              <span className="s3-dot opp" style={{ left: `${pos(r.opp, r.avg)}%` }} />
              <span className={cx('s3-dot me', good ? 'good' : 'low')} style={{ left: `${pos(r.me, r.avg)}%` }} />
            </div>
            <b className="num">{fmt1(r.me)}</b>
            <span className="num muted">{fmt1(r.avg)}</span>
            <span className="num muted">{fmt1(r.opp)}</span>
          </div>
        )
      })}
    </div>
  )
}

export function Summary3({ fb, d }) {
  const S = d?.plus?.site
  const axes = styleAxes(S)
  const rows = S?.lane14?.rows
  const [on, setOn] = useState(null)
  return (
    <Section no="01">
      <div className="bento s3">
        {fb ? (
          <>
            <div className="cell s3-lede"><Xm /><Lede text={fb.summary} /></div>
            <div className="cell s3-fixes"><Xm />
              <p className="s3-goal"><span className="chip chip-pos">다음 판 목표</span><b>{fb.takeaway}</b></p>
              <ol className="fixes">
                {fb.keyFixes.map((f, i) => (
                  <li key={i} className="fix"><span className="fix-no">{i + 1}</span><div><h3>{f.title}</h3><p>{f.body}</p></div></li>
                ))}
              </ol>
            </div>
          </>
        ) : (
          <div className="cell s3-none"><Xm /><Pending text="이 판은 피드백 글이 아직 없어요. 아래 숫자 기록을 먼저 보여 드려요." /></div>
        )}
        {axes && rows ? (
          <>
            <div className="cell s3-radar"><Xm />
              <span className="label">플레이 스타일, 14분까지</span>
              <Radar axes={axes} plain on={on} />
              <p className="s3-key small"><i className="s3-key-avg" />점선이 {d.me.n} 평균(에메랄드 이상), 바깥 끝이 평균의 2배예요.</p>
            </div>
            <div className="cell s3-table"><Xm />
              <div className="s3-head"><span className="label">14분 숫자, 나와 평균과 {d.opp.n}</span>
                <span className="s3-lg"><i className="s3-lg-me" />나 <i className="s3-lg-opp" />{d.opp.n} <i className="s3-key-avg" />평균</span></div>
              <StyleTable d={d} rows={rows} axes={axes} on={on} setOn={setOn} />
            </div>
          </>
        ) : (
          <div className="cell s3-noaxes"><Xm /><p className="lab-empty">이 챔피언은 사이트 평균 숫자를 아직 가져오지 않아서 플레이 스타일을 그리지 못했어요.</p></div>
        )}
      </div>
    </Section>
  )
}

// ================================================================ 02 경기 흐름
// 왼쪽: 팀 골드 차이 한 장(세로축은 말로, 내 죽음과 킬은 선 위에, 주석은 빈 곳에).
// 오른쪽: 그 차이가 어느 라인에서 났는지(브리지). 그래프에 마우스를 올리면 그 분 기준으로 바뀌어요.
const ROLES = [['top', '탑'], ['jg', '정글'], ['mid', '미드'], ['bot', '바텀']]
const W = 1000, PL = 8, PR = 56, CH = 330

function useFlowGeo(d) {
  const f = d.flow, xmax = d.hero.durationSec / 60
  const pts = f.points.map((p) => [Math.min(p.min, xmax), p.team])
  const lo = Math.min(0, ...pts.map((p) => p[1])), hi = Math.max(0, ...pts.map((p) => p[1]))
  const span = Math.max(hi - lo, 4000)
  const vmax = hi + span * 0.08, vmin = lo - span * 0.08
  const X = (m) => PL + (W - PL - PR) * Math.min(m, xmax) / xmax
  const Y = (v) => CH * (vmax - v) / (vmax - vmin)
  // 분 사이 값은 앞뒤 분을 이어서 구해요(죽음, 킬 표시를 선 위에 올리려고).
  const at = (m) => {
    const i = pts.findIndex((p) => p[0] >= m)
    if (i <= 0) return pts[Math.max(0, i)][1]
    const [a, b] = [pts[i - 1], pts[i]]
    return a[1] + (b[1] - a[1]) * ((m - a[0]) / ((b[0] - a[0]) || 1))
  }
  // 오브젝트 줄: 겹치면 아래 줄로
  const objRow = [], last = []
  f.objs.forEach((o, i) => { const px = X(o.t / 60000); let r = 0; while (last[r] != null && px - last[r] < 20) r++; last[r] = px; objRow[i] = r })
  const OY = CH + 50
  const H = OY + Math.max(1, ...objRow.map((r) => r + 1)) * 21 + 4
  return { f, xmax, pts, X, Y, at, vmin, vmax, objRow, OY, H }
}

function FlowChart3({ d, fb, g, hov, setHov, onDeath }) {
  const { f, xmax, pts, X, Y, at, vmin, vmax, objRow, OY: oy, H } = g
  const D = d.deaths
  const P = (m, v) => `${X(m).toFixed(1)},${Y(v).toFixed(1)}`
  const line = pts.map(([m, v]) => P(m, v)).join(' ')
  const area = `${P(0, 0)} ${line} ${P(pts[pts.length - 1][0], 0)}`
  // 보조 눈금: 5k 단위, 오른쪽 끝에 작게
  const step = vmax - vmin > 16000 ? 5000 : 2500
  const grid = []
  for (let v = Math.ceil(vmin / step) * step; v <= vmax; v += step) if (v !== 0) grid.push(v)
  // 내 죽음: 선 위 번호 원. 붙어 있으면 위로 비켜 놓아요.
  const deaths = D.list.map((x) => ({ x, m: toSec(x.t) / 60 }))
  let lastX = -99, bump = 0
  deaths.forEach((o) => { const px = X(o.m); bump = px - lastX < 24 ? bump + 1 : 0; lastX = px; o.dy = bump * -26 })
  const kills = f.myKills.map((t) => t / 60000)
  // 내가 죽은 뒤 잃은 오브젝트만 진하게, 나머지는 흐리게
  const lostSet = new Set(D.list.flatMap((x) => x.lostAfter || []))
  const objs = f.objs.map((o) => ({ ...o, lost: lostSet.has(`${mmss(o.t)} ${o.name}`) }))
  const phases = d.plus?.phases || []
  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect()
    const y = (e.clientY - r.top) * H / r.height
    if (y > CH + 4) return setHov(null)
    const m = Math.round(((e.clientX - r.left) * W / r.width - PL) / (W - PL - PR) * xmax)
    setHov(m < 0 || m > Math.floor(xmax) ? null : m)
  }
  const hp = hov != null ? pts.find((p) => p[0] === hov) || pts[pts.length - 1] : null
  return (
    <svg className={cx('chart f3-chart', hp && 'is-hover')} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="팀 골드 차이 그래프"
      onPointerMove={onMove} onPointerLeave={() => setHov(null)}>
      <defs>
        <clipPath id="f3-pos"><rect x="0" y="0" width={W} height={Y(0).toFixed(1)} /></clipPath>
        <clipPath id="f3-neg"><rect x="0" y={Y(0).toFixed(1)} width={W} height={H} /></clipPath>
      </defs>
      {grid.map((v) => (
        <g key={v}>
          <line className="grid" x1={PL} x2={W - PR} y1={Y(v).toFixed(1)} y2={Y(v).toFixed(1)} />
          <text className="ax" x={W - PR + 8} y={(Y(v) + 4).toFixed(1)}>{k1(v)}</text>
        </g>
      ))}
      <polygon className="area-pos" points={area} clipPath="url(#f3-pos)" />
      <polygon className="area-neg" points={area} clipPath="url(#f3-neg)" />
      <line className="grid grid-zero" x1={PL} x2={W - PR} y1={Y(0).toFixed(1)} y2={Y(0).toFixed(1)} />
      <text className="ax" x={W - PR + 8} y={(Y(0) + 4).toFixed(1)}>0</text>
      {/* 세로축은 숫자 대신 말로(Opta 모멘텀 방식) */}
      <text className="f3-dir" x={PL + 6} y="16">우리 팀 앞섬 ↑</text>
      <text className="f3-dir" x={PL + 6} y={CH - 8}>상대 팀 앞섬 ↓</text>
      <polyline className="ln-team" points={line} pathLength="1" />
      {kills.map((m, i) => {
        const x = X(m), y = Y(at(m))
        return <rect key={i} className="f3-kill" x={(x - 4.5).toFixed(1)} y={(y - 4.5).toFixed(1)} width="9" height="9" transform={`rotate(45 ${x.toFixed(1)} ${y.toFixed(1)})`}><title>{mmss(f.myKills[i])} 내 킬</title></rect>
      })}
      {deaths.map(({ x, m, dy }) => {
        const px = X(m), py = Y(at(m))
        return (
          <g key={x.no} className="f3-death" onClick={() => onDeath(x.no)} role="button" tabIndex="0" aria-label={`${x.no}번째 죽음 ${x.t} 보기`}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onDeath(x.no)}>
            <title>{x.no}번째 죽음 {x.t}, {x.killer?.n}에게{x.lostAfter?.length ? `. 그 뒤 ${x.lostAfter.join(', ')}` : ''}</title>
            {dy !== 0 && <line className="f3-death-stem" x1={px} x2={px} y1={py} y2={py + dy + 10} />}
            <circle cx={px.toFixed(1)} cy={(py + dy).toFixed(1)} r="11" />
            <text x={px.toFixed(1)} y={(py + dy + 4.5).toFixed(1)} textAnchor="middle">{x.no}</text>
          </g>
        )
      })}
      <text className="f3-ob-k" x={PL} y={oy + 13}>오브젝트</text>
      {objs.map((o, i) => (
        <g key={i} className={cx('f3-ob', o.lost ? 'lost' : 'dim')}>
          <title>{mmss(o.t)} {o.name} ({o.ours ? '우리 팀' : '상대 팀'}){o.lost ? ', 내가 죽은 뒤 잃음' : ''}</title>
          <use className={o.ours ? 'ob-ours' : 'ob-theirs'} href={`#i-${o.icon}`} x={(X(o.t / 60000) - 9).toFixed(1)} y={oy + objRow[i] * 21} width="18" height="18" />
        </g>
      ))}
      {/* 시간 축: 5분 눈금 + 구간 이름(띠 없이 글자만) */}
      {[0, 5, 10, 15, 20, 25, 30, 35, 40].filter((m) => m <= xmax).map((m) => <text key={m} className="ax" x={X(m).toFixed(1)} y={CH + 16} textAnchor={m === 0 ? 'start' : 'middle'}>{m}:00</text>)}
      {phases.filter((p) => p.from < xmax).map((p, i) => {
        const x0 = X(p.from), x1 = X(p.to == null ? xmax : Math.min(p.to, xmax))
        return (
          <g key={p.name} className="f3-ph">
            {i > 0 && <line x1={x0} x2={x0} y1={CH + 22} y2={CH + 38} />}
            <text x={((x0 + x1) / 2).toFixed(1)} y={CH + 35} textAnchor="middle">{p.name} <tspan className="f3-ph-r">{p.to == null ? `${p.from}분~` : `${p.from}~${p.to}분`}</tspan></text>
          </g>
        )
      })}
      {hp && (
        <g className="hov" pointerEvents="none">
          <line className="f3-cross" x1={X(hp[0])} x2={X(hp[0])} y1="0" y2={CH} />
          <circle className="hov-dot" cx={X(hp[0]).toFixed(1)} cy={Y(hp[1]).toFixed(1)} r="5" />
        </g>
      )}
    </svg>
  )
}

// 변곡 주석: 그래프 안 빈 쪽(지는 판은 위, 이기는 판은 아래)에 괄호 + 골드 변화 + 피드백 한 줄. 겹치면 옆으로 밀어요.
function Notes({ g, fb }) {
  const { f, xmax, X, Y, at, H } = g
  const notes = (fb && fb.swings) || {}
  const keys = Object.keys(notes).map(Number)
  const noteOf = (w) => notes[String(w.m0)] ?? (() => { const k = keys.find((x) => x >= w.m0 && x < w.m1); return k != null ? notes[String(k)] : '' })()
  const pick = [...f.swings].sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta)).filter((w, i) => i === 0 || Math.abs(w.delta) >= 1500).slice(0, 3)
    .sort((a, b) => a.m0 - b.m0)
  const pct = (m) => (X(Math.min(m, xmax)) / W) * 100
  const MINW = 22, MAXW = 40
  const RIGHT = 100 - (PR / W) * 100, LEFT = (PL / W) * 100
  const items = pick.map((w) => ({ w, a: pct(w.m0), b: pct(w.m1), note: noteOf(w) }))
  // 가로 자리: 괄호 시작에 맞추되 그래프 안에 들어오게만 해요. 겹침은 세로 자리로 풀어요.
  items.forEach((it) => {
    it.width = Math.min(MAXW, Math.max(it.b - it.a, MINW))
    it.left = Math.min(Math.max(it.a, LEFT), RIGHT - it.width)
  })
  // 세로 자리: 글 칸이 걸치는 시간 동안 선이 지나가는 높이를 보고, 선 아래와 위 중 들어가는 곳에 놓아요(선을 가리지 않게).
  const toM = (pc) => Math.max(0, Math.min(xmax, ((pc / 100) * W - PL) / (W - PL - PR) * xmax))
  const NH = 90
  const placed = []
  const hits = (x0, x1, y) => placed.some((q) => x0 < q.x1 && q.x0 < x1 && Math.abs(q.y - y) < NH)
  items.forEach((it) => {
    const x0 = it.left, x1 = it.left + it.width
    const ys = []
    for (let m = toM(x0); m <= toM(x1) + 1e-9; m += 0.25) ys.push(Y(at(m)))
    const top = Math.min(...ys), bot = Math.max(...ys)
    const cands = []
    if (CH - bot - 12 >= NH) cands.push(bot + 12, CH - NH)
    if (top - 12 >= NH) cands.push(top - NH - 12, 18)
    if (!cands.length) cands.push(CH - bot > top ? bot + 12 : 18)
    it.y = cands.find((y) => !hits(x0, x1, y)) ?? cands[0]
    placed.push({ x0, x1, y: it.y })
  })
  return (
    <div className="f3-notes">
      {items.map((it, i) => (
        <div key={i} className="f3-note" style={{ top: `${(it.y / H) * 100}%` }}>
          <span className={cx('f3-br', it.w.delta > 0 ? 'up' : 'down')} style={{ left: `${it.a}%`, width: `${Math.max(it.b - it.a, 0.6)}%` }} />
          <div className="f3-note-t" style={{ left: `${it.left}%`, width: `${it.width}%` }}>
            <b className="num">{it.w.m0}~{Math.min(it.w.m1, Math.floor(xmax))}분 <span className={it.w.delta < 0 ? 'neg' : 'pos'}>{signed(it.w.delta)}</span></b>
            {it.note && <span>{it.note}</span>}
          </div>
        </div>
      ))}
    </div>
  )
}

// 브리지: 팀 골드 차이를 탑, 정글, 미드, 바텀(나와 서폿)으로 나눠요. 막대 길이 기준은 판 전체에서 같게 둬서, 분을 바꿔도 비교가 돼요.
function Split({ d, g, hov }) {
  const P = d.flow.points
  const have = P.some((p) => p.roles)
  const lowest = P.reduce((a, b) => (b.team < a.team ? b : a))
  const highest = P.reduce((a, b) => (b.team > a.team ? b : a))
  const base = d.flow.final < 0 ? lowest : highest
  const p = hov != null ? P.find((x) => x.min === hov) || base : base
  const maxAbs = useMemo(() => Math.max(1, ...P.flatMap((x) => (x.roles ? Object.values(x.roles) : [x.bot, x.team - x.bot]).map(Math.abs))), [P])
  if (!have) {
    return (
      <div className="f3-split">
        <span className="label">팀 골드 차이 중 바텀 2대2</span>
        <p className="f3-split-say">{p.min}분에 팀은 <b className={cx('num', p.team < 0 ? 'neg' : 'pos')}>{signed(p.team)}</b>, 바텀 2대2는 <b className={cx('num', p.bot < 0 ? 'neg' : 'pos')}>{signed(p.bot)}</b>였어요.</p>
      </div>
    )
  }
  const r = p.roles
  const w = (v) => `${(Math.abs(v) / maxAbs) * 50}%`
  // 한 줄 요약: 바텀이 어땠는지 + 가장 크게 벌어진(또는 앞선) 라인
  const losing = p.team < 0
  const others = ROLES.filter(([k]) => k !== 'bot').map(([k, n]) => [n, r[k]]).filter(([, v]) => (losing ? v <= -1000 : v >= 1000)).sort((a, b) => (losing ? a[1] - b[1] : b[1] - a[1]))
  const botTxt = Math.abs(r.bot) < 1000 ? `바텀은 ${signed(r.bot)}로 거의 같았고` : r.bot < 0 ? `바텀도 ${signed(r.bot)} 밀렸고` : `바텀은 ${signed(r.bot)} 앞섰고`
  // 이름 뒤 조사: 받침이 있으면 '과', 없으면 '와'. 셋 이상이면 쉼표로 이어요.
  const wa = (n) => ((n.charCodeAt(n.length - 1) - 0xac00) % 28 ? '과' : '와')
  const parts = others.map(([n, v]) => `${n}(${signed(v)})`)
  const joined = others.length === 2 ? `${parts[0]}${wa(others[0][0])} ${parts[1]}` : parts.join(', ')
  const restTxt = others.length ? `${joined}에서 ${losing ? '벌어졌어요' : '앞섰어요'}.` : '다른 라인은 크게 차이 나지 않았어요.'
  return (
    <div className="f3-split">
      <div className="s3-head"><span className="label">이 차이는 어느 라인에서 났나</span>
        <span className="f3-split-at num">{hov != null ? `${p.min}분` : `${p.min}분, 가장 ${losing ? '밀렸을' : '앞섰을'} 때`}</span></div>
      <ol className="f3-bars">
        {ROLES.map(([k, n]) => (
          <li key={k} className={cx(k === 'bot' && 'mine')}>
            <span className="f3-bk">{n}{k === 'bot' && <small>나와 서폿</small>}</span>
            <div className="f3-bt"><i className="f3-b0" /><span className={cx('f3-bf', r[k] < 0 ? 'neg' : 'pos')} style={{ width: w(r[k]), [r[k] < 0 ? 'right' : 'left']: '50%' }} /></div>
            <b className={cx('num', r[k] < 0 ? 'neg' : r[k] > 0 && 'pos')}>{signed(r[k])}</b>
          </li>
        ))}
        <li className="sum"><span className="f3-bk">팀 전체</span><span /><b className={cx('num', p.team < 0 ? 'neg' : 'pos')}>{signed(p.team)}</b></li>
      </ol>
      <p className="f3-split-say">{botTxt}, {restTxt}</p>
      <p className="small muted">그래프에 마우스를 올리면 그 분 기준으로 바뀌어요.</p>
    </div>
  )
}

export function Flow3({ d, fb, onDeath }) {
  const g = useFlowGeo(d)
  const [hov, setHov] = useState(null)
  const go = onDeath || ((no) => { const el = document.getElementById('s04'); if (el) el.scrollIntoView({ behavior: 'smooth' }); window.dispatchEvent(new CustomEvent('open-death', { detail: no })) })
  return (
    <Section no="02">
      <div className="bento f3">
        <div className="cell f3-main"><Xm />
          <div className="f3-top">
            <h3>팀 골드 차이 <span className="h-final">최종 <b className={cx('num', d.flow.final < 0 ? 'neg' : 'pos')}>{signed(d.flow.final)}</b></span></h3>
            <ul className="legend">
              <li><span className="lg f3-lg-death" />내 죽음(누르면 04에서 열려요)</li>
              <li><span className="lg f3-lg-kill" />내 킬</li>
              <li><span className="lg f3-lg-lost"><Gi name="tower" /></span>내가 죽은 뒤 잃은 오브젝트</li>
            </ul>
          </div>
          <div className="f3-wrap">
            <FlowChart3 d={d} fb={fb} g={g} hov={hov} setHov={setHov} onDeath={go} />
            {fb && fb.swings && <Notes g={g} fb={fb} />}
          </div>
        </div>
        <div className="cell f3-side"><Xm /><Split d={d} g={g} hov={hov} /></div>
      </div>
    </Section>
  )
}

// ================================================================ 03 라인전
// 크게: 라인전 글, 14분 맞라인 차이, 서폿 있을 때와 없을 때 CS. 작게(참고): 상성 승률, 레벨 선점, 첫 귀환.
function Diff14({ d }) {
  const r = (d.plus?.minute || []).find((x) => x.m === 14)
  const bk = d.lane.botAdcKills
  if (!r) return null
  const items = [['CS', r.cs], ['골드', r.gold], ['경험치', r.xp]]
  return (
    <div className="l3-nums">
      <span className="label">14분, {d.oppWith} 차이</span>
      <dl>
        {items.map(([k, [a, b]]) => (
          <div key={k}><dt>{k}<small className="num">{num(a)} : {num(b)}</small></dt><dd><b className={cx('num', a - b < 0 ? 'neg' : a - b > 0 && 'pos')}>{signed(a - b)}</b></dd></div>
        ))}
        {bk && <div><dt>바텀 원딜 킬<small>내가 잡음 : 내가 죽음</small></dt><dd><b className={cx('num', bk.opp > bk.me && 'pos')}>{bk.opp}</b><i>:</i><b className={cx('num', bk.me > 0 && 'death')}>{bk.me}</b></dd></div>}
      </dl>
    </div>
  )
}

function Support({ d }) {
  const s = d.lane.support
  if (!s) return <p className="lab-empty">서폿 위치를 알 수 없는 판이에요.</p>
  const gap = (s.without.me - s.without.opp) - (s.with.me - s.with.opp)
  const nIn = s.atBot.filter((c) => c.in).length
  return (
    <div className="l3-sup">
      <span className="label">서폿이 바텀에 있을 때와 없을 때, {s.atBot[0]?.min}~{s.atBot[s.atBot.length - 1]?.min}분</span>
      <div className="l3-sup-big">
        <div className="l3-sup-col in">
          <span className="l3-sup-k">서폿 있을 때 <small>{nIn}분</small></span>
          <div className="l3-sup-v"><b className="num">{s.with.me}</b><i>:</i><b className="num muted">{s.with.opp}</b></div>
        </div>
        <div className="l3-sup-col out">
          <span className="l3-sup-k">서폿 없을 때 <small>{s.atBot.length - nIn}분</small></span>
          <div className="l3-sup-v"><b className="num">{s.without.me}</b><i>:</i><b className="num muted">{s.without.opp}</b></div>
        </div>
      </div>
      <div className="sup-strip l3-strip" style={{ gridTemplateColumns: `repeat(${s.atBot.length}, 1fr)` }}>{s.atBot.map((c) => <span key={c.min} className={c.in ? 'in' : ''}>{c.min}</span>)}</div>
      <p className="l3-sup-say">CS는 {d.me.n} : {d.opp.n}이에요. 서폿이 없던 분에는 CS 차이가 <b className={cx('num', gap < 0 ? 'neg' : 'pos')}>{signed(gap)}</b> 더 {gap < 0 ? '벌어졌어요' : '좋았어요'}.</p>
    </div>
  )
}

function Refs({ d }) {
  const L = d.lane, P = d.plus, mu = P?.site?.matchup, main = mu && (mu.kr || mu.world)
  const stat = Object.fromEntries(((mu && mu.lv) || []).map((r) => [String(r.lv), r]))
  return (
    <div className="l3-refs">
      <span className="label">참고</span>
      <dl>
        {main && <div><dt>{d.me.n} vs {d.opp.n} 상성 승률</dt><dd><b className="num">{main.win.toFixed(1)}%</b> <span className="muted small">{mu.kr ? '한국' : '전 세계'} {num(main.games)}판</span></dd></div>}
        {L.levels.map((v) => {
          const df = toSec(v.opp) - toSec(v.me), st = stat[v.lv]
          return (
            <div key={v.lv}><dt>{v.lv}레벨</dt>
              <dd>{df === 0 ? '같이 찍음' : <><b>{df > 0 ? d.me.n : d.opp.n}</b> {gapTxt(Math.abs(df))} 먼저</>}
                {st && <span className="muted small"> (보통 {st.first}% 판에서 {d.me.n}가 먼저)</span>}</dd></div>
          )
        })}
        {P?.back && <div><dt>첫 귀환</dt><dd>나 <span className="num">{sec(P.back.me.t)}</span>, {d.opp.n} <span className="num">{sec(P.back.opp.t)}</span>
          <span className="l3-back-it">{P.back.me.items.map((it, i) => <Ii key={i} it={it} size="xs" />)}</span></dd></div>}
      </dl>
    </div>
  )
}

export function Lane3({ d, fb }) {
  return (
    <Section no="03">
      <div className="bento l3">
        <div className="cell l3-lede"><Xm />
          {fb && fb.laneText ? <p className="l3-lede-t">{fb.laneText}</p> : <Pending text="라인전 글은 피드백 글을 쓰면 채워져요." />}
        </div>
        <div className="cell l3-numcell"><Xm /><Diff14 d={d} /></div>
        <div className="cell l3-supcell"><Xm /><Support d={d} /></div>
        <div className="cell l3-refcell"><Xm /><Refs d={d} /></div>
      </div>
    </Section>
  )
}

// ================================================================ 04 머리: 죽음 유형 표
// 열 = 죽음(번호, 시각), 줄 = 유형. 칠한 칸만 세면 그 유형의 개수예요. 칸이나 번호를 누르면 아래에서 그 죽음이 열려요.
export function DeathHead({ D, fb, keyNos, onOpen }) {
  const [col, setCol] = useState(null)
  const L = D.list
  const tags = Object.entries(D.tagCount || {}).sort((a, b) => b[1] - a[1]).map(([t]) => t)
  const rows = [
    ...tags.map((t) => [t, (x) => (x.tags || []).includes(t)]),
    ['혼자 있다가 죽음', (x) => !(x.alliesNear || []).length],
    ['죽은 뒤 손해 있음', (x) => (x.lostAfter || []).length > 0],
  ].map(([name, fn]) => ({ name, hit: L.map(fn) })).filter((r) => r.hit.some(Boolean))
  const p = fb && fb.deathPattern
  const lost = L.filter((x) => (x.lostAfter || []).length).length
  return (
    <div className="bento d4h">
      <div className="cell d4h-n"><Xm />
        <span className="label">죽음</span>
        <div className="d4h-big num">{L.length}<small>번</small></div>
        <p className="d4h-say">{lost > 0 ? <>그중 <b className="death num">{lost}번</b>은 죽은 뒤 포탑이나 오브젝트를 잃었어요.</> : '죽은 뒤 잃은 포탑이나 오브젝트는 없었어요.'}</p>
        {p && <div className="d4h-pat"><span className="chip chip-bad">{p.tag}</span><b>{p.title}</b>{p.next && <p>{p.next}</p>}</div>}
      </div>
      <div className="cell d4h-mx"><Xm />
        <div className="d4h-grid" style={{ gridTemplateColumns: `minmax(170px, 1.4fr) repeat(${L.length}, minmax(40px, 1fr)) 56px` }} onPointerLeave={() => setCol(null)}>
          <span />
          {L.map((x, i) => (
            <button key={x.t} type="button" className={cx('d4h-col', col === i && 'on')} onPointerEnter={() => setCol(i)} onClick={() => onOpen(x.no)} aria-label={`${x.no}번째 죽음 ${x.t} 보기`}>
              <span className={cx('dno', keyNos.has(x.no) && 'key')}>{x.no}</span><span className="num">{x.t}</span>
            </button>
          ))}
          <span className="label d4h-sum-h">횟수</span>
          {rows.map((r) => (
            <div key={r.name} className={cx('d4h-row', p && p.tag === r.name && 'pat')} style={{ display: 'contents' }}>
              <span className="d4h-k">{r.name}</span>
              {r.hit.map((h, i) => (
                <button key={i} type="button" tabIndex="-1" className={cx('d4h-c', h && 'hit', col === i && 'on')} onPointerEnter={() => setCol(i)} onClick={() => onOpen(L[i].no)} aria-hidden="true"><i /></button>
              ))}
              <b className="num d4h-sum">{r.hit.filter(Boolean).length}</b>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
