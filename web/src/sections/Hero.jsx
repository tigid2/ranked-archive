import { Ci, ItemsRow, Loadout, num, signed, fix, cx } from '../ui.jsx'

function Tile({ label, value, sub, cmp }) {
  return (
    <div className="tile">
      <span className="label">{label}</span>
      <span className="tile-value">{value}</span>
      <span className="tile-sub">{sub}</span>
      {cmp && <span className="tile-cmp">{cmp}</span>}
    </div>
  )
}

export default function Hero({ d }) {
  const h = d.hero
  const [k, de, a] = h.kda
  const opp = d.opp.n
  const dur = h.durationSec
  return (
    <section className={cx('hero', h.win ? 'is-win' : 'is-loss')}>
      <div className="stripes" aria-hidden="true" />
      <div className="hero-top">
        <div className="hero-id">
          <Loadout lo={h.loadout} big />
          <div className="hero-title">
            <p className="hero-meta"><span>솔로랭크</span><span className="num">{h.when}</span><span>패치 {h.patch}</span></p>
            <h1><span className="res">{h.win ? '승리' : '패배'}</span><span className="dur">{Math.floor(dur / 60)}:{String(dur % 60).padStart(2, '0')}</span></h1>
            <p className="hero-match">
              <Ci c={h.match.me} size="sm" /><Ci c={h.match.duo} size="sm" />
              <span className="vs">VS</span>
              <Ci c={h.match.opp} size="sm" /><Ci c={h.match.eduo} size="sm" />
            </p>
          </div>
        </div>
        {h.rank && (
          <div className="hero-lp">
            <span className="lp-tier">{h.rank.tier}</span>
            <span className="lp-num">{h.rank.lp}<small>LP</small></span>
          </div>
        )}
      </div>
      <div className="hero-items"><ItemsRow items={h.items} size="md" /></div>
      <div className="tiles">
        <Tile label="KDA" value={<>{k}<i>/</i><span className="death">{de}</span><i>/</i>{a}</>}
          sub={`평점 ${fix(h.kdaRatio, 2)}`} cmp={`킬 관여 ${h.kp}%`} />
        <Tile label="CS" value={h.cs} sub={`분당 ${fix(h.csPerMin, 1)}`} cmp={`${opp} ${h.oppCs}`} />
        <Tile label="챔피언 피해" value={num(h.dmg)} sub={`팀 내 ${h.dmgShare}%`} cmp={`${opp} ${num(h.oppDmg)}`} />
        <Tile label="골드" value={num(h.gold)} sub={`분당 ${fix(h.goldPerMin, 0)}`} cmp={`${opp} ${num(h.oppGold)}`} />
        <Tile label="15분 맞라인 골드" value={<span className={h.lane15.gold < 0 ? 'neg' : ''}>{signed(h.lane15.gold)}</span>}
          sub={`${d.oppWith} 비교`} cmp={`CS ${signed(h.lane15.cs)}`} />
        <Tile label="시야 점수" value={String(h.vision)} sub={`와드 ${h.wards}개 설치`} cmp={`제어 와드 ${h.controlWards}개`} />
      </div>
    </section>
  )
}
