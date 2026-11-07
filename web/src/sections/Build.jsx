import { Section, Ci, Ii, Pi, src, mmss, fix, cx } from '../ui.jsx'

const srcOf = (p) => src(p.img)

// 완성 아이템을 시간 축 위에 놓아서 나와 맞라인 상대의 성장 속도를 바로 비교해요.
function ItemTimeline({ d, fb }) {
  const dur = d.hero.durationSec
  const pos = (t) => t / (dur * 1000) * 100
  const mine = d.build.timeline.me
  let gap = null
  if (mine.length >= 2) {
    // 피드백 글에서 짚은 구간을 표시해요. 'gapAfter'가 n이면 n번째와 n+1번째 완성 아이템 사이 (기본 1)
    const j = Math.min(parseInt((fb && fb.build && fb.build.gapAfter) || 1, 10) - 1, mine.length - 2)
    const t1 = mine[j].t, t2 = mine[j + 1].t
    gap = (
      <>
        <span className="itl-gap" style={{ left: `${pos(t1).toFixed(2)}%`, width: `${(pos(t2) - pos(t1)).toFixed(2)}%` }} title="완성 아이템 사이 시간" />
        <span className="itl-gap-l" style={{ left: `${((pos(t1) + pos(t2)) / 2).toFixed(2)}%` }}>{mmss(t2 - t1)}</span>
      </>
    )
  }
  const row = (list, c, cls, extra) => (
    <div className={cx('itl-row', cls)}>
      <div className="itl-who"><Ci c={c} size="sm" /><span className={cls === 'mine' ? 'me-name' : ''}>{c.n}</span></div>
      <div className="itl-track">
        {extra}
        {list.map((x, i) => <div key={i} className="itl-it" style={{ left: `${pos(x.t).toFixed(2)}%` }}><Ii it={x.item} size="sm" /><time>{mmss(x.t)}</time></div>)}
      </div>
    </div>
  )
  const ticks = []
  for (let m = 0; m <= Math.floor(dur / 60); m += 5) ticks.push(m)
  return (
    <div className="itl">
      {row(mine, d.me, 'mine', gap)}
      {row(d.build.timeline.opp, d.opp, 'theirs')}
      <div className="itl-axis"><div /><div>{ticks.map((m) => <span key={m} style={{ left: `${(m * 60000 / (dur * 1000) * 100).toFixed(2)}%` }}>{m}:00</span>)}</div></div>
    </div>
  )
}

const Note = ({ t }) => (t ? <p className="body">{t}</p> : null)

export default function Build({ d, fb }) {
  const B = d.build
  const R = B.runes
  const fbb = (fb && fb.build) || {}
  const cell = (p, cls, key) => <div key={key} className={cx('r-cell', cls)}><Pi p={p} cls="ic ic-md ic-rune" /><span>{p.n}</span></div>
  return (
    <Section no="06">
      <div className="panel">
        <div className="panel-head"><h3>완성 아이템 시점</h3></div>
        <ItemTimeline d={d} fb={fb} />
        <Note t={fbb['아이템']} />
        <div className="buys">
          <h3 className="panel-title">전체 구매 순서</h3>
          <ol className="bt-list">
            {B.buys.map((g, i) => (
              <li key={i}>
                <div className="bt-items">{g.items.map((it, j) => (it.done ? <Ii key={j} it={it} size="md" extra="is-core" /> : <Ii key={j} it={it} size="xs" />))}</div>
                <time>{mmss(g.t)}</time>
              </li>
            ))}
          </ol>
        </div>
      </div>
      <div className="build-grid">
        <div className="panel">
          <h3 className="panel-title">룬</h3>
          <div className="runes">
            <div className="r-h p"><img className="ic ic-xs ic-rune" src={srcOf(R.primary)} alt="" />{R.primary.n}</div>
            <div className="r-h s"><img className="ic ic-xs ic-rune" src={srcOf(R.secondary)} alt="" />{R.secondary.n}</div>
            <div className="r-big p"><Pi p={R.keystone} cls="ic ic-lg ic-rune" /><span>{R.keystone.n}</span></div>
            {R.sub.map((p, j) => cell(p, j === 0 ? 'psub s1' : 'psub', `s${j}`))}
            {R.minor.map((p, j) => cell(p, 'pmin', `m${j}`))}
            <div className="r-shards">{R.shards.map((s, j) => <Pi key={j} p={s} cls="ic ic-rune" />)}</div>
          </div>
          <Note t={fbb['룬']} />
        </div>
        <div className="panel">
          <h3 className="panel-title">소환사 주문</h3>
          <ul className="spells">
            {B.spells.map((s) => <li key={s.key}><img className="ic ic-md" src={srcOf(s)} alt="" /><span>{s.n}</span><b>{s.casts}<small>번</small></b></li>)}
          </ul>
          <Note t={fbb['소환사 주문']} />
          <h3 className="panel-title panel-gap">스킬 사용</h3>
          <ul className="skills">
            {B.skills.map((s) => (
              <li key={s.key}>
                <span className="sk-k">{s.img && <img className="ic ic-xs" src={srcOf(s)} alt="" title={s.n} />}{s.key}</span>
                <b>{s.casts}</b><span className="muted">분당 {fix(s.perMin, 1)}</span>
              </li>
            ))}
          </ul>
          <p className="body small">논타깃 스킬 적중 {B.skillshotsHit}번, 피한 스킬 {B.skillshotsDodged}번</p>
        </div>
      </div>
    </Section>
  )
}

