import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { Section, Ci, LostList, Pi, MAP_IMG, src, num, signed, cx } from '../ui.jsx'

// 04 죽음 (11-20): 왼쪽 무대(기본 / 리플레이), 가운데 죽음 목록(개선점 한 줄), 오른쪽 사망 정보(롤 Death Recap처럼),
// 아래 숫자 띠(전체 요약 또는 고른 죽음).

const ms = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`
const SPELL_WORD = { held: '안 씀', used_before: '씀', already_down: '없음', uncertain: '판단 보류' }

// ---------- 기본: 모든 죽음 번호와 킬 ----------
function OverviewMap({ m, active, onPick }) {
  const S = m.size
  return (
    <svg className={cx('map', active != null && 'has-active')} viewBox={`0 0 ${S} ${S}`} role="img" aria-label="내가 죽은 곳과 킬한 곳">
      <image href={MAP_IMG} x="0" y="0" width={S} height={S} />
      {m.kills.map((p, i) => (
        <rect key={`k${i}`} className={p.solid ? 'mp-kill' : 'mp-assist'} x={p.x - 6.5} y={p.y - 6.5} width="13" height="13"
          transform={`rotate(45 ${p.x} ${p.y})`}><title>{p.t} {p.solid ? '킬' : '어시스트'}</title></rect>
      ))}
      {m.deaths.map((p) => (
        <g key={p.no} className={cx('mp-d', active === p.no && 'on')} onClick={() => onPick(p.no)} style={{ cursor: 'pointer' }}>
          <title>{p.t} {p.no}번째 죽음</title>
          <circle className="mp-death" cx={p.x} cy={p.y} r={p.key ? 15 : 12} />
          {p.key && <circle cx={p.x} cy={p.y} r="19" fill="none" stroke="var(--red)" strokeWidth="1.5" />}
          <text className="mp-num" x={p.x} y={p.y + 4.5} textAnchor="middle">{p.no}</text>
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

function Label({ x, y, S, text, tone }) {
  // 점 위쪽에 이름표를 달고 선으로 이어요. 지도 밖으로 나가지 않게 자리를 조정해요.
  const w = text.length * 10 + 18, h = 24
  const up = y > 60
  const lx = Math.min(Math.max(x - w / 2, 4), S - w - 4)
  const ly = up ? y - 52 : y + 28
  return (
    <g className={cx('rp-label', tone && `rp-label-${tone}`)}>
      <line x1={x} y1={y + (up ? -14 : 14)} x2={Math.min(Math.max(x, lx + 6), lx + w - 6)} y2={up ? ly + h : ly} />
      <rect x={lx} y={ly} width={w} height={h} />
      <text x={lx + 8} y={ly + 16.5}>{text}</text>
    </g>
  )
}

// 플레이어 버튼 그림 (각진 도형)
const PI = {
  play: <path d="M7 4.5 L19 12 L7 19.5 Z" />,
  pause: <><rect x="6" y="4.5" width="4" height="15" /><rect x="14" y="4.5" width="4" height="15" /></>,
  back: <><path d="M11 6 L4 12 L11 18 Z" /><path d="M20 6 L13 12 L20 18 Z" /></>,
  fwd: <><path d="M4 6 L11 12 L4 18 Z" /><path d="M13 6 L20 12 L13 18 Z" /></>,
  again: <><path d="M5 12 a7 7 0 1 0 2.1 -5" fill="none" stroke="currentColor" strokeWidth="2.2" /><path d="M3.5 3.5 L8.6 4.2 L6.4 8.8 Z" /></>,
}
const Icon = ({ n }) => <svg className="rp-i" viewBox="0 0 24 24" aria-hidden="true">{PI[n]}</svg>
const SPEEDS = [0.5, 1, 2, 4, 8]
const OBJ_NAME = { dragon: '드래곤', baron: '바론', herald: '전령', grub: '공허 유충', tower: '포탑', inhib: '억제기' }

// 시간 막대: 위 줄 = 우리 팀 일, 아래 줄 = 상대 팀 일, 빨간 칸 = 내 죽음(교전 구간). 마우스를 올리면 그 시각과 일어난 일.
function Timeline({ rp, t, scene, fights, onSeek, onScrub }) {
  const ref = useRef(null)
  const [hover, setHover] = useState(null)
  const C = rp.champs
  const L = rp.len
  const pct = (v) => `${(v / L * 100).toFixed(3)}%`
  const toT = (clientX) => {
    const r = ref.current.getBoundingClientRect()
    return Math.min(Math.max((clientX - r.left) / r.width, 0), 1) * L
  }
  const marks = useMemo(() => rp.events.map((e) => {
    if (e.k === 'kill') {
      const me = C[e.who] && C[e.who].me
      const by = e.by != null && C[e.by] ? C[e.by].n : '처형'
      return { ...e, row: me ? 'me' : e.us ? 'us' : 'them', what: me ? `내가 죽음 (${by})` : `${by} → ${C[e.who].n} 킬` }
    }
    return { ...e, row: e.us ? 'us' : 'them', what: `${e.us ? '우리' : '상대'} ${OBJ_NAME[e.g] || ''}` }
  }), [rp])
  const near = hover != null ? marks.filter((m) => Math.abs(m.t - hover) <= L / 120 + 4).slice(0, 4) : []
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
        {marks.filter((m) => m.row === 'us').map((m, i) => <Mark key={i} m={m} left={pct(m.t)} onSeek={onSeek} />)}
      </div>
      <div className="tl-track">
        {fights.map((f, i) => <span key={i} className={cx('tl-fight', scene && scene.to === f.to && 'on')} style={{ left: pct(f.from), width: `max(3px, ${pct(f.to - f.from)})` }} />)}
        <span className="tl-done" style={{ width: pct(t) }} />
        {marks.filter((m) => m.row === 'me').map((m, i) => <span key={i} className="tl-death" style={{ left: pct(m.t) }} />)}
        <span className="tl-knob" style={{ left: pct(t) }} />
      </div>
      <div className="tl-row tl-them">
        {marks.filter((m) => m.row === 'them').map((m, i) => <Mark key={i} m={m} left={pct(m.t)} onSeek={onSeek} />)}
      </div>
      {hover != null && (
        <div className="tl-tip" style={{ left: pct(hover) }}>
          <b>{ms(hover)}</b>
          {near.map((m, i) => <span key={i} className={cx(m.row === 'me' && 'red')}>{ms(m.t)} {m.what}</span>)}
        </div>
      )}
      {hover != null && <span className="tl-hline" style={{ left: pct(hover) }} />}
    </div>
  )
}

function Mark({ m, left, onSeek }) {
  const go = (e) => { e.stopPropagation(); onSeek(Math.max(m.t - 5, 0)) }
  if (m.k === 'kill') return <span className={cx('tl-m tl-kill', m.us && 'us')} style={{ left }} onPointerDown={(e) => e.stopPropagation()} onClick={go} title={`${ms(m.t)} ${m.what}`} />
  return (
    <svg className={cx('tl-m tl-obj', m.us && 'us')} style={{ left }} viewBox="0 0 24 24" onPointerDown={(e) => e.stopPropagation()} onClick={go}>
      <title>{ms(m.t)} {m.what}</title><use href={`#i-${m.g}`} />
    </svg>
  )
}

function Replay({ rp, scene, vision, setVision, fights }) {
  const T = useTracks(rp)
  const S = rp.size
  const [t, setT] = useState(scene ? Math.max(scene.from - 5, 0) : 0)
  const [play, setPlay] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [flash, setFlash] = useState(null)
  const stopAt = useRef(null)
  const raf = useRef(0)
  const last = useRef(0)

  const playScene = () => {
    if (!scene) return
    setT(Math.max(scene.from - 5, 0)); stopAt.current = scene.to + 3; setPlay(true)
  }
  // 죽음을 고르면 교전 5초 전으로 가서 재생하고, 죽은 뒤 3초에 멈춰요.
  useEffect(() => { if (scene) { setSpeed(1); playScene() } }, [scene && scene.to])

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
    if (e.target.closest('.tl')) return
    if (e.key === ' ' || e.key === 'k') { e.preventDefault(); toggle() }
    else if (e.key === 'ArrowLeft' || e.key === 'j') { e.preventDefault(); seek(t - 10) }
    else if (e.key === 'ArrowRight' || e.key === 'l') { e.preventDefault(); seek(t + 10) }
  }

  const C = rp.champs
  const pos = C.map((_, i) => posAt(T, i, t))
  // 추정 시야: 살아 있는 우리 팀 주변, 켜져 있는 우리 와드, 남아 있는 우리 포탑 (벽·수풀은 계산하지 않아요)
  const src_ = []
  C.forEach((c, i) => { if (c.us && pos[i]) src_.push([pos[i][0], pos[i][1], rp.sight / 10]) })
  rp.wards.forEach(([a, b, x, y, r]) => { if (t >= a && t < b) src_.push([x / 10, y / 10, r / 10]) })
  rp.turrets.forEach(([x, y, end]) => { if (t < end) src_.push([x / 10, y / 10, rp.sight / 10]) })
  const seen = (p) => src_.some(([x, y, r]) => (p[0] - x) ** 2 + (p[1] - y) ** 2 <= r * r)

  const evNow = rp.events.filter((e) => t >= e.t && t < e.t + 4)
  const labels = []
  if (scene) {
    scene.joins.forEach((j) => {
      if (t >= j.t && t < j.t + 3 && pos[j.who]) labels.push({ key: `j${j.who}`, at: pos[j.who], text: `${C[j.who].n} 접근 ${ms(j.t)}`, ring: j.who })
    })
    const meI = C.findIndex((c) => c.me)
    const dk = rp.events.find((e) => e.k === 'kill' && e.who === meI && e.t === scene.to)
    if (dk && t >= scene.to && t < scene.to + 4) labels.push({ key: 'd', at: [dk.x / 10, dk.y / 10], text: `내가 죽음 ${ms(scene.to)}`, tone: 'red' })
  }
  const rings = new Set(labels.map((l) => l.ring).filter((r) => r != null))
  const inFight = scene && t >= scene.from && t <= scene.to

  return (
    <div className="rp" tabIndex={0} onKeyDown={keys} aria-label="리플레이. 스페이스 재생·멈춤, 화살표 10초 이동">
      <div className="rp-screen" onClick={toggle}>
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
          {evNow.map((e, i) => {
            const x = e.x / 10, y = e.y / 10
            if (e.k === 'kill') {
              return e.us
                ? <rect key={i} className="mp-kill" x={x - 6} y={y - 6} width="12" height="12" transform={`rotate(45 ${x} ${y})`} />
                : <path key={i} className="rp-x" d={`M${x - 7} ${y - 7}L${x + 7} ${y + 7}M${x + 7} ${y - 7}L${x - 7} ${y + 7}`} />
            }
            return <use key={i} href={`#i-${e.g}`} x={x - 10} y={y - 10} width="20" height="20" className={e.us ? 'rp-obj-us' : 'rp-obj-them'} />
          })}
          {C.map((c, i) => {
            const p = pos[i]
            if (!p) return null
            const r = c.me ? 13 : 11
            const out = vision && !c.us && !seen(p)
            return (
              <g key={i} transform={`translate(${p[0].toFixed(1)} ${p[1].toFixed(1)})`} className={cx('rp-tok', c.us ? 'us' : 'them', c.me && 'me', out && 'out')}>
                {rings.has(i) && <circle className="rp-pulse" r={r + 8} />}
                <image href={src(c.img)} x={-r} y={-r} width={r * 2} height={r * 2} clipPath={`url(#rp-tk${c.me ? '-me' : ''})`} />
                <circle className="rp-ring" r={r} />
                <title>{c.n}{out ? ' (시야 밖으로 추정)' : ''}</title>
              </g>
            )
          })}
          {labels.map((l) => <Label key={l.key} x={l.at[0]} y={l.at[1]} S={S} text={l.text} tone={l.tone} />)}
        </svg>
        <span className="rp-clock">{ms(t)}{inFight && <i>교전 중</i>}</span>
        {flash && <span className="rp-flash"><Icon n={flash} /></span>}
      </div>
      <div className="rp-dock">
        <Timeline rp={rp} t={t} scene={scene} fights={fights} onSeek={seek} onScrub={(v) => { setPlay(false); seek(v) }} />
        <div className="rp-ctrl">
          <button type="button" className="rp-b" onClick={() => seek(t - 10)} title="10초 뒤로 (←)"><Icon n="back" /></button>
          <button type="button" className="rp-b rp-main" onClick={toggle} title={play ? '멈춤 (스페이스)' : '재생 (스페이스)'}><Icon n={play ? 'pause' : 'play'} /></button>
          <button type="button" className="rp-b" onClick={() => seek(t + 10)} title="10초 앞으로 (→)"><Icon n="fwd" /></button>
          <span className="rp-time"><b>{ms(t)}</b> / {ms(rp.len)}</span>
          {scene && <button type="button" className="rp-again" onClick={playScene}><Icon n="again" />교전 다시 보기</button>}
          <span className="rp-right">
            <span className="rp-speed" role="group" aria-label="재생 속도">
              <button type="button" disabled={si <= 0} onClick={() => setSpeed(SPEEDS[si - 1])} aria-label="느리게">−</button>
              <b>{speed}×</b>
              <button type="button" disabled={si >= SPEEDS.length - 1} onClick={() => setSpeed(SPEEDS[si + 1])} aria-label="빠르게">+</button>
            </span>
            <label className="rp-vis"><input type="checkbox" checked={vision} onChange={(e) => setVision(e.target.checked)} />추정 시야</label>
          </span>
        </div>
      </div>
    </div>
  )
}

// ---------- 가운데 죽음 목록 ----------
function Row({ x, line, on, onPick }) {
  return (
    <li>
      <button type="button" className={cx('d2-row', on && 'on')} onClick={onPick} aria-pressed={on}>
        <span className="dno">{x.no}</span>
        <time>{x.t}</time>
        <span className="d2-kill"><Ci c={x.killer} size="sm" />{x.assists.map((a, i) => <Ci key={i} c={a} size="xs" />)}</span>
        <span className="d2-lost">{x.lostAfter.length > 0 ? <LostList lost={x.lostAfter} /> : <span className="muted">손해 없음</span>}</span>
        {line && <span className="d2-next"><b>개선점</b>{line}</span>}
      </button>
    </li>
  )
}

// ---------- 오른쪽 사망 정보 (롤 Death Recap처럼) ----------
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
  if (p.img) return <span className="dr-sk"><img src={src(p.img)} alt="" />{['Q', 'W', 'E', 'R', 'P'].includes(p.slot) && <em>{p.slot}</em>}</span>
  return <span className="dr-sk dr-sk-txt">{SLOT_TXT[p.slot] || p.slot}</span>
}

function Parts({ parts, me, to }) {
  const max = Math.max(1, ...parts.map((p) => p.v))
  return (
    <div className="dr-parts">
      {parts.length === 0 && <p className="muted small">세부 기록이 없어요.</p>}
      {parts.map((p, i) => (
        <div key={i} className="dr-part">
          <SkillIc p={p} /><span className="dr-pn">{p.n}</span><Split r={p} max={max} me={me} /><b>{num(p.v)}</b>
        </div>
      ))}
      {to && to.length > 0 && <div className="dr-to"><span className="label">넣은 대상</span>{to.map((x, i) => <span key={i}><Ci c={x.who} size="xs" />{num(x.v)}</span>)}</div>}
    </div>
  )
}

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
      <g transform="rotate(-90 36 36)">{seg(r.ph, 'ph')}{seg(r.mg, 'mg')}{seg(r.tr, 'tr')}</g>
      <text x="36" y="41" textAnchor="middle">{num(r.total)}</text>
    </svg>
  )
}

function MySpells({ s }) {
  if (!s || s.state !== 'each') return <span className="muted small">{s && s.state === 'none' ? '스펠 기록 없음' : '스펠 확인 못 함'}</span>
  return s.list.map((sp) => (
    <span key={sp.key} className={cx('dr-ms', sp.verdict === 'held' && 'bad', sp.verdict === 'used_before' && 'used')} title={`${sp.n} ${SPELL_WORD[sp.verdict] || '확인 못 함'}`}>
      <Pi p={sp} cls="dr-ms-ic" /><small>{SPELL_WORD[sp.verdict] || '?'}</small>
    </span>
  ))
}

function Recap({ r, fight, spells, many }) {
  const [open, setOpen] = useState(null)
  useEffect(() => setOpen(null), [r])
  const max = Math.max(1, ...r.rows.map((x) => x.v), r.me ? r.me.v : 0)
  const me = r.me
  const myR = me && me.parts.find((p) => p.slot === 'R')
  return (
    <div className="dr">
      <div className="dr-head">
        {many
          ? <div className="dr-time"><span className="label">죽음 {many}번 동안</span><b>받은 피해</b></div>
          : <div className="dr-time">
              <span className="label">교전 시간</span>
              {fight ? <><b className="num">{fight.to - fight.from}<small>초</small></b><span className="dr-range">{ms(fight.from)}~{ms(fight.to)}</span></>
                : <b className="muted">계산 못 함</b>}
            </div>}
        <Ring r={r} />
        <ul className="dr-legend"><li><i className="ph" />물리</li><li><i className="mg" />마법</li><li><i className="tr" />고정</li></ul>
      </div>
      <ol className="dr-rows">
        {r.rows.map((x, i) => {
          const can = x.kind === 'champ' && x.parts.length > 0
          const on = open === i
          return (
            <li key={i} className={cx(on && 'on')}>
              <button type="button" className="dr-row" disabled={!can} onClick={() => setOpen(on ? null : i)} aria-expanded={can ? on : undefined}>
                <Ci c={x.who} size="sm" />
                <span className="dr-v"><b>{num(x.v)}</b><Split r={x} max={max} /></span>
                <span className="dr-used">{x.used.map((u, k) => <SkillIc key={k} p={u} />)}</span>
                {can && <span className="dr-chev" aria-hidden="true">{on ? '−' : '+'}</span>}
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
            <Ci c={me.who} size="sm" />
            <span className="dr-v"><span className="label">내가 넣은 피해</span><b>{num(me.v)}</b><Split r={me} max={max} me /></span>
            <span className="dr-used">{!many && <MySpells s={spells} />}{myR && <SkillIc p={myR} />}</span>
            <span className="dr-chev" aria-hidden="true">{open === 'me' ? '−' : '+'}</span>
          </button>
        ) : <p className="muted small">내가 넣은 피해 기록이 없어요.</p>}
        {open === 'me' && me && <Parts parts={me.parts} me to={me.to} />}
      </div>
      <p className="dr-foot">챔피언을 누르면 어떤 기술로 피해를 줬는지 보여요.{!many && fight && ' 교전 시간은 롤 전투 상태 기준(마지막 상호작용 뒤 5초)으로 추정했어요.'}</p>
    </div>
  )
}

// 여러 죽음의 사망 정보를 하나로 합쳐요(아무것도 고르지 않았을 때).
function mergeRecaps(list) {
  const add = (a, b) => { a.v += b.v; a.ph += b.ph; a.mg += b.mg; a.tr += b.tr }
  const mergeParts = (into, parts) => parts.forEach((p) => {
    const k = p.slot + p.n
    if (!into[k]) into[k] = { ...p, v: 0, ph: 0, mg: 0, tr: 0 }
    add(into[k], p)
  })
  const rows = {}, mp = {}, to = {}
  let me = null
  const out = { v: 0, ph: 0, mg: 0, tr: 0 }
  list.forEach((r) => {
    if (!r) return
    add(out, { v: r.total, ph: r.ph, mg: r.mg, tr: r.tr })
    r.rows.forEach((x) => {
      const k = x.kind + x.who.n
      if (!rows[k]) rows[k] = { ...x, v: 0, ph: 0, mg: 0, tr: 0, _p: {}, _u: {} }
      add(rows[k], x); mergeParts(rows[k]._p, x.parts); x.used.forEach((u) => { rows[k]._u[u.n] = u })
    })
    if (r.me) {
      if (!me) me = { ...r.me, v: 0, ph: 0, mg: 0, tr: 0 }
      add(me, r.me); mergeParts(mp, r.me.parts)
      ;(r.me.to || []).forEach((x) => { to[x.who.n] = { who: x.who, v: ((to[x.who.n] || {}).v || 0) + x.v } })
    }
  })
  out.total = out.v
  out.rows = Object.values(rows).map((x) => ({ ...x, parts: Object.values(x._p).sort((a, b) => b.v - a.v), used: Object.values(x._u) }))
    .sort((a, b) => b.v - a.v)
  out.me = me && { ...me, parts: Object.values(mp).sort((a, b) => b.v - a.v), to: Object.values(to).sort((a, b) => b.v - a.v) }
  return out
}

function Strip({ cells }) {
  return <div className="d2-strip">{cells.map((c, i) => <div key={i}><span className="label">{c[0]}</span><div className="d2-v">{c[1]}</div></div>)}</div>
}

export default function Deaths({ d, fb }) {
  const D = d.deaths
  const rp = D.replay
  const byT = Object.fromEntries(D.list.map((x) => [x.t, x]))
  const keyList = fb ? fb.keyDeaths.filter((kd) => byT[kd.t]) : []
  const kdOf = Object.fromEntries(keyList.map((kd) => [kd.t, kd]))
  const other = (fb && fb.otherDeaths) || {}
  const [sel, setSel] = useState(null)
  const [mode, setMode] = useState('all')
  const [vision, setVision] = useState(true)
  const X = sel != null ? D.list.find((x) => x.no === sel) : null
  const pick = (no) => {
    if (no === sel) { setSel(null); setMode('all'); return }
    setSel(no)
    if (rp) setMode('replay')
  }
  const keySet = new Set(keyList.map((k) => k.t))
  const mapM = { ...D.map, deaths: D.map.deaths.map((p) => ({ ...p, key: keySet.has(p.t) })) }
  const lineOf = (x) => (kdOf[x.t] && kdOf[x.t].next) || other[x.t] || null
  const keyRows = D.list.filter((x) => keySet.has(x.t))
  const restRows = D.list.filter((x) => !keySet.has(x.t))
  const scene = X && X.fight ? { ...X.fight, joins: X.joins || [] } : X && X.sec ? { from: X.sec - 10, to: X.sec, joins: X.joins || [] } : null
  const fights = D.list.map((x) => x.fight || (x.sec != null ? { from: x.sec, to: x.sec } : null)).filter(Boolean)
  const allRecap = useMemo(() => mergeRecaps(D.list.map((x) => x.recap)), [D])
  const kd = X && kdOf[X.t]

  const cells = X
    ? [
        ['보유 골드', <span className="num">{X.gold != null ? num(X.gold) : '—'}</span>],
        ['적에게 준 골드', X.recap ? <span className="num">+{num(X.recap.given)}</span> : <span className="muted">—</span>],
        ['팀 골드 차이', <span className={cx('num', X.teamGoldDiff < 0 && 'neg')}>{signed(X.teamGoldDiff)}</span>],
        ['죽은 뒤 손해', X.lostAfter.length ? <LostList lost={X.lostAfter} /> : <span className="muted">없음</span>],
      ]
    : [
        ['데스', <span className="num red">{D.total}</span>],
        ...D.phases.map((p) => [p.name, <span className="num">{p.n}<small>번</small></span>]),
        ['혼자 죽음', <span className="num">{D.alone}<small>번</small></span>],
        ['죽은 뒤 손해', <span className="num">{D.lostN}<small>번</small></span>],
      ]

  return (
    <Section no="04">
      <div className="d2">
        <div className="d2-top">
          <span className="d2-count">{X ? <>죽음 <b>{X.no}</b> / {D.total}</> : <>죽음 전체 <b>{D.total}</b></>}</span>
          <span className="d2-seg">
            {D.list.map((x) => <button key={x.t} type="button" className={cx(sel === x.no && 'on', keySet.has(x.t) && 'key')} onClick={() => pick(x.no)} aria-label={`${x.no}번째 죽음 ${x.t}`} />)}
          </span>
          <span className="d2-meta">{X ? `${X.t} · ${X.phase} · ${X.zone}` : D.zones.filter((z) => z.n).map((z) => `${z.name} ${z.n}`).join(' · ')}</span>
        </div>
        {X && (
          <h3 className="d2-head">
            <Ci c={X.killer} size="sm" />{X.killer.n}{X.assists.length > 0 && <>·{X.assists.map((a) => a.n).join('·')}</>}에게 죽음
            <span className="d2-near">근처 아군 {X.alliesNear.length} · 적 {X.enemiesNear.length}</span>
          </h3>
        )}
        <div className="d2-main">
          <div className="d2-stage">
            <div className="d2-tabs">
              <button type="button" className={cx(mode === 'all' && 'on')} onClick={() => setMode('all')}>기본</button>
              {rp && <button type="button" className={cx(mode === 'replay' && 'on')} onClick={() => setMode('replay')}>리플레이</button>}
            </div>
            <div className="d2-frame">
              {mode === 'replay' && rp
                ? <Replay rp={rp} scene={scene} vision={vision} setVision={setVision} fights={fights} />
                : <OverviewMap m={mapM} active={sel} onPick={pick} />}
            </div>
            {mode === 'replay' && rp && vision && <p className="d2-note">어두운 곳은 우리 팀 시야 밖으로 추정한 곳이에요(벽·수풀은 계산 안 함). 시야 밖의 적은 흐리게 보여요.</p>}
            {mode === 'all' && (
              <ul className="legend legend-map">
                <li><span className="lg lg-mdeath" />죽은 곳</li><li><span className="lg lg-mkill" />킬</li><li><span className="lg lg-massist" />어시스트</li>
                {keyList.length > 0 && <li>큰 원 = 주요 죽음</li>}
              </ul>
            )}
          </div>
          <div className="d2-list">
            {keyRows.length > 0 && <>
              <h4 className="d2-lh">주요 죽음</h4>
              <ol>{keyRows.map((x) => <Row key={x.t} x={x} line={lineOf(x)} on={sel === x.no} onPick={() => pick(x.no)} />)}</ol>
            </>}
            {restRows.length > 0 && <>
              <h4 className="d2-lh">{keyRows.length ? '다른 죽음' : `죽음 ${D.total}`}</h4>
              <ol>{restRows.map((x) => <Row key={x.t} x={x} line={lineOf(x)} on={sel === x.no} onPick={() => pick(x.no)} />)}</ol>
            </>}
            {kd && kd.what && (
              <div className="d2-why">
                <p><b>상황</b>{kd.what}</p>
                {kd.evidence && <p><b>근거</b>{kd.evidence}</p>}
              </div>
            )}
            {!X && <p className="muted small d2-hint">{rp ? '죽음을 고르면 그 교전을 리플레이로 다시 보여 줘요. 한 번 더 누르면 전체로 돌아가요.' : '죽음을 고르면 그 죽음의 사망 정보가 오른쪽에 나와요.'}</p>}
          </div>
          <div className="d2-recap">
            {X ? (X.recap ? <Recap r={X.recap} fight={X.fight} spells={X.spells} /> : <p className="muted small">사망 정보 기록이 없어요.</p>)
              : <Recap r={allRecap} many={D.total} />}
          </div>
        </div>
        <Strip cells={cells} />
      </div>
    </Section>
  )
}
