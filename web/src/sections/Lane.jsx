import { Section, Ci, BfRow, cx } from '../ui.jsx'

// 라인전 동안 아군 서폿이 바텀에 있었는지(1분마다)와, 있을 때/없을 때로 나눈 CS
function Support({ s }) {
  return (
    <div className="sup">
      <h3 className="panel-title">아군 서폿 위치</h3>
      <div className="sup-strip">{s.atBot.map((c) => <span key={c.min} className={c.in ? 'in' : ''}>{c.min}</span>)}</div>
      <div className="sup-foot">
        <ul className="legend"><li><span className="lg lg-sup-in" />바텀에 있음</li><li><span className="lg lg-sup-out" />바텀에 없음</li></ul>
      </div>
      <div className="sup-cs">
        <div><span className="label">서폿이 있을 때 CS</span><b>{s.with.me} : {s.with.opp}</b></div>
        <div><span className="label">서폿이 없을 때 CS</span><b>{s.without.me} : {s.without.opp}</b></div>
      </div>
    </div>
  )
}

export default function Lane({ d, fb }) {
  const L = d.lane
  const me = d.me.n, opp = d.opp.n
  const bk = L.botAdcKills
  return (
    <Section no="03">
      <div className="lane-grid">
        <div className="panel">
          <div className="bf-head">
            <span className="bf-who"><Ci c={d.me} size="sm" /><span className="me-name">{me}</span></span>
            <span className="bf-who">{opp}<Ci c={d.opp} size="sm" /></span>
          </div>
          <div className="bf">{L.rows.map((r) => <BfRow key={r.label} label={r.label} mine={r.me} theirs={r.opp} />)}</div>
          {L.support && <Support s={L.support} />}
        </div>
        <div className="panel">
          <div className="lane-facts">
            <div><span className="label">2레벨 선점</span><b className={L.first2 ? 'me-name' : ''}>{L.first2 ? me : opp}</b></div>
            {bk ? (
              <div>
                <span className="label" title="14분까지 바텀 근처에서 원딜이 죽은 횟수. 서폿이 막타를 친 것도 셉니다.">바텀 원딜 킬</span>
                <b className={cx('num', bk.opp > bk.me && 'pos')}>{bk.opp} : {bk.me}</b>
              </div>
            ) : (
              <div><span className="label">라인전 솔로킬</span><b className="num">{L.soloKills.me} : {L.soloKills.opp}</b></div>
            )}
            <div><span className="label">최대 CS 우위</span><b className="pos">+{L.maxCsAdv}</b></div>
          </div>
          <h3 className="panel-title">레벨 도달 시간</h3>
          <div className="lv-grid">
            <span className="lv-h lv-n">레벨</span>
            {L.levels.map((v) => <span key={v.lv} className="lv-n">{v.lv}</span>)}
            <span className="lv-h">{me}</span>
            {L.levels.map((v) => <span key={v.lv} className={v.meAhead ? 'ahead' : ''}>{v.me}</span>)}
            <span className="lv-h">{opp}</span>
            {L.levels.map((v) => <span key={v.lv} className={v.oppAhead ? 'behind' : ''}>{v.opp}</span>)}
          </div>
          <p className="body">{(fb && fb.laneText) || ''}</p>
        </div>
      </div>
    </Section>
  )
}
