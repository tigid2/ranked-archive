import { Fragment, useEffect, useRef, useState } from 'react'
import { Follower } from '../fx.jsx'
import { Section, Ci, Faces, LostList, ChipPhase, Pi, MAP_IMG, num, signed, cx } from '../ui.jsx'

function DeathMap({ m, active, onHover, onPick, mini }) {
  const S = m.size
  return (
    <svg className={cx('map', mini && 'map-mini', active != null && 'has-active')} viewBox={`0 0 ${S} ${S}`} role="img" aria-label="소환사의 협곡에서 내가 죽은 곳과 킬한 곳">
      <image href={MAP_IMG} x="0" y="0" width={S} height={S} className="map-img" />
      {!mini && m.kills.map((p, i) => (
        <g key={`k${i}`} className="mp-k">
          <title>{p.t} {p.solid ? '킬' : '어시스트'}</title>
          <rect className={p.solid ? 'mp-kill' : 'mp-assist'} x={(p.x - 6.5).toFixed(1)} y={(p.y - 6.5).toFixed(1)}
            width="13" height="13" transform={`rotate(45 ${p.x.toFixed(1)} ${p.y.toFixed(1)})`} />
        </g>
      ))}
      {m.deaths.map((p) => (
        <g key={`d${p.no}`} className={cx('mp-d', active === p.no && 'on')} style={{ transformOrigin: `${p.x.toFixed(1)}px ${p.y.toFixed(1)}px` }}
          onPointerEnter={onHover && (() => onHover(p.no))} onPointerLeave={onHover && (() => onHover(null))} onClick={onPick && (() => onPick(p.no))}>
          <title>{p.t} {p.no}번째 죽음</title>
          {active === p.no && <circle className="mp-ring" cx={p.x.toFixed(1)} cy={p.y.toFixed(1)} r="12" />}
          <circle className="mp-death" cx={p.x.toFixed(1)} cy={p.y.toFixed(1)} r="12" />
          <text className="mp-num" x={p.x.toFixed(1)} y={(p.y + 4.5).toFixed(1)} textAnchor="middle">{p.no}</text>
        </g>
      ))}
    </svg>
  )
}

// 죽을 때 스펠 2개의 상태 (게임 중 기록에서)
function DeathSpells({ s }) {
  const icon = (sp) => <Pi p={sp} cls="ic ic-xs" />
  if (s.state !== 'each') {
    return <>{s.list.map((sp) => <Fragment key={sp.key}>{icon(sp)}</Fragment>)}<span className="no-rec">{s.state === 'none' ? '기록 없음' : '확인 못 함'}</span></>
  }
  return s.list.map((sp) => (
    <span key={sp.key} className="d-spell">
      {icon(sp)}
      {sp.verdict ? <span className={`chip chip-${sp.tone}`}>{sp.label}</span> : <span className="no-rec">확인 못 함</span>}
    </span>
  ))
}

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

// 죽음 한 줄. 누르면 자세한 내용이 펼쳐지고 나머지 줄은 흐려져요.
function DeathRow({ x, me, kd, note, open, dim, onToggle, onHover }) {
  return (
    <li className={cx('drow', open && 'open', dim && 'dim')} id={`death-${x.no}`}>
      <button type="button" className="drow-head" aria-expanded={open} onClick={onToggle}
        onPointerEnter={() => onHover(x.no)} onPointerLeave={() => onHover(null)}>
        <span className="dnum">{x.no ?? ''}</span>
        <time>{x.t}</time>
        <ChipPhase phase={x.phase} />
        <span className="drow-zone">{x.zone}</span>
        <span className="drow-kill">
          <Ci c={x.killer} size="sm" />
          {x.assists.length > 0 && <span className="kchain-plus"><Faces list={x.assists} /></span>}
          <span className="karrow" aria-hidden="true" />
          <Ci c={me} size="sm" extra="is-dead" />
        </span>
        <span className="drow-lost" title="죽은 뒤 90초 안에 잃은 포탑/오브젝트">
          {x.lostAfter.length > 0 ? <LostList lost={x.lostAfter} /> : <span className="muted">손해 없음</span>}
        </span>
        <span className="drow-x" aria-hidden="true" />
      </button>
      {(kd && kd.next) || note ? <p className="drow-note">{kd && kd.next ? <><b>개선점</b>{kd.next}</> : note}</p> : null}
      <div className="drow-body"><div><div className="drow-grid">
        <div>
          <dl className="dfacts">
            <div><dt>근처 아군</dt><dd><Faces list={x.alliesNear} /></dd></div>
            <div><dt>근처 적</dt><dd><Faces list={x.enemiesNear} /></dd></div>
            <div><dt>보유 골드</dt><dd className="num">{x.gold != null ? num(x.gold) : '계산 불가'}</dd></div>
            <div><dt>스펠</dt><dd className="d-spells"><DeathSpells s={x.spells} /></dd></div>
            <div><dt>팀 골드 차이</dt><dd className={cx('num', x.teamGoldDiff < 0 && 'neg')}>{signed(x.teamGoldDiff)}</dd></div>
            <div><dt title="죽은 뒤 90초 안에 잃은 포탑/오브젝트">손해</dt><dd><LostList lost={x.lostAfter} /></dd></div>
          </dl>
          {x.roams.length > 0 && (
            <ul className="roams">
              <li className="roams-h">합류한 적</li>
              {x.roams.map((r, i) => <li key={i}><Ci c={r.who} size="xs" /><span><span className="num">{r.minuteMark}</span> {r.wasAt}</span></li>)}
            </ul>
          )}
        </div>
        <div>
          <div className="dcard-dmg"><span className="label">받은 피해</span><DamageBar dmg={x.damage} /></div>
          {kd && kd.what && (
            <div className="dcard-text">
              <p><b>상황</b><span>{kd.what}</span></p>
              <p><b>근거</b><span>{kd.evidence}</span></p>
            </div>
          )}
        </div>
      </div></div></div>
    </li>
  )
}

export default function Deaths({ d, fb }) {
  const D = d.deaths
  const byT = Object.fromEntries(D.list.map((x) => [x.t, x]))
  // 피드백 글이 있으면 글에서 고른 죽음만 카드로, 나머지는 표로. 글이 없으면 모든 죽음을 카드로 보여 줘요.
  const key = fb ? fb.keyDeaths.filter((kd) => byT[kd.t]) : D.list.map((x) => ({ t: x.t }))
  const otherText = (fb && fb.otherDeaths) || {}
  // 펼친 줄(open)과 마우스를 올린 줄(hover). 지도와 줄이 서로 같은 죽음을 가리켜요.
  const [open, setOpen] = useState(null)
  const [hover, setHover] = useState(null)
  const [fromRow, setFromRow] = useState(false)
  const active = hover ?? open
  // 큰 지도가 화면에 보이는 동안에는 커서를 따라다니는 작은 지도를 띄우지 않아요.
  const mapRef = useRef(null)
  const [mapSeen, setMapSeen] = useState(true)
  useEffect(() => {
    const io = new IntersectionObserver((es) => setMapSeen(es[0].intersectionRatio > 0.5), { threshold: [0, 0.5, 1] })
    io.observe(mapRef.current)
    return () => io.disconnect()
  }, [])
  const kdOf = Object.fromEntries(key.map((kd) => [kd.t, kd]))
  const pick = (no) => {
    setOpen(no)
    const el = document.getElementById(`death-${no}`)
    if (el) el.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }
  return (
    <Section no="04">
      <div className="death-top">
        <div className="panel map-panel" ref={mapRef}>
          <DeathMap m={D.map} active={active} onHover={(no) => { setHover(no); setFromRow(false) }} onPick={pick} />
          <ul className="legend legend-map">
            <li><span className="lg lg-mdeath" />죽은 곳</li>
            <li><span className="lg lg-mkill" />킬</li>
            <li><span className="lg lg-massist" />어시스트</li>
          </ul>
        </div>
        <div className="death-stats">
          <div className="big-stat"><span className="big-n">{D.total}</span><span className="big-l">데스</span></div>
          <div className="ptl"><div className="ptl-bar">
            {D.phases.map((p) => (
              <div key={p.name} className="ptl-seg" style={{ flex: p.to - p.from }}>
                <div className="ptl-top"><span className="ptl-name">{p.name}</span><span className="ptl-n">{p.n}<small>번</small></span></div>
                <span className="ptl-range">{Math.floor(p.from / 60)}:00 ~ {Math.floor(p.to / 60)}:{String(p.to % 60).padStart(2, '0')}</span>
              </div>
            ))}
          </div></div>
          <div className="zones">
            <span className="label">죽은 위치</span>
            <div className="zone-row">{D.zones.map((z) => <div key={z.name}><span className="label">{z.name}</span><b>{z.n}</b></div>)}</div>
          </div>
          <ul className="dlist-stats">
            <li><span className="ds-n">{D.lostN}</span><span>죽은 뒤 90초 안에 포탑/오브젝트를 잃음</span></li>
            <li title="1분 전에 4,000 거리 넘게 떨어져 있던 적"><span className="ds-n">{D.roamN}</span><span>멀리서 합류한 적에게 죽음</span></li>
            <li><span className="ds-n">{D.alone}</span><span>근처에 아군 없이 죽음</span></li>
          </ul>
        </div>
      </div>
      {D.list.length > 0 && (
        <>
          <div className="drows-h"><h3 className="sub-h">죽음</h3><span className="muted small">줄이나 지도의 번호를 누르면 자세한 내용이 펼쳐져요.</span></div>
          <ol className={cx('drows', open != null && 'has-open')}>
            {D.list.map((x) => (
              <DeathRow key={x.t} x={x} me={d.me} kd={fb ? kdOf[x.t] : null} note={otherText[x.t]}
                open={open === x.no} dim={open != null && open !== x.no}
                onToggle={() => setOpen(open === x.no ? null : x.no)}
                onHover={(no) => { setHover(no); setFromRow(no != null) }} />
            ))}
          </ol>
          <Follower show={fromRow && hover != null && !mapSeen}>
            <DeathMap m={D.map} active={hover} mini />
          </Follower>
        </>
      )}
    </Section>
  )
}
