import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Section, Ci, LostList, Pi, MAP_IMG, src, num, signed, cx } from '../ui.jsx'

// 04 죽음 (11-20 시안 5)
// 기본: 왼쪽 지도 + 오른쪽 죽음 목록. 죽음을 고르면 목록 위에 죽음 정보 칸(근처 챔피언, 골드, 스펠, 합류한 적, 받은 피해, 상황과 근거).
// 리플레이: 왼쪽 미니맵 리플레이와 그 아래 숫자 칸, 오른쪽 위 죽음 번호 칸(교전 시간, 킬과 어시스트 초상화, 교전 보기),
// 그 아래 왼쪽은 받은 피해(롤 사망 정보처럼), 오른쪽은 상황과 근거.
// 가운뎃점(·)은 화면 글자에 쓰지 않아요(사용자 요청).
// 죽음 번호: 주요 죽음(피드백의 keyDeaths) = 주황 칠, 나머지 = 흰 바탕 + 주황 테두리 (11-20 시안 5 방식으로 되돌림, 새 방식은 나중에 다시 정해요)

const ms = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`
const SPELL_WORD = { held: '미사용', used_before: '사용', already_down: '없음', uncertain: '판단 보류' }
const killers = (x) => [x.killer, ...x.assists].map((c) => c.n).join(', ')
// 죽은 뒤 손해: 정확한 시각(29:38 등)은 빼고 무엇을 잃었는지만
const noTime = (lost) => lost.map((v) => v.replace(/^\d+:\d{2}\s*/, ''))

// ---------- 기본: 모든 죽음 번호와 킬 ----------
function OverviewMap({ m, active, onPick, keyNos }) {
  const S = m.size
  return (
    <svg className={cx('map', 'map-deaths', active != null && 'has-active')} viewBox={`0 0 ${S} ${S}`} role="img" aria-label="내가 죽은 곳과 킬한 곳">
      <image href={MAP_IMG} x="0" y="0" width={S} height={S} />
      {m.kills.map((p, i) => (
        <rect key={`k${i}`} className={p.solid ? 'mp-kill' : 'mp-assist'} x={p.x - 6.5} y={p.y - 6.5} width="13" height="13"
          transform={`rotate(45 ${p.x} ${p.y})`}><title>{p.t} {p.solid ? '킬' : '어시스트'}</title></rect>
      ))}
      {m.deaths.map((p) => (
        <g key={p.no} className={cx('mp-d', active === p.no && 'on', keyNos.has(p.no) && 'key')} onClick={() => onPick(p.no)} role="button" aria-label={`${p.no}번째 죽음 ${p.t}${keyNos.has(p.no) ? ' 주요 죽음' : ''}`}>
          <title>{p.t} {p.no}번째 죽음{keyNos.has(p.no) ? ' (주요 죽음)' : ''}</title>
          {active === p.no && <circle className="mp-sel" cx={p.x} cy={p.y} r="21" />}
          {/* 고르지 않은 죽음은 흐리게 그리되, 아래에 불투명한 받침 원을 깔아서 킬 표시가 비치지 않게 해요 */}
          <circle className="mp-back" cx={p.x} cy={p.y} r="15.25" />
          <g className="mp-body">
            <circle className="mp-death" cx={p.x} cy={p.y} r="14" />
            <text className="mp-num" x={p.x} y={p.y + 5} textAnchor="middle">{p.no}</text>
          </g>
        </g>
      ))}
    </svg>
  )
}

// ---------- 리플레이 ----------
function useTracks(rp) {
  return useMemo(() => {
    if (!rp) return null
    const L = rp.len + 3
    const X = [], Y = []
    rp.tracks.forEach((enc) => {
      const xs = new Float32Array(L).fill(NaN), ys = new Float32Array(L).fill(NaN)
      let t = 0, x = 0, y = 0
      for (let k = 0; k < enc.length; k += 3) {
        t += enc[k]; x += enc[k + 1]; y += enc[k + 2]
        if (t < L) { xs[t] = x / 10; ys[t] = y / 10 }
      }
      X.push(xs); Y.push(ys)
    })
    return { X, Y }
  }, [rp])
}

function posAt(T, i, t) {
  const s = Math.floor(t), f = t - s
  const ax = T.X[i][s], ay = T.Y[i][s]
  if (Number.isNaN(ax)) return null
  const bx = T.X[i][s + 1], by = T.Y[i][s + 1]
  if (Number.isNaN(bx)) return [ax, ay]
  return [ax + (bx - ax) * f, ay + (by - ay) * f]
}

function Label({ x, y, S, text, tone, stack = 0 }) {
  // 점 위쪽에 이름표를 달고 선으로 이어요. 지도 밖으로 나가지 않게 자리를 조정해요.
  // 글자 폭을 실제로 재서 좌우 여백을 8로 똑같이 맞춰요(한글과 숫자 폭이 달라서 글자 수로 어림하면 오른쪽이 넓어졌어요).
  const tref = useRef(null)
  const [tw, setTw] = useState(text.length * 9)
  useLayoutEffect(() => { if (tref.current) setTw(tref.current.getComputedTextLength()) }, [text])
  const w = Math.ceil(tw) + 16, h = 24
  const up = y > 60
  const lx = Math.min(Math.max(x - w / 2, 4), S - w - 4)
  const ly = up ? y - 52 - stack * 28 : y + 28 + stack * 28
  return (
    <g className={cx('rp-label', tone && `rp-label-${tone}`)}>
      <line x1={x} y1={y + (up ? -14 : 14)} x2={Math.min(Math.max(x, lx + 6), lx + w - 6)} y2={up ? ly + h : ly} />
      <rect x={lx} y={ly} width={w} height={h} />
      <text ref={tref} x={lx + 8} y={ly + 16.5}>{text}</text>
    </g>
  )
}

// 플레이어 버튼 그림 (각진 도형)
const PI = {
  play: <path d="M7 4.5 L19 12 L7 19.5 Z" />,
  pause: <><rect x="6" y="4.5" width="4" height="15" /><rect x="14" y="4.5" width="4" height="15" /></>,
  back: <><path d="M11 6 L4 12 L11 18 Z" /><path d="M20 6 L13 12 L20 18 Z" /></>,
  fwd: <><path d="M4 6 L11 12 L4 18 Z" /><path d="M13 6 L20 12 L13 18 Z" /></>,
  x: <path d="M5 5 L19 19 M19 5 L5 19" fill="none" stroke="currentColor" strokeWidth="2.2" />,
}
const Icon = ({ n }) => <svg className="rp-i" viewBox="0 0 24 24" aria-hidden="true">{PI[n]}</svg>
const SPEEDS = [0.5, 1, 2, 4, 8]
const OBJ_NAME = { dragon: '드래곤', baron: '바론', herald: '전령', grub: '공허 유충', tower: '포탑', inhib: '억제기' }

// 시간 막대: 위 줄 = 우리 팀 일, 아래 줄 = 상대 팀 일, 빨간 칸 = 내 죽음(교전 구간). 마우스를 올리면 그 시각과 일어난 일.
// 묶는 기준은 교전이에요. 킬과 오브젝트가 앞 일과 CHAIN초 안에 이어지면 같은 교전으로 보고 표시 하나로 묶어요(2개 이상이면 개수).
// 교전끼리 너무 가까워 표시가 겹치면, 뒤 표시를 MIN_PX만큼 오른쪽으로 밀어서 그려요(누르면 원래 시각으로 가요).
const CHAIN = 15
const MIN_PX = 24
function fightGroups(marks) {
  let id = -1, prev = -1e9
  const tagged = marks.map((m) => { if (m.t - prev > CHAIN) id += 1; prev = m.t; return { ...m, fid: id } })
  const byRow = (row) => {
    const out = []
    tagged.filter((m) => m.row === row).forEach((m) => {
      const g = out[out.length - 1]
      if (g && g.fid === m.fid) g.items.push(m)
      else out.push({ t: m.t, fid: m.fid, row, us: m.us, items: [m] })
    })
    return out.map((g) => {
      const obj = g.items.find((m) => m.k !== 'kill')
      return { ...g, k: obj ? 'obj' : 'kill', g: obj && obj.g, what: g.items.map((m) => `${ms(m.t)} ${m.what}`).join('\n') }
    })
  }
  return { us: byRow('us'), them: byRow('them') }
}
// 표시 자리(px). 겹치면 오른쪽으로 밀어요.
function spread(groups, L, w) {
  let last = -1e9
  return groups.map((g) => { const x = Math.max(g.t / L * w, last + MIN_PX); last = x; return { ...g, x } })
}

function Timeline({ rp, t, scene, fights, onSeek, onScrub }) {
  const ref = useRef(null)
  const [hover, setHover] = useState(null)
  const [w, setW] = useState(1400)
  useEffect(() => {
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width || 1400))
    ro.observe(ref.current)
    return () => ro.disconnect()
  }, [])
  const C = rp.champs
  const L = rp.len
  const win = 12 * L / w   // 마우스 근처로 보는 시간 폭(초): 좌우 12px
  const pct = (v) => `${(v / L * 100).toFixed(3)}%`
  const toT = (clientX) => {
    const r = ref.current.getBoundingClientRect()
    return Math.min(Math.max((clientX - r.left) / r.width, 0), 1) * L
  }
  const marks = useMemo(() => rp.events.map((e) => {
    if (e.k === 'kill') {
      const me = C[e.who] && C[e.who].me
      const by = e.by != null && C[e.by] ? C[e.by].n : '처형'
      return { ...e, row: me ? 'me' : e.us ? 'us' : 'them', what: me ? `사망 (${by})` : `${by} → ${C[e.who].n} 킬` }
    }
    return { ...e, row: e.us ? 'us' : 'them', what: `${e.us ? '우리' : '상대'} ${OBJ_NAME[e.g] || ''}` }
  }).sort((a, b) => a.t - b.t), [rp])
  const fg = useMemo(() => fightGroups(marks), [marks])
  const groups = useMemo(() => ({ us: spread(fg.us, L, w), them: spread(fg.them, L, w) }), [fg, L, w])
  const near = hover != null ? marks.filter((m) => Math.abs(m.t - hover) <= win / 2).slice(0, 6) : []
  const drag = (ev) => {
    ev.preventDefault()
    ref.current.setPointerCapture(ev.pointerId)
    onScrub(toT(ev.clientX))
    const move = (e2) => onScrub(toT(e2.clientX))
    const up = () => { ref.current.removeEventListener('pointermove', move); ref.current.removeEventListener('pointerup', up) }
    ref.current.addEventListener('pointermove', move)
    ref.current.addEventListener('pointerup', up)
  }
  const key = (e) => {
    const d = { ArrowLeft: -5, ArrowRight: 5, PageDown: -30, PageUp: 30 }[e.key]
    if (d) { e.preventDefault(); onSeek(t + d) }
  }
  return (
    <div className="tl" ref={ref} role="slider" tabIndex={0} aria-label="재생 위치" aria-valuemin={0} aria-valuemax={L}
      aria-valuenow={Math.floor(t)} aria-valuetext={ms(t)} onKeyDown={key} onPointerDown={drag}
      onPointerMove={(e) => setHover(toT(e.clientX))} onPointerLeave={() => setHover(null)}>
      <div className="tl-row tl-us">
        {groups.us.map((m, i) => <Mark key={i} m={m} left={`${m.x}px`} onSeek={onSeek} />)}
      </div>
      <div className="tl-track">
        {fights.map((f, i) => <span key={i} className={cx('tl-fight', scene && scene.to === f.to && 'on')} style={{ left: pct(f.from), width: `max(3px, ${pct(f.to - f.from)})` }} />)}
        <span className="tl-done" style={{ width: pct(t) }} />
        {marks.filter((m) => m.row === 'me').map((m, i) => <span key={i} className="tl-death" style={{ left: pct(m.t) }} />)}
      </div>
      <div className="tl-row tl-them">
        {groups.them.map((m, i) => <Mark key={i} m={m} left={`${m.x}px`} onSeek={onSeek} />)}
      </div>
      {/* 재생 위치: 선과 머리 네모를 한 덩어리로 그려서 함께 움직여요 */}
      <span className="tl-head" style={{ left: pct(t) }} aria-hidden="true"><i /></span>
      {hover != null && (
        <div className="tl-tip" style={{ left: pct(hover) }}>
          <b>{ms(hover)}</b>
          {near.map((m, i) => <span key={i} className={cx(m.row === 'me' && 'red')}>{ms(m.t)} {m.what}</span>)}
        </div>
      )}
    </div>
  )
}

function Mark({ m, left, onSeek }) {
  const go = (e) => { e.stopPropagation(); onSeek(Math.max(m.t - 5, 0)) }
  const n = m.items.length
  return (
    <span className={cx('tl-m', m.us && 'us')} style={{ left }} onPointerDown={(e) => e.stopPropagation()} onClick={go} title={m.what}>
      {m.k === 'kill'
        ? <i className="tl-kill" />
        : <svg className="tl-obj" viewBox="0 0 24 24" aria-hidden="true"><use href={`#i-${m.g}`} /></svg>}
      {n > 1 && <small className="tl-n">{n}</small>}
    </span>
  )
}

// 지도 위 재생 막대(유튜브처럼): 지도 아래쪽에 마우스를 올리면 나와요. 교전 구간만 연한 주황으로, 오브젝트는 표시하지 않아요.
function MiniBar({ L, t, fights, show, onScrub, onDrag }) {
  const ref = useRef(null)
  const [hover, setHover] = useState(null)
  const toT = (cx_) => {
    const r = ref.current.getBoundingClientRect()
    return Math.min(Math.max((cx_ - r.left) / r.width, 0), 1) * L
  }
  const pct = (v) => `${(v / L * 100).toFixed(3)}%`
  const down = (ev) => {
    ev.preventDefault(); ev.stopPropagation()
    ref.current.setPointerCapture(ev.pointerId)
    onDrag(true); onScrub(toT(ev.clientX))
    const move = (e2) => { onScrub(toT(e2.clientX)); setHover(toT(e2.clientX)) }
    const up = () => { onDrag(false); ref.current.removeEventListener('pointermove', move); ref.current.removeEventListener('pointerup', up) }
    ref.current.addEventListener('pointermove', move)
    ref.current.addEventListener('pointerup', up)
  }
  return (
    <div className={cx('rp-mini', show && 'on')} onClick={(e) => e.stopPropagation()}>
      <div className="rp-mini-hit" ref={ref} onPointerDown={down}
        onPointerMove={(e) => setHover(toT(e.clientX))} onPointerLeave={() => setHover(null)}>
        <div className="rp-mini-track">
          <span className="rp-mini-done" style={{ width: pct(t) }} />
          {fights.map((f, i) => <span key={i} className="rp-mini-fight" style={{ left: pct(f.from), width: `max(3px, ${pct(f.to - f.from)})` }} />)}
        </div>
        <span className="rp-mini-head" style={{ left: pct(t) }} />
        {hover != null && <span className="rp-mini-tip" style={{ left: pct(hover) }}>{ms(hover)}</span>}
      </div>
    </div>
  )
}

// side(playScene)와 under를 받아서, 지도 오른쪽과 지도 아래에 그려요. 교전 보기 버튼은 side 안(죽음 번호 칸)에 있어요.
function Replay({ rp, scene, jump, onTime, joins, vision, setVision, fights, side, under }) {
  const T = useTracks(rp)
  const S = rp.size
  const [t, setT] = useState(scene ? Math.max(scene.from - 5, 0) : 0)
  const [play, setPlay] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [flash, setFlash] = useState(null)
  const [nearBottom, setNearBottom] = useState(false)   // 지도 아래쪽에 마우스가 있음
  const [dragging, setDragging] = useState(false)
  const stopAt = useRef(null)
  const raf = useRef(0)
  const last = useRef(0)

  // 교전 보기: 교전 5초 전부터 재생하고, 죽은 뒤 3초에 멈춰요.
  const playScene = () => {
    if (!scene) return
    setT(Math.max(scene.from - 5, 0)); stopAt.current = scene.to + 3; setPlay(true)
  }
  // 죽음 바로가기를 누르면 교전 5초 전으로만 옮겨요(자동 재생은 하지 않음).
  // 재생 막대를 움직여서 보는 죽음이 바뀔 때는 옮기지 않아요(jump는 바로가기를 누를 때만 바뀌어요, 11-22).
  const fromJump = useRef(true)
  useEffect(() => { if (scene) { fromJump.current = true; setPlay(false); stopAt.current = null; setT(Math.max(scene.from - 5, 0)) } }, [jump])
  // 재생하거나 막대를 움직이면 지금 시간을 알려서, 그 시간에 맞는 죽음 정보를 보여 줘요.
  useEffect(() => {
    if (fromJump.current) { fromJump.current = false; return }
    if (onTime) onTime(t)
  }, [t])

  useEffect(() => {
    if (!play) return
    last.current = performance.now()
    const step = (now) => {
      const dt = (now - last.current) / 1000
      last.current = now
      setT((v) => {
        let n = v + dt * speed
        if (stopAt.current != null && v < stopAt.current && n >= stopAt.current) { n = stopAt.current; setPlay(false); stopAt.current = null }
        if (n >= rp.len) { n = rp.len; setPlay(false) }
        return n
      })
      raf.current = requestAnimationFrame(step)
    }
    raf.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf.current)
  }, [play, speed, rp.len])

  const seek = (v) => { stopAt.current = null; setT(Math.min(Math.max(v, 0), rp.len)) }
  const toggle = () => {
    stopAt.current = null
    if (!play && t >= rp.len) setT(0)
    setFlash(play ? 'pause' : 'play'); setTimeout(() => setFlash(null), 450)
    setPlay(!play)
  }
  const si = SPEEDS.indexOf(speed)
  const keys = (e) => {
    if (e.target.closest('.tl, .rx-side, button, input')) return
    if (e.key === ' ' || e.key === 'k') { e.preventDefault(); toggle() }
    else if (e.key === 'ArrowLeft' || e.key === 'j') { e.preventDefault(); seek(t - 10) }
    else if (e.key === 'ArrowRight' || e.key === 'l') { e.preventDefault(); seek(t + 10) }
  }

  // 죽은 챔피언: 킬 시각부터 부활할 때까지(위치가 죽은 자리에서 처음 움직이는 때) X로 그려요.
  const deadList = useMemo(() => rp.events.filter((e) => e.k === 'kill').map((e) => {
    const xs = T.X[e.who], ys = T.Y[e.who], N = xs.length
    let base = null
    for (let k = e.t; k < Math.min(e.t + 3, N); k++) if (!Number.isNaN(xs[k])) { base = [xs[k], ys[k]]; break }
    let end = e.t + 60
    for (let k = e.t + 2; k < Math.min(e.t + 150, N); k++) {
      if (Number.isNaN(xs[k])) continue
      if (!base || (xs[k] - base[0]) ** 2 + (ys[k] - base[1]) ** 2 > 225) { end = k; break }
    }
    return { who: e.who, t: e.t, end, x: e.x / 10, y: e.y / 10 }
  }), [rp, T])
  const C = rp.champs
  const dead = deadList.filter((d) => t >= d.t && t < d.end)
  const deadSet = new Set(dead.map((d) => d.who))
  const pos = C.map((_, i) => posAt(T, i, t))
  // 추정 시야: 살아 있는 우리 팀 주변, 켜져 있는 우리 와드, 남아 있는 우리 포탑 (벽, 수풀은 계산하지 않아요)
  const src_ = []
  C.forEach((c, i) => { if (c.us && pos[i]) src_.push([pos[i][0], pos[i][1], rp.sight / 10]) })
  rp.wards.forEach(([a, b, x, y, r]) => { if (t >= a && t < b) src_.push([x / 10, y / 10, r / 10]) })
  rp.turrets.forEach(([x, y, end]) => { if (t < end) src_.push([x / 10, y / 10, rp.sight / 10]) })
  ;(rp.base || []).forEach(([x, y, r]) => src_.push([x / 10, y / 10, r / 10]))   // 우물과 넥서스 쪽은 항상 보여요
  const seen = (p) => src_.some(([x, y, r]) => (p[0] - x) ** 2 + (p[1] - y) ** 2 <= r * r)

  const evNow = rp.events.filter((e) => e.k !== 'kill' && t >= e.t && t < e.t + 4)
  // 이름표: 고른 죽음만이 아니라 모든 내 죽음에서 똑같이 떠요.
  // 접근 = 교전 구간 안에서 적이 1000 거리 밖에서 들어온 순간(처음부터 가까이 있던 적은 접근이 아니라서 띄우지 않아요). 사망 = 항상.
  const labels = []
  joins.forEach((j) => {
    if (t >= j.t && t < j.t + 3 && pos[j.who] && !deadSet.has(j.who)) labels.push({ key: `j${j.t}-${j.who}`, at: pos[j.who], text: `${C[j.who].n} 접근 ${ms(j.t)}`, ring: j.who })
  })
  const meI = C.findIndex((c) => c.me)
  deadList.filter((d) => d.who === meI && t >= d.t && t < d.t + 4).forEach((d) => labels.push({ key: `d${d.t}`, at: [d.x, d.y], text: `사망 ${ms(d.t)}`, tone: 'red' }))

  const rings = new Set(labels.map((l) => l.ring).filter((r) => r != null))
  const inFight = scene && t >= scene.from && t <= scene.to

  return (
    <div className="rx" tabIndex={-1} onKeyDown={keys}>
      <div className="d3-main">
        <div className="d3-stage">
          <div className="rp" tabIndex={0} aria-label="리플레이. 스페이스로 재생과 멈춤, 화살표로 10초 이동">
            <div className="rp-screen" onClick={toggle}
              onPointerMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); setNearBottom(e.clientY > r.bottom - 72) }}
              onPointerLeave={() => setNearBottom(false)}>
              <svg className="map rp-map" viewBox={`0 0 ${S} ${S}`} role="img" aria-label={`리플레이 ${ms(t)}`}>
                <defs>
                  <clipPath id="rp-tk"><circle r="11" /></clipPath>
                  <clipPath id="rp-tk-me"><circle r="13" /></clipPath>
                  {vision && (
                    <mask id="rp-vis">
                      <rect width={S} height={S} fill="#fff" />
                      {src_.map(([x, y, r], i) => <circle key={i} cx={x} cy={y} r={r} fill="#000" />)}
                    </mask>
                  )}
                </defs>
                <image href={MAP_IMG} x="0" y="0" width={S} height={S} />
                {vision && <rect width={S} height={S} className="rp-fog" mask="url(#rp-vis)" />}
                {vision && rp.wards.filter(([a, b]) => t >= a && t < b).map(([, , x, y], i) => <circle key={`w${i}`} className="rp-ward" cx={x / 10} cy={y / 10} r="2.5" />)}
                {/* 죽은 자리 X는 챔피언 초상화 아래에 그려요 */}
                {dead.map((d) => {
                  const c = C[d.who], r = c.me ? 9 : 7.5
                  return (
                    <path key={`x${d.who}`} className={cx('rp-dead', c.me ? 'me' : c.us ? 'us' : 'them')}
                      d={`M${d.x - r} ${d.y - r}L${d.x + r} ${d.y + r}M${d.x + r} ${d.y - r}L${d.x - r} ${d.y + r}`}><title>{c.n} 사망</title></path>
                  )
                })}
                {evNow.map((e, i) => <use key={i} href={`#i-${e.g}`} x={e.x / 10 - 10} y={e.y / 10 - 10} width="20" height="20" className={e.us ? 'rp-obj-us' : 'rp-obj-them'} />)}
                {C.map((c, i) => {
                  const p = pos[i]
                  if (!p || deadSet.has(i)) return null
                  const r = c.me ? 13 : 11
                  const out = vision && !c.us && !seen(p)
                  return (
                    <g key={i} transform={`translate(${p[0].toFixed(1)} ${p[1].toFixed(1)})`} className={cx('rp-tok', c.us ? 'us' : 'them', c.me && 'me', out && 'out')}>
                      {rings.has(i) && <circle className="rp-pulse" r={r + 8} />}
                      <image href={src(c.img)} x={-r} y={-r} width={r * 2} height={r * 2} clipPath={`url(#rp-tk${c.me ? '-me' : ''})`} />
                      <circle className="rp-ring" r={r} />
                      <title>{c.n}{out ? ' (시야 밖)' : ''}</title>
                    </g>
                  )
                })}
                {labels.map((l, k) => {
                  // 가까운 이름표끼리 겹치지 않게, 앞 이름표 근처면 한 칸(28)씩 더 띄워요.
                  const n = labels.slice(0, k).filter((o) => Math.abs(o.at[0] - l.at[0]) < 140 && Math.abs(o.at[1] - l.at[1]) < 40).length
                  return <Label key={l.key} x={l.at[0]} y={l.at[1]} S={S} text={l.text} tone={l.tone} stack={n} />
                })}
              </svg>
              {inFight && <span className="rp-tag">교전 중</span>}
              {flash && <span className="rp-flash"><Icon n={flash} /></span>}
              <MiniBar L={rp.len} t={t} fights={fights} show={nearBottom || dragging}
                onDrag={(v) => { setDragging(v); if (v) setPlay(false) }} onScrub={seek} />
            </div>
            {/* 재생 조작: 지도 바로 아래 한 줄 */}
            <div className="rp-ctrl">
              <button type="button" className="rp-b" onClick={() => seek(t - 10)} title="10초 뒤로 (←)"><Icon n="back" /></button>
              <button type="button" className="rp-b rp-main" onClick={toggle} title={play ? '멈춤 (스페이스)' : '재생 (스페이스)'}><Icon n={play ? 'pause' : 'play'} /></button>
              <button type="button" className="rp-b" onClick={() => seek(t + 10)} title="10초 앞으로 (→)"><Icon n="fwd" /></button>
              <span className="rp-time"><b>{ms(t)}</b> / {ms(rp.len)}</span>
              <label className="rp-vis">
                <input type="checkbox" checked={vision} onChange={(e) => setVision(e.target.checked)} />
                <span className="rp-box" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="M3 8.5 L6.5 12 L13 4.5" /></svg></span>
                시야
              </label>
              <span className="rp-speed" role="group" aria-label="재생 속도">
                <button type="button" disabled={si <= 0} onClick={() => setSpeed(SPEEDS[si - 1])} aria-label="느리게">−</button>
                <b>{speed}×</b>
                <button type="button" disabled={si >= SPEEDS.length - 1} onClick={() => setSpeed(SPEEDS[si + 1])} aria-label="빠르게">+</button>
              </span>
            </div>
          </div>
          {under}
        </div>
        <div className="d3-side rx-side">{side(playScene)}</div>
      </div>
      <div className="rx-dock">
        <Timeline rp={rp} t={t} scene={scene} fights={fights} onSeek={seek} onScrub={(v) => { setPlay(false); seek(v) }} />
      </div>
    </div>
  )
}

// ---------- 기본: 죽음 목록 한 줄 ----------
function Row({ x, note, isKey, on, onPick }) {
  // 줄마다 개선점 한 줄. 개선점이 없는 죽음(주요 죽음이 아닌 것)은 상황 한 줄을 회색 제목으로 보여요.
  const line = note && (note.next ? ['개선점', note.next] : note.what ? ['상황', note.what] : null)
  return (
    <li>
      <button type="button" className={cx('d3-row', on && 'on')} onClick={onPick} aria-pressed={on}>
        <span className={cx('dno', isKey && 'key')} title={isKey ? '주요 죽음' : undefined}>{x.no}</span>
        <time>{x.t}</time>
        <span className="d3-kill"><Ci c={x.killer} size="sm" />{x.assists.map((a, i) => <Ci key={i} c={a} size="xs" />)}</span>
        <span className="d3-lost">{x.lostAfter.length > 0 ? <LostList lost={noTime(x.lostAfter)} /> : <span className="muted">손해 없음</span>}</span>
        {line && <span className={cx('d3-next', line[0] === '상황' && 'is-what')}><b>{line[0]}</b>{line[1]}</span>}
      </button>
    </li>
  )
}

// ---------- 기본: 죽음 정보 칸 (예전 죽음 정보와 같은 내용) ----------
function DamageBar({ dmg }) {
  const tot = dmg.reduce((s, x) => s + x.v, 0) || 1
  return (
    <div className="dmg">
      <div className="dmg-bar">
        {dmg.map((x, i) => <span key={i} className={`dmg-seg dmg-${i}`} style={{ width: `${(x.v / tot * 100).toFixed(1)}%` }} title={`${x.who.n} ${num(x.v)}`} />)}
      </div>
      <ul className="dmg-list">
        {dmg.map((x, i) => <li key={i}><Ci c={x.who} size="xs" title={x.who.n} /><span>{x.who.n}</span><b>{num(x.v)}</b></li>)}
      </ul>
    </div>
  )
}

// 고른 죽음 칸. 위 = 번호와 누구에게 죽음, 그 아래 한 줄 = 숫자 칸(박스 없이), 그 아래 = 받은 피해, 상황, 근거, 개선점.
function DeathCard({ X, note, isKey, onClose, hidden }) {
  return (
    <div className={cx('d3-card', hidden && 'is-hidden')} aria-hidden={hidden || undefined}>
      <button type="button" className="d3-x" onClick={onClose} aria-label="죽음 정보 닫기" tabIndex={hidden ? -1 : 0}><Icon n="x" /></button>
      <div className="d3-card-h">
        <span className={cx('dno', 'dno-lg', isKey && 'key')}>{X.no}</span>
        <span className="d3-faces"><Ci c={X.killer} size="lg" />{X.assists.map((a, i) => <Ci key={i} c={a} size="sm" />)}</span>
        <div>
          {isKey && <span className="d3-keytag">주요 죽음</span>}
          {/* 제목 = 왜 죽었는지(피드백 글의 title). 없으면 누구에게 죽었는지 */}
          <h3>{(note && note.title) || `${killers(X)}에게 죽음`}</h3>
          <p className="d3-meta"><span>{X.t}</span><span>{X.phase}</span><span>{X.zone}</span></p>
        </div>
      </div>
      <dl className="d3-facts">
        <div><dt>근처 아군</dt><dd>{X.alliesNear.length ? X.alliesNear.map((c, i) => <Ci key={i} c={c} size="sm" />) : <span className="muted">없음</span>}</dd></div>
        <div><dt>근처 적</dt><dd>{X.enemiesNear.length ? X.enemiesNear.map((c, i) => <Ci key={i} c={c} size="sm" />) : <span className="muted">없음</span>}</dd></div>
        <div><dt>보유 골드</dt><dd className="num">{X.gold != null ? num(X.gold) : '—'}</dd></div>
        <div><dt>스펠</dt><dd className="rx-spells"><MySpells s={X.spells} /></dd></div>
        <div><dt>팀 골드 차이</dt><dd className={cx('num', 'gd', X.teamGoldDiff > 0 ? 'gd-us' : X.teamGoldDiff < 0 ? 'gd-them' : '')}>{signed(X.teamGoldDiff)}</dd></div>
        <div><dt title="죽은 뒤 90초 안에 잃은 포탑과 오브젝트">죽은 뒤 손해</dt><dd>{X.lostAfter.length ? <LostList lost={noTime(X.lostAfter)} /> : <span className="muted">없음</span>}</dd></div>
      </dl>
      <div className="d3-body">
        <div className="d3-row2"><span className="d3-lab">받은 피해</span><DamageBar dmg={X.damage} /></div>
        {X.roams.length > 0 && (
          <div className="d3-row2"><span className="d3-lab">합류한 적</span>
            <ul className="d3-roams">{X.roams.map((r, i) => <li key={i}><Ci c={r.who} size="sm" /><span><b className="num">{r.minuteMark}</b> {r.wasAt}</span></li>)}</ul>
          </div>
        )}
        {note && note.what && <div className="d3-row2"><span className="d3-lab">상황</span><p className="d3-what">{note.what}</p></div>}
        {note && note.evidence && <div className="d3-row2"><span className="d3-lab">근거</span><p>{note.evidence}</p></div>}
        {note && note.next && <div className="d3-row2 d3-nextbox"><span className="d3-lab">개선점</span><p>{note.next}</p></div>}
      </div>
    </div>
  )
}

// ---------- 리플레이: 사망 정보 (롤 Death Recap처럼) ----------
const SLOT_TXT = { AA: '평타', etc: '기타', item: '템', spell: '스펠' }

function Split({ r, max, me }) {
  const w = (v) => `${(v / (max || 1) * 100).toFixed(1)}%`
  return (
    <span className={cx('dr-bar', me && 'me')}>
      <i className="ph" style={{ width: w(r.ph) }} /><i className="mg" style={{ width: w(r.mg) }} /><i className="tr" style={{ width: w(r.tr) }} />
    </span>
  )
}

function SkillIc({ p }) {
  if (p.img) return <span className="dr-sk" title={p.n}><img src={src(p.img)} alt={p.n} />{['Q', 'W', 'E', 'R', 'P'].includes(p.slot) && <em>{p.slot}</em>}</span>
  return <span className="dr-sk dr-sk-txt" title={p.n}>{SLOT_TXT[p.slot] || p.slot}</span>
}

// 기술 이름은 길어서 쓰지 않아요. 아이콘과 Q/W/E/R, 평타/기타 표시로 알 수 있어요.
function Parts({ parts, me, to }) {
  const max = Math.max(1, ...parts.map((p) => p.v))
  return (
    <div className="dr-parts">
      {parts.length === 0 && <p className="muted small">세부 기록이 없어요.</p>}
      {parts.map((p, i) => (
        <div key={i} className="dr-part">
          <SkillIc p={p} /><Split r={p} max={max} me={me} /><b>{num(p.v)}</b>
        </div>
      ))}
      {to && to.length > 0 && <div className="dr-to">{to.map((x, i) => <span key={i}><Ci c={x.who} size="xs" />{num(x.v)}</span>)}</div>}
    </div>
  )
}

// 원 그래프의 고정 피해 칸도 막대와 같은 빗금(SVG 무늬)으로 칠해요.
function Ring({ r }) {
  const R = 30, L = 2 * Math.PI * R, tot = r.ph + r.mg + r.tr || 1
  let off = 0
  const seg = (v, cls) => {
    const len = v / tot * L
    const el = <circle key={cls} className={cls} r={R} cx="36" cy="36" strokeDasharray={`${len} ${L - len}`} strokeDashoffset={-off} />
    off += len
    return el
  }
  return (
    <svg className="dr-ring" viewBox="0 0 72 72" aria-hidden="true">
      <defs>
        <pattern id="dr-hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="5" height="5" fill="#d9dce1" /><rect width="1.6" height="5" fill="#1a1b1e" />
        </pattern>
      </defs>
      <g transform="rotate(-90 36 36)">{seg(r.ph, 'ph')}{seg(r.mg, 'mg')}{seg(r.tr, 'tr')}</g>
      <text x="36" y="41" textAnchor="middle">{num(r.total)}</text>
    </svg>
  )
}

function MySpells({ s }) {
  if (!s || s.state !== 'each') return <span className="muted small">{s && s.state === 'none' ? '기록 없음' : '확인 못 함'}</span>
  return s.list.map((sp) => (
    <span key={sp.key} className={cx('dr-ms', sp.verdict === 'held' && 'bad', sp.verdict === 'used_before' && 'used')} title={`${sp.n} ${SPELL_WORD[sp.verdict] || '확인 못 함'}`}>
      <Pi p={sp} cls="dr-ms-ic" /><small>{SPELL_WORD[sp.verdict] || '?'}</small>
    </span>
  ))
}

function Recap({ r, meC }) {
  const [open, setOpen] = useState(null)
  useEffect(() => setOpen(null), [r])
  const max = Math.max(1, ...r.rows.map((x) => x.v), r.me ? r.me.v : 0)
  const me = r.me
  const myR = me && me.parts.find((p) => p.slot === 'R')
  return (
    <div className="dr">
      <div className="dr-head">
        <div className="dr-time">
          <span className="label">받은 피해</span>
          <b className="num">{num(r.total)}</b>
          <ul className="dr-legend"><li><i className="ph" />물리</li><li><i className="mg" />마법</li><li><i className="tr" />고정</li></ul>
        </div>
        <Ring r={r} />
      </div>
      <ol className="dr-rows">
        {r.rows.map((x, i) => {
          const can = x.kind === 'champ' && x.parts.length > 0
          const on = open === i
          return (
            <li key={i} className={cx(on && 'on')}>
              <button type="button" className="dr-row" disabled={!can} onClick={() => setOpen(on ? null : i)} aria-expanded={can ? on : undefined}>
                <Ci c={x.who} size="md" />
                <span className="dr-v"><b>{num(x.v)}</b><Split r={x} max={max} /></span>
                <span className="dr-used">{x.used.map((u, k) => <SkillIc key={k} p={u} />)}</span>
                <span className="dr-chev" aria-hidden="true">{can ? (on ? '−' : '+') : ''}</span>
              </button>
              {on && <Parts parts={x.parts} />}
            </li>
          )
        })}
        {r.rows.length === 0 && <li className="muted small dr-none">받은 피해 기록이 없어요.</li>}
      </ol>
      <div className={cx('dr-mine', open === 'me' && 'on')}>
        {me ? (
          <button type="button" className="dr-row" onClick={() => setOpen(open === 'me' ? null : 'me')} aria-expanded={open === 'me'}>
            <Ci c={me.who} size="md" />
            <span className="dr-v"><b>{num(me.v)}</b><Split r={me} max={max} me /></span>
            <span className="dr-used">{myR && <SkillIc p={myR} />}</span>
            <span className="dr-chev" aria-hidden="true">{open === 'me' ? '−' : '+'}</span>
          </button>
        ) : (
          <div className="dr-row dr-zero">
            <Ci c={meC} size="md" />
            <span className="dr-v"><b>0</b><span className="dr-bar" /></span>
            <span /><span />
          </div>
        )}
        {open === 'me' && me && <Parts parts={me.parts} me to={me.to} />}
      </div>
    </div>
  )
}

// 리플레이 지도 아래: 교전 구간, 스펠, 골드, 손해 (3칸 x 2줄)
function ReplayNums({ X }) {
  const cells = [
    ['교전 구간', X.fight ? <span className="num sm">{ms(X.fight.from)}~{ms(X.fight.to)}</span> : <span className="muted">계산 못 함</span>],
    ['스펠', <span className="rx-spells"><MySpells s={X.spells} /></span>],
    ['보유 골드', <span className="num">{X.gold != null ? num(X.gold) : '—'}</span>],
    ['적에게 준 골드', X.recap ? <span className="num">{num(X.recap.given)}</span> : <span className="muted">—</span>],
    ['팀 골드 차이', <span className={cx('num', 'gd', X.teamGoldDiff > 0 ? 'gd-us' : X.teamGoldDiff < 0 ? 'gd-them' : '')}>{signed(X.teamGoldDiff)}</span>],
    ['죽은 뒤 손해', X.lostAfter.length ? <LostList lost={noTime(X.lostAfter)} /> : <span className="muted">없음</span>],
  ]
  return (
    <div className="rx-nums">
      {cells.map((c, i) => <div key={i}><span className="label">{c[0]}</span><div className="d3-v">{c[1]}</div></div>)}
    </div>
  )
}

// 리플레이 오른쪽: 위 = 죽음 번호 칸(아래 두 칸과 시작점을 맞춘 격자), 아래 왼쪽 = 받은 피해(좁게), 아래 오른쪽 = 상황과 근거, 개선점(넓게)
function ReplaySide({ X, note, isKey, meC, onPlay }) {
  return (
    <div className="rx-in">
      <div className="rx-top">
        <div className="rx-head">
          <div className="rx-id">
            <span className={cx('dno', isKey && 'key')}>{X.no}</span>
            <span className="rx-t">{X.t}</span>
            {isKey && <span className="d3-keytag">주요 죽음</span>}
          </div>
          <div className="rx-who">
            <span className="rx-faces" aria-label={`${killers(X)}에게 죽음`}>
              <Ci c={X.killer} size="lg" />{X.assists.map((a, i) => <Ci key={i} c={a} size="md" />)}
            </span>
            <div className="rx-ft">
              <span className="label">교전 시간</span>
              {X.fight ? <b className="num">{X.fight.to - X.fight.from}<small>초</small></b> : <b className="rx-none">계산 못 함</b>}
            </div>
          </div>
        </div>
        <button type="button" className="rx-play" onClick={onPlay}>교전 보기</button>
      </div>
      <div className="rx-body">
        <div className="rx-dmg">
          {X.recap ? <Recap r={X.recap} meC={meC} /> : <p className="muted">사망 정보 기록이 없어요.</p>}
        </div>
        <div className="rx-story">
          <div className="rx-story-main">
            {note && note.what
              ? <dl className="rx-why">
                  <div><dt>상황</dt><dd className="rx-what">{note.what}</dd></div>
                  {note.evidence && <div><dt>근거</dt><dd>{note.evidence}</dd></div>}
                </dl>
              : <p className="muted">이 죽음의 상황 설명은 아직 없어요.</p>}
            <p className="rx-near">
              <span>근처 아군</span>{X.alliesNear.length ? X.alliesNear.map((c, i) => <Ci key={i} c={c} size="sm" />) : <em>없음</em>}
              <span>근처 적</span>{X.enemiesNear.map((c, i) => <Ci key={i} c={c} size="sm" />)}
            </p>
          </div>
          {note && note.next && <div className="rx-next"><h4>개선점</h4><p>{note.next}</p></div>}
        </div>
      </div>
    </div>
  )
}

export default function Deaths({ d, fb }) {
  const D = d.deaths
  const rp = D.replay
  // 죽음마다 상황, 근거, 개선점. 피드백 글이 없는 판은 시안 확인용 예시(demoNotes)만 있어요.
  const notes = useMemo(() => {
    const o = {}
    if (fb) {
      ;(fb.keyDeaths || []).forEach((k) => { o[k.t] = k })
      // otherDeaths 한 줄은 개선점이 아니라 상황 설명이라 what으로 넣어요.
      Object.entries(fb.otherDeaths || {}).forEach(([t, v]) => { if (!o[t]) o[t] = typeof v === 'string' ? { what: v } : v })
    } else if (D.demoNotes) Object.assign(o, D.demoNotes)
    return o
  }, [fb, D])
  const keyNos = useMemo(() => {
    const ts = new Set(((fb && fb.keyDeaths) || []).map((k) => k.t))
    return new Set(D.list.filter((x) => ts.has(x.t)).map((x) => x.no))
  }, [fb, D])
  const [mode, setMode] = useState('all')
  const [sel, setSel] = useState(null)      // 기본 모드에서 고른 죽음
  const [cur, setCur] = useState(1)         // 리플레이 모드에서 보는 죽음
  const [vision, setVision] = useState(true)
  const X = sel != null ? D.list.find((x) => x.no === sel) : null
  const R = D.list.find((x) => x.no === cur) || D.list[0]
  const pick = (no) => setSel(no === sel ? null : no)
  const [jump, setJump] = useState(0)        // 죽음 바로가기를 누른 횟수 (누를 때만 재생 위치를 옮겨요)
  const goDeath = (no) => { setCur(no); setJump((j) => j + 1) }
  const toReplay = () => { setMode('replay'); goDeath(1) }
  // 재생 위치에 맞는 죽음: 다음에 올 죽음이에요. 죽고 3초 뒤까지는 그 죽음, 마지막 죽음 뒤로는 마지막 죽음.
  const deathAt = (t) => {
    const xs = D.list.filter((x) => x.sec != null)
    return (xs.find((x) => t <= x.sec + 3) || xs[xs.length - 1] || D.list[0]).no
  }
  const onTime = (t) => setCur(deathAt(t))
  const scene = R && R.fight ? { ...R.fight, joins: R.joins || [] } : R && R.sec ? { from: R.sec - 10, to: R.sec, joins: R.joins || [] } : null
  const fights = D.list.map((x) => x.fight || (x.sec != null ? { from: x.sec, to: x.sec } : null)).filter(Boolean)
  // 접근 이름표: 살펴보는 구간 첫 초에 이미 가까이 있던 적은 빼요(그건 접근이 아니라 원래 붙어 있던 것)
  const joins = useMemo(() => D.list.flatMap((x) => {
    if (x.sec == null) return []
    const w0 = Math.max((x.fight ? x.fight.from : x.sec) - 5, x.sec - 90)
    return (x.joins || []).filter((j) => j.t > w0)
  }), [D])
  const isReplay = mode === 'replay' && rp && R

  const cells = [
    ['데스', <span className="num">{D.total}</span>, 'hot'],
    ...D.phases.map((p) => [p.name, <span className="num">{p.n}<small>번</small></span>]),
    ['혼자 죽음', <span className="num">{D.alone}<small>번</small></span>],
    ['죽은 뒤 손해', <span className="num red">{D.lostN}<small>번</small></span>],
  ]

  return (
    <Section no="04">
      <div className={cx('d3', isReplay && 'is-replay', keyNos.size > 0 && 'has-key')}>
        <div className="d3-bar">
          <div className="d3-tabs">
            <button type="button" className={cx(mode === 'all' && 'on')} onClick={() => setMode('all')}>기본</button>
            {rp && <button type="button" className={cx(mode === 'replay' && 'on')} onClick={toReplay}>리플레이</button>}
          </div>
          {isReplay && (
            <div className="d3-jump" role="group" aria-label="죽음 바로가기">
              {D.list.map((x) => <button key={x.t} type="button" className={cx('dno', keyNos.has(x.no) && 'key', cur === x.no && 'on')} onClick={() => goDeath(x.no)} aria-pressed={cur === x.no} title={`${x.no}번째 죽음 ${x.t}${keyNos.has(x.no) ? ' (주요 죽음)' : ''}`}>{x.no}</button>)}
            </div>
          )}
        </div>
        {isReplay ? (
          <Replay rp={rp} scene={scene} jump={jump} onTime={onTime} joins={joins} vision={vision} setVision={setVision} fights={fights}
            under={<ReplayNums X={R} />}
            side={(play) => <ReplaySide X={R} note={notes[R.t]} isKey={keyNos.has(R.no)} meC={rp.champs.find((c) => c.me)} onPlay={play} />} />
        ) : (
          <>
            <div className="d3-main">
              <div className="d3-stage">
                <div className="d3-map"><OverviewMap m={D.map} active={sel} onPick={pick} keyNos={keyNos} /></div>
                <ul className="legend legend-map">
                  <li><span className="lg lg-mdeath" />죽음</li><li><span className="lg lg-mkill" />킬</li><li><span className="lg lg-massist" />어시스트</li>
                </ul>
              </div>
              <div className="d3-side">
                {/* 모든 죽음 칸을 한 자리에 겹쳐 두고 고른 것만 보여요. 칸 높이가 가장 긴 죽음에 맞춰져서 다른 죽음을 눌러도 목록이 출렁이지 않아요. */}
                {X && (
                  <div className="d3-cards">
                    {D.list.map((x) => <DeathCard key={x.t} X={x} note={notes[x.t]} isKey={keyNos.has(x.no)} hidden={x.no !== sel} onClose={() => setSel(null)} />)}
                  </div>
                )}
                <ol className="d3-list">
                  {D.list.map((x) => <Row key={x.t} x={x} note={notes[x.t]} isKey={keyNos.has(x.no)} on={sel === x.no} onPick={() => pick(x.no)} />)}
                </ol>
              </div>
            </div>
            <div className="d3-strip">{cells.map((c, i) => <div key={i} className={cx(c[2])}><span className="label">{c[0]}</span><div className="d3-v">{c[1]}</div></div>)}</div>
          </>
        )}
      </div>
    </Section>
  )
}
