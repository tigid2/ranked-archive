import { Section, Loadout, ItemsRow, BfRow, num, fix, cx } from '../ui.jsx'

function TeamTable({ t, maxDmg }) {
  const top = (on) => (on ? 't-top' : '')
  return (
    <div className={cx('team', t.ours ? 'team-ours' : 'team-theirs')}>
      <div className="team-head">
        <span className="team-name">{t.ours ? '우리 팀' : '상대 팀'}</span>
        <span className={cx('chip', t.win ? 'chip-pos' : 'chip-bad')}>{t.win ? '승리' : '패배'}</span>
        <span className="team-k num">{t.kills}킬</span>
      </div>
      <div className="table-wrap"><table className="tbl tbl-team">
        <colgroup><col className="c-pos" /><col className="c-champ" /><col className="c-kda" /><col className="c-dmg" /><col className="c-gold" /><col className="c-cs" /><col className="c-vis" /><col className="c-items" /></colgroup>
        <thead><tr><th></th><th>챔피언</th><th>KDA</th><th>챔피언 피해</th><th>골드</th><th>CS</th><th>시야</th><th className="t-items">아이템</th></tr></thead>
        <tbody>
          {t.players.map((p, i) => (
            <tr key={i} className={p.me ? 'is-me' : ''}>
              <td className="t-pos">{p.pos}</td>
              <td className="t-champ-td"><div className="t-champ"><Loadout lo={p.loadout} /><span className="t-name">{p.loadout.champ.n}</span></div></td>
              <td className="t-kda">
                <span className="num">{p.kda[0]} / {p.kda[1]} / {p.kda[2]}</span>
                <span className="t-sub">평점 {fix(p.kdaRatio, 2)}, 관여 <span className={top(p.topKp)}>{p.kp}%</span></span>
              </td>
              <td className="t-dmg"><span className={cx('num', top(p.topDmg))}>{num(p.dmg)}</span><span className="t-bar"><i style={{ width: `${(p.dmg / maxDmg * 100).toFixed(1)}%` }} /></span></td>
              <td className={cx('num', top(p.topGold))}>{num(p.gold)}</td>
              <td className={cx('num', top(p.topCs))}>{p.cs}</td>
              <td className="num">{p.vision}</td>
              <td className="t-items"><ItemsRow items={p.items} size="xs" /></td>
            </tr>
          ))}
        </tbody>
      </table></div>
    </div>
  )
}

export default function Team({ d }) {
  const T = d.team
  const head = <div className="bf-head"><span className="bf-who">우리 팀</span><span className="bf-who">상대 팀</span></div>
  const rows = T.compare.map((r) => <BfRow key={r.label} label={r.label} mine={r.v[0]} theirs={r.v[1]} neutral={r.neutral} />)
  return (
    <Section no="05">
      <div className="panel team-cmp"><div className="bf-team">
        {[0, 5].map((i) => <div key={i}>{head}<div className="bf">{rows.slice(i, i + 5)}</div></div>)}
      </div></div>
      <TeamTable t={T.ours} maxDmg={T.maxDmg} />
      <TeamTable t={T.theirs} maxDmg={T.maxDmg} />
    </Section>
  )
}
