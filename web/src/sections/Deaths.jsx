import { Fragment } from 'react'
import { Section, Ci, Faces, LostList, ChipPhase, Pi, MAP_IMG, num, signed, cx } from '../ui.jsx'

function DeathMap({ m }) {
  const S = m.size
  return (
    <svg className="map" viewBox={`0 0 ${S} ${S}`} role="img" aria-label="소환사의 협곡에서 내가 죽은 곳과 킬한 곳">
      <image href={MAP_IMG} x="0" y="0" width={S} height={S} className="map-img" />
      <rect className="map-veil" x="0" y="0" width={S} height={S} />
      {m.kills.map((p, i) => (
        <g key={`k${i}`}>
          <title>{p.t} {p.solid ? '킬' : '어시스트'}</title>
          <rect className={p.solid ? 'mp-kill' : 'mp-assist'} x={(p.x - 6.5).toFixed(1)} y={(p.y - 6.5).toFixed(1)}
            width="13" height="13" transform={`rotate(45 ${p.x.toFixed(1)} ${p.y.toFixed(1)})`} />
        </g>
      ))}
      {m.deaths.map((p) => (
        <g key={`d${p.no}`}>
          <title>{p.t} {p.no}번째 죽음</title>
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

function DeathCard({ x, me, kd }) {
  return (
    <article className="dcard">
      <header className="dcard-head">
        <span className="dnum">{x.no ?? ''}</span>
        <time>{x.t}</time>
        <ChipPhase phase={x.phase} />
        <span className="dzone">{x.zone}</span>
      </header>
      <div className="dcard-kill">
        <div className="kchain">
          <Ci c={x.killer} size="md" />
          {x.assists.length > 0 && <span className="kchain-plus"><Faces list={x.assists} /></span>}
        </div>
        <span className="karrow" aria-hidden="true" />
        <div className="kvictim"><Ci c={me} size="md" extra="is-dead" /></div>
      </div>
      <dl className="dfacts">
        <div><dt>근처 아군</dt><dd><Faces list={x.alliesNear} /></dd></div>
        <div><dt>근처 적</dt><dd><Faces list={x.enemiesNear} /></dd></div>
        <div><dt>보유 골드</dt><dd className="num">{x.gold != null ? num(x.gold) : '계산 불가'}</dd></div>
        <div><dt>스펠</dt><dd className="d-spells"><DeathSpells s={x.spells} /></dd></div>
        <div><dt>팀 골드 차이</dt><dd className={cx('num', x.teamGoldDiff < 0 && 'neg')}>{signed(x.teamGoldDiff)}</dd></div>
        <div><dt title="죽은 뒤 90초 안에 잃은 포탑/오브젝트">손해</dt><dd><LostList lost={x.lostAfter} /></dd></div>
      </dl>
      {x.roams.length > 0 ? (
        <ul className="roams">
          <li className="roams-h">합류한 적</li>
          {x.roams.map((r, i) => <li key={i}><Ci c={r.who} size="xs" /><span><span className="num">{r.minuteMark}</span> {r.wasAt}</span></li>)}
        </ul>
      ) : <div className="roams-slot" />}
      <div className="dcard-dmg"><span className="label">받은 피해</span><DamageBar dmg={x.damage} /></div>
      {kd && (
        <div className="dcard-text">
          <p><b>상황</b><span>{kd.what}</span></p>
          <p><b>근거</b><span>{kd.evidence}</span></p>
          <p className="next"><b>개선점</b><span>{kd.next}</span></p>
        </div>
      )}
    </article>
  )
}

export default function Deaths({ d, fb }) {
  const D = d.deaths
  const byT = Object.fromEntries(D.list.map((x) => [x.t, x]))
  // 피드백 글이 있으면 글에서 고른 죽음만 카드로, 나머지는 표로. 글이 없으면 모든 죽음을 카드로 보여 줘요.
  const key = fb ? fb.keyDeaths.filter((kd) => byT[kd.t]) : D.list.map((x) => ({ t: x.t }))
  const keyT = new Set(key.map((kd) => kd.t))
  const other = fb ? D.list.filter((x) => !keyT.has(x.t)) : []
  const otherText = (fb && fb.otherDeaths) || {}
  const dur = d.hero.durationSec
  return (
    <Section no="04">
      <div className="death-top">
        <div className="panel map-panel">
          <DeathMap m={D.map} />
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
      {key.length > 0 && (
        <>
          <h3 className="sub-h">{fb ? '주요 죽음' : '죽음'}</h3>
          <div className="dcards">{key.map((kd) => <DeathCard key={kd.t} x={byT[kd.t]} me={d.me} kd={fb ? kd : null} />)}</div>
        </>
      )}
      {other.length > 0 && (
        <>
          <h3 className="sub-h">나머지 죽음</h3>
          <div className="table-wrap"><table className="tbl">
            <thead><tr><th>#</th><th>시간</th><th>구간</th><th>처치</th><th>내용</th><th title="죽은 뒤 90초 안에 잃은 포탑/오브젝트">손해</th></tr></thead>
            <tbody>
              {other.map((x) => (
                <tr key={x.t}>
                  <td><span className="dnum">{x.no ?? ''}</span></td>
                  <td className="num">{x.t}</td>
                  <td><ChipPhase phase={x.phase} /></td>
                  <td className="faces"><Ci c={x.killer} size="xs" />{x.assists.length > 0 && <Faces list={x.assists} />}</td>
                  <td>{otherText[x.t] || ''}</td>
                  <td><LostList lost={x.lostAfter} /></td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </>
      )}
    </Section>
  )
}
