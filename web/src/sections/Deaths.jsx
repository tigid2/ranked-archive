import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { Section, Ci, Faces, LostList, Pi, Gi, MAP_IMG, src, num, signed, cx } from '../ui.jsx'

// 04 죽음 (11-19 새 배치): 왼쪽 무대(전체 지도 / 미니맵 리플레이), 오른쪽 죽음 목록(개선점 한 줄),
// 아래 숫자 띠(전체 요약 또는 고른 죽음), 그 아래 고른 죽음의 그림 3칸.

const ms = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`
const SPELL_WORD = { held: '안 씀', used_before: '씀', already_down: '없음', uncertain: '판단 보류' }

// ---------- 전체 지도: 모든 죽음 번호와 킬 ----------
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

// ---------- 미니맵 리플레이 ----------
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

function Replay({ rp, scene, vision }) {
  const T = useTracks(rp)
  const S = rp.size
  const [t, setT] = useState(scene ? Math.max(scene.from - 5, 0) : 0)
  const [play, setPlay] = useState(false)
  const [speed, setSpeed] = useState(1)
  const stopAt = useRef(null)
  const raf = useRef(0)
  const last = useRef(0)

  // 죽음을 고르면 교전 5초 전으로 가서 재생하고, 죽은 뒤 3초에 멈춰요.
  useEffect(() => {
    if (!scene) return
    setT(Math.max(scene.from - 5, 0)); setSpeed(1); stopAt.current = scene.to + 3; setPlay(true)
  }, [scene && scene.to])

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

  const sec = Math.floor(t)
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
  const myDeaths = rp.events.filter((e) => e.k === 'kill' && C[e.who] && C[e.who].me)

  return (
    <div className="rp">
      <svg className="map rp-map" viewBox={`0 0 ${S} ${S}`} role="img" aria-label={`미니맵 리플레이 ${ms(t)}`}>
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
      <div className="rp-ctrl">
        <button type="button" className="rp-btn" onClick={() => { stopAt.current = null; if (t >= rp.len) setT(0); setPlay(!play) }}>{play ? '멈춤' : '재생'}</button>
        <span className="rp-time"><b>{ms(t)}</b> / {ms(rp.len)}</span>
        <div className="rp-speed" role="group" aria-label="재생 속도">
          {[1, 2, 4, 8].map((v) => <button key={v} type="button" className={cx(speed === v && 'on')} onClick={() => setSpeed(v)}>{v}×</button>)}
        </div>
      </div>
      <div className="rp-bar">
        {scene && <span className="rp-band" style={{ left: `${scene.from / rp.len * 100}%`, width: `${Math.max((scene.to - scene.from) / rp.len * 100, 0.4)}%` }} />}
        {myDeaths.map((e, i) => <span key={i} className="rp-tick" style={{ left: `${e.t / rp.len * 100}%` }} title={`죽음 ${ms(e.t)}`} />)}
        <input type="range" min="0" max={rp.len} step="1" value={sec} aria-label="시간"
          onChange={(e) => { stopAt.current = null; setT(Number(e.target.value)) }} />
      </div>
    </div>
  )
}

// ---------- 오른쪽 죽음 목록 ----------
function Row({ x, me, line, on, onPick }) {
  return (
    <li>
      <button type="button" className={cx('d2-row', on && 'on')} onClick={onPick} aria-pressed={on}>
        <span className="dno">{x.no}</span>
        <time>{x.t}</time>
        <span className="d2-kill"><Ci c={x.killer} size="sm" />{x.assists.length > 0 && <Faces list={x.assists} />}</span>
        <span className="d2-lost">{x.lostAfter.length > 0 ? <LostList lost={x.lostAfter} /> : <span className="muted">손해 없음</span>}</span>
        {line && <span className="d2-next"><b>개선점</b>{line}</span>}
      </button>
    </li>
  )
}

// ---------- 고른 죽음의 그림 3칸 ----------
function HpLine({ hp, end }) {
  if (!hp.length) return <p className="muted small">게임 중 기록이 없어요.</p>
  const W = 240, H = 70, t0 = end - 10
  const X = (t) => ((t - t0) / 10) * W, Yv = (v) => H - (v / 100) * H
  const pts = [...hp, { t: end, hp: 0 }].filter((p) => p.t >= t0)
  return (
    <svg className="d2-hp" viewBox={`-4 -4 ${W + 8} ${H + 22}`} role="img" aria-label="죽기 전 10초 체력">
      <line x1="0" y1={H} x2={W} y2={H} className="ax" />
      <polyline points={pts.map((p) => `${X(p.t).toFixed(1)},${Yv(p.hp).toFixed(1)}`).join(' ')} />
      {pts.slice(0, 1).map((p) => <text key="a" x={X(p.t)} y={Yv(p.hp) - 6} className="v">{p.hp}%</text>)}
      <text x="0" y={H + 16} className="tk">10초 전</text>
      <text x={W} y={H + 16} className="tk" textAnchor="end">죽음</text>
    </svg>
  )
}

function Detail({ x, kd }) {
  const tot = x.damage.reduce((s, v) => s + v.v, 0) || 1
  const maxSk = Math.max(1, ...(x.skills || []).map((s) => s.v))
  return (
    <div className="d2-detail">
      <div>
        <span className="label">받은 피해</span>
        <div className="dmg-bar d2-dmg">{x.damage.map((v, i) => <span key={i} className={`dmg-seg dmg-${i}`} style={{ width: `${(v.v / tot * 100).toFixed(1)}%` }} />)}</div>
        <ul className="d2-dmg-list">{x.damage.map((v, i) => <li key={i}><Ci c={v.who} size="sm" /><span>{v.who.n}</span><b>{num(v.v)}</b></li>)}</ul>
      </div>
      <div>
        <span className="label">크게 맞은 기술</span>
        <ul className="d2-skills">
          {(x.skills || []).map((s, i) => (
            <li key={i}><Ci c={s.who} size="sm" /><span className="d2-slot">{s.slot}</span>
              <span className="d2-sbar"><i style={{ width: `${(s.v / maxSk * 100).toFixed(0)}%` }} /></span><b>{num(s.v)}</b></li>
          ))}
        </ul>
      </div>
      <div>
        <span className="label">죽기 전 10초 체력</span>
        <HpLine hp={x.hp || []} end={x.sec} />
      </div>
      {kd && kd.what && (
        <div className="d2-why">
          <p><b>상황</b>{kd.what}</p>
          {kd.evidence && <p><b>근거</b>{kd.evidence}</p>}
        </div>
      )}
    </div>
  )
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

  const spells = (s) => (s.state !== 'each'
    ? <span className="muted">{s.state === 'none' ? '기록 없음' : '확인 못 함'}</span>
    : <span className="d2-spells">{s.list.map((sp) => (
      <span key={sp.key} className={cx('d2-sp', sp.verdict === 'held' && 'bad')}><Pi p={sp} cls="d2-sp-ic" />{SPELL_WORD[sp.verdict] || '확인 못 함'}</span>
    ))}</span>)

  const cells = X
    ? [
        ['교전 시간', X.fight ? <><span className="num">{ms(X.fight.from)}~{ms(X.fight.to)}</span><small>{X.fight.to - X.fight.from}초</small></> : <span className="muted">계산 못 함</span>],
        ['스펠', spells(X.spells)],
        ['보유 골드', <span className="num">{X.gold != null ? num(X.gold) : '—'}</span>],
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
              <button type="button" className={cx(mode === 'all' && 'on')} onClick={() => setMode('all')}>전체 지도</button>
              {rp && <button type="button" className={cx(mode === 'replay' && 'on')} onClick={() => setMode('replay')}>미니맵 리플레이</button>}
              {rp && mode === 'replay' && (
                <label className="d2-vis"><input type="checkbox" checked={vision} onChange={(e) => setVision(e.target.checked)} />추정 시야</label>
              )}
            </div>
            <div className="d2-frame">
              {mode === 'replay' && rp ? <Replay rp={rp} scene={scene} vision={vision} /> : <OverviewMap m={mapM} active={sel} onPick={pick} />}
            </div>
            {mode === 'replay' && rp && vision && <p className="d2-note">어두운 곳은 우리 팀 시야 밖으로 추정한 곳이에요. 벽과 수풀은 계산하지 않아서 실제와 다를 수 있어요. 시야 밖의 적은 흐리게 보여요.</p>}
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
              <ol>{keyRows.map((x) => <Row key={x.t} x={x} me={d.me} line={lineOf(x)} on={sel === x.no} onPick={() => pick(x.no)} />)}</ol>
            </>}
            {restRows.length > 0 && <>
              <h4 className="d2-lh">{keyRows.length ? '다른 죽음' : `죽음 ${D.total}`}</h4>
              <ol>{restRows.map((x) => <Row key={x.t} x={x} me={d.me} line={lineOf(x)} on={sel === x.no} onPick={() => pick(x.no)} />)}</ol>
            </>}
            {X ? <Detail x={X} kd={kdOf[X.t]} />
              : <p className="muted small d2-hint">{rp ? '죽음을 고르면 그 교전을 리플레이로 다시 보여 줘요. 한 번 더 누르면 전체로 돌아가요.' : '죽음을 고르면 자세한 내용이 여기에 나와요.'}</p>}
          </div>
        </div>
        <Strip cells={cells} />
      </div>
    </Section>
  )
}
