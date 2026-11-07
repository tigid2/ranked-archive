// 여러 섹션에서 같이 쓰는 작은 조각: 숫자 모양, 아이콘, 섹션 틀
import mapUrl from '../../data/map11_gray.png'

const CDN = 'https://ddragon.leagueoflegends.com/cdn/'

// 아이콘 주소. artifact용 한 파일은 window.__ASSETS__ 안에 그림이 들어 있어요.
export const src = (ref) => (!ref ? '' : (window.__ASSETS__ && window.__ASSETS__[ref]) || CDN + ref)
export const MAP_IMG = mapUrl

export const num = (n) => Number(n).toLocaleString('en-US')
export const signed = (n) => (n > 0 ? '+' : n < 0 ? '−' : '±') + Math.abs(n).toLocaleString('en-US')
export const mmss = (ms) => {
  const s = Math.floor(ms / 1000)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
export const fix = (n, d) => Number(n).toFixed(d)
export const cx = (...a) => a.filter(Boolean).join(' ')

export const SECTIONS = [['01', '경기 요약'], ['02', '경기 흐름'], ['03', '라인전'], ['04', '죽음'],
  ['05', '팀 기록'], ['06', '빌드'], ['07', '체크리스트'], ['08', '메모']]

export function Section({ no, children }) {
  const title = Object.fromEntries(SECTIONS)[no]
  return (
    <section className="sec" id={`s${no}`}>
      <header className="sec-head"><span className="sec-no" aria-hidden="true">{no}</span><h2>{title}</h2></header>
      {children}
    </section>
  )
}

// 그림 아이콘(글자 대신 쓰는 것)
export const Gi = ({ name, cls = 'gi' }) => (
  <svg className={cls} aria-hidden="true"><use href={`#i-${name}`} /></svg>
)

export const SPRITE = `<svg class="sprite" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<symbol id="i-dragon" viewBox="0 0 24 24"><path d="M3 20 8 10 6 3l5 4 4-3-1 5 7 2-5 3 1 6-5-4z"/></symbol>
<symbol id="i-baron" viewBox="0 0 24 24"><path d="M6 9 7.5 3 10 7l2-4 2 4 2.5-4L18 9z"/><path fill-rule="evenodd" d="M4 21c0-7 3.5-11 8-11s8 4 8 11l-4-2.5-4 2.5-4-2.5zm8-8a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"/></symbol>
<symbol id="i-herald" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M1.5 12C5 5.5 19 5.5 22.5 12 19 18.5 5 18.5 1.5 12zm10.5-4a4 4 0 1 0 0 8 4 4 0 0 0 0-8zm0 2.4a1.6 1.6 0 1 1 0 3.2 1.6 1.6 0 0 1 0-3.2z"/></symbol>
<symbol id="i-grub" viewBox="0 0 24 24"><circle cx="12" cy="7" r="4"/><circle cx="6.5" cy="16" r="4"/><circle cx="17.5" cy="16" r="4"/></symbol>
<symbol id="i-tower" viewBox="0 0 24 24"><path d="M6 3h3v2h2V3h2v2h2V3h3v6l-2 2 1 10H7l1-10-2-2z"/></symbol>
<symbol id="i-inhib" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M12 1.5 20.5 12 12 22.5 3.5 12zm0 5.5L8 12l4 5 4-5z"/></symbol>
<symbol id="i-atakhan" viewBox="0 0 24 24"><path d="M3 2c1.5 6 4.5 9 9 9s7.5-3 9-9c1.5 8-1.5 14-9 20C4.5 16 1.5 10 3 2z"/></symbol>
<symbol id="i-minion" viewBox="0 0 24 24"><path d="M12 2 20 5.5V12c0 4.5-3.2 8-8 10-4.8-2-8-5.5-8-10V5.5z"/></symbol>
</svg>`

// 챔피언 아이콘. 챔피언이 아니면(미니언, 포탑 등) 그림 아이콘
export function Ci({ c, size = 'md', extra, title }) {
  if (!c || !c.k) {
    const t = title || (c && c.n) || '?'
    return <span className={cx('ic', `ic-${size}`, 'ic-glyph', extra)} title={t}><Gi name={(c && c.glyph) || 'minion'} /></span>
  }
  const t = title || c.n
  return <img className={cx('ic', `ic-${size}`, extra)} src={src(c.img)} alt={t} title={t} />
}

// 아이템 아이콘. 빈 칸이면 빈 상자
export function Ii({ it, size = 'sm', extra }) {
  if (!it) return <span className={cx('ic', `ic-${size}`, 'ic-empty', extra)} />
  return <img className={cx('ic', `ic-${size}`, extra)} src={src(it.img)} alt={it.n} title={it.n} />
}

// 룬·스펠처럼 이름과 그림만 있는 아이콘
export const Pi = ({ p, cls }) => <img className={cls} src={src(p.img)} alt={p.n} title={p.n} />

// OP.GG식: 초상화 + 레벨 / 스펠 2개 / 핵심 룬 + 보조 빌드
export function Loadout({ lo, big }) {
  return (
    <div className={cx('loadout', big && 'loadout-big')}>
      <div className="portrait"><Ci c={lo.champ} size={big ? 'xl' : 'md'} /><span className="lvl">{lo.level}</span></div>
      <div className="loadout-grid">
        <Pi p={lo.spells[0]} cls="ic ic-xs" />
        <Pi p={lo.keystone} cls="ic ic-xs ic-rune" />
        <Pi p={lo.spells[1]} cls="ic ic-xs" />
        <Pi p={lo.subStyle} cls="ic ic-xs ic-rune ic-style" />
      </div>
    </div>
  )
}

export function ItemsRow({ items, size = 'sm' }) {
  return (
    <div className="items">
      {items.slice(0, 6).map((it, i) => <Ii key={i} it={it} size={size} />)}
      <span className="trinket"><Ii it={items[6]} size={size} /></span>
    </div>
  )
}

// 양쪽 비교 막대 (나 vs 상대, 우리 팀 vs 상대 팀)
export function BfRow({ label, mine, theirs, fmt = num, neutral }) {
  const tot = Math.max(mine + theirs, 1)
  const lw = mine + theirs ? (mine / tot) * 100 : 50
  const win = neutral ? '' : mine > theirs ? 'mine' : theirs > mine ? 'theirs' : ''
  return (
    <div className={cx('bf-row', win)}>
      <span className="bf-v bf-l">{fmt(mine)}</span>
      <div className="bf-bar"><span className="bf-a" style={{ width: `${lw.toFixed(1)}%` }} /><span className="bf-b" style={{ width: `${(100 - lw).toFixed(1)}%` }} /></div>
      <span className="bf-v bf-r">{fmt(theirs)}</span>
      <span className="bf-label">{label}</span>
    </div>
  )
}

export const ChipPhase = ({ phase }) => <span className="chip chip-line">{phase}</span>

export function Faces({ list, size = 'xs' }) {
  if (!list || !list.length) return <span className="muted">없음</span>
  return list.map((c, i) => <Ci key={i} c={c} size={size} title={c.n} />)
}

export function LostList({ lost }) {
  if (!lost || !lost.length) return <span className="muted">없음</span>
  return lost.map((x, i) => <span key={i} className="lost">{x}</span>)
}

// 괄호 안 근거는 연한 글자로
export function Lede({ text }) {
  const parts = []
  const re = /\(([^)]*)\)/g
  let last = 0, m
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(text.slice(last, m.index))
    parts.push(<span key={m.index} className="aside">({m[1]})</span>)
    last = re.lastIndex
  }
  parts.push(text.slice(last))
  return <p className="lede">{parts}</p>
}

// 피드백 글이 아직 없을 때 보여 주는 칸
export const Pending = ({ text }) => <div className="memo is-empty"><p>{text}</p></div>
