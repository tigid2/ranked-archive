import { useEffect, useState } from 'react'
import { Ci, ItemsRow, Loadout, num, signed, fix, cx } from '../ui.jsx'
import { Roll, Count, Foil, reduceMotion } from '../fx.jsx'

// 이 판 전 점수 → 이 판 뒤 점수. 100점을 넘기면 한 단계 올라가고, 0점 아래로 내려가면 한 단계 내려가요.
const TIERS = ['아이언', '브론즈', '실버', '골드', '플래티넘', '에메랄드', '다이아몬드']
function stepTier(tier, up) {
  const m = /^(\S+)\s+([1-4])$/.exec(tier || '')
  if (!m) return null
  let t = TIERS.indexOf(m[1]), d = +m[2] + (up ? -1 : 1)
  if (t < 0) return null
  if (d < 1) { t += 1; d = 4 } else if (d > 4) { t -= 1; d = 1 }
  return TIERS[t] ? `${TIERS[t]} ${d}` : null
}
function lpBefore(rank) {
  const raw = rank.lp - rank.change
  if (raw < 0) return { lp: raw + 100, tier: stepTier(rank.tier, false), moved: 'up' }
  if (raw >= 100) return { lp: raw - 100, tier: stepTier(rank.tier, true), moved: 'down' }
  return { lp: raw, tier: rank.tier, moved: '' }
}

function LpChange({ rank }) {
  const b = lpBefore(rank)
  const still = reduceMotion()
  // 단계: 0 = 이 판 전, 1 = 줄 끝까지(승급/강등일 때만), 2 = 이 판 뒤
  const [ph, setPh] = useState(still ? 2 : 0)
  const [run, setRun] = useState(0)
  useEffect(() => {
    if (still) return undefined
    setPh(0)
    const ts = b.moved
      ? [setTimeout(() => setPh(1), 700), setTimeout(() => setPh(2), 1500)]
      : [setTimeout(() => setPh(2), 700)]
    return () => ts.forEach(clearTimeout)
  }, [run]) // eslint-disable-line react-hooks/exhaustive-deps
  const after = ph === 2
  const lp = after ? rank.lp : b.lp
  const pos = ph === 0 ? b.lp : ph === 1 ? (b.moved === 'up' ? 100 : 0) : rank.lp
  const jump = ph === 2 && b.moved  // 줄 반대쪽 끝에서 다시 시작
  const gain = rank.change > 0
  return (
    <button type="button" className={cx('hero-lp lpx', after && 'is-after')} onClick={() => setRun((n) => n + 1)} title="누르면 점수 변화를 다시 보여 줘요">
      <span className="lpx-tier">
        {b.moved && b.tier ? <><span className={cx('lpx-from', after && 'off')}>{b.tier}</span><i aria-hidden="true">→</i><span className={cx('lpx-to', after && 'on')}>{rank.tier}</span></> : <span className="lpx-to on">{rank.tier}</span>}
        {b.moved && <span className={cx('chip', b.moved === 'up' ? 'chip-pos' : 'chip-mid', 'lpx-moved', after && 'on')}>{b.moved === 'up' ? '승급' : '강등'}</span>}
      </span>
      <span className="lpx-num">
        <span className={cx('lpx-delta', gain ? 'pos' : 'neg', after && 'on')}>{signed(rank.change)}</span>
        <span className="lp-num"><Roll value={lp} digits={2} /><small>LP</small></span>
      </span>
      <span className="lpx-line" aria-hidden="true">
        <span className="lpx-fill" style={{ left: `${Math.min(b.moved ? (b.moved === 'up' ? 0 : rank.lp) : Math.min(b.lp, rank.lp), 100)}%`, width: `${after ? (b.moved ? (b.moved === 'up' ? rank.lp : 100 - rank.lp) : Math.abs(rank.change)) : 0}%` }} />
        <span className={cx('lpx-mark', jump && `jump-${b.moved}`)} style={{ left: `${pos}%` }} />
        <span className="lpx-ghost" style={{ left: `${b.lp}%` }} />
      </span>
      <span className="lpx-ends" aria-hidden="true"><span>0</span><span>이 판 전 {b.lp} → 이 판 뒤 {rank.lp}</span><span>100</span></span>
    </button>
  )
}

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
            <h1><span className="res"><Foil radius={130} area=".hero">{h.win ? '승리' : '패배'}</Foil></span><span className="dur">{Math.floor(dur / 60)}:{String(dur % 60).padStart(2, '0')}</span></h1>
            <p className="hero-match">
              <Ci c={h.match.me} size="sm" /><Ci c={h.match.duo} size="sm" />
              <span className="vs">VS</span>
              <Ci c={h.match.opp} size="sm" /><Ci c={h.match.eduo} size="sm" />
            </p>
          </div>
        </div>
        {h.rank && (h.rank.change != null ? <LpChange rank={h.rank} /> : (
          <div className="hero-lp">
            <span className="lp-tier">{h.rank.tier}</span>
            <span className="lp-num">{h.rank.lp}<small>LP</small></span>
          </div>
        ))}
      </div>
      <div className="hero-items"><ItemsRow items={h.items} size="md" /></div>
      <div className="tiles">
        <Tile label="KDA" value={<>{k}<i>/</i><span className="death">{de}</span><i>/</i>{a}</>}
          sub={`평점 ${fix(h.kdaRatio, 2)}`} cmp={`킬 관여 ${h.kp}%`} />
        <Tile label="CS" value={<Count to={h.cs} />} sub={`분당 ${fix(h.csPerMin, 1)}`} cmp={`${opp} ${h.oppCs}`} />
        <Tile label="챔피언 피해" value={<Count to={h.dmg} fmt={num} />} sub={`팀 내 ${h.dmgShare}%`} cmp={`${opp} ${num(h.oppDmg)}`} />
        <Tile label="골드" value={<Count to={h.gold} fmt={num} />} sub={`분당 ${fix(h.goldPerMin, 0)}`} cmp={`${opp} ${num(h.oppGold)}`} />
        <Tile label="15분 맞라인 골드" value={<span className={h.lane15.gold < 0 ? 'neg' : ''}>{signed(h.lane15.gold)}</span>}
          sub={`${d.oppWith} 비교`} cmp={`CS ${signed(h.lane15.cs)}`} />
        <Tile label="시야 점수" value={<Count to={h.vision} />} sub={`와드 ${h.wards}개 설치`} cmp={`제어 와드 ${h.controlWards}개`} />
      </div>
    </section>
  )
}
