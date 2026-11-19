// 여러 섹션에서 같이 쓰는 작은 조각: 숫자 모양, 아이콘, 섹션 틀
import mapUrl from '../../data/map-rift-dark.svg'
import { useInView } from './fx.jsx'

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
  const [ref, seen] = useInView()
  return (
    <section className={seen ? 'sec in' : 'sec'} id={`s${no}`} ref={ref}>
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
<symbol id="i-dragon" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M5.3 16.5 L7.5 14 L2.5 10 L8.5 8.5 L4 2.5 L11 5 L15 5 L21.5 8.5 L20.5 11.5 L14.5 11.5 L13 12.2 L14.5 13 L19.2 13 L18.5 15.5 L11.5 15.5 L9.2 19.5 Z M12.5 7.5 L14.5 7.1 L16.5 8.5 L14.5 8.9 Z" /></symbol>
<symbol id="i-baron" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M 12 2 L 14 5.2 L 18 3.5 L 16.5 6.8 L 21.8 9 L 21.2 12.2 L 18.8 14 L 17.2 20.5 L 12 21.5 L 6.8 20.5 L 5.2 14 L 2.8 12.2 L 2.2 9 L 7.5 6.8 L 6 3.5 L 10 5.2 Z M 10.1 7 L 11.2 8.2 L 10.1 9.4 L 9 8.2 Z M 13.9 7 L 15 8.2 L 13.9 9.4 L 12.8 8.2 Z M 8.6 10.3 L 9.7 11.5 L 8.6 12.7 L 7.5 11.5 Z M 15.4 10.3 L 16.5 11.5 L 15.4 12.7 L 14.3 11.5 Z M 12 13.8 L 8.2 15.2 L 7.8 17.8 L 9.8 16.6 L 12 18.2 L 14.2 16.6 L 16.2 17.8 L 15.8 15.2 Z" /></symbol>
<symbol id="i-herald" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M 8.6 2.5 L 9.4 6 L 14.6 6 L 15.4 2.5 L 19.6 6 L 20.2 11.2 L 17.8 16.2 L 14.4 19.8 L 9.6 19.8 L 6.2 16.2 L 3.8 11.2 L 4.4 6 Z M 12 7.6 L 15.8 10.3 L 15.8 15.3 L 12 18 L 8.2 15.3 L 8.2 10.3 Z" /> <polygon points="12,9.7 13.8,12.8 12,15.9 10.2,12.8" /> <polygon points="3.3,14.8 6.1,19.8 2,19.8" /> <polygon points="20.7,14.8 22,19.8 17.9,19.8" /></symbol>
<symbol id="i-grub" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M 9.4 5.5 L 9.8 4.5 L 11 5.5 L 13 5.5 L 14.2 4.5 L 14.6 5.5 L 15.8 6.7 L 15.8 9.7 L 14.4 11.1 L 9.6 11.1 L 8.2 9.7 L 8.2 6.7 Z M 10 7.5 L 14 7.5 L 14 9.1 L 10 9.1 Z" /> <path fill-rule="evenodd" d="M 4.6 13.9 L 5 12.9 L 6.2 13.9 L 8.2 13.9 L 9.4 12.9 L 9.8 13.9 L 11 15.1 L 11 18.1 L 9.6 19.5 L 4.8 19.5 L 3.4 18.1 L 3.4 15.1 Z M 5.2 15.9 L 9.2 15.9 L 9.2 17.5 L 5.2 17.5 Z" /> <path fill-rule="evenodd" d="M 14.2 13.9 L 14.6 12.9 L 15.8 13.9 L 17.8 13.9 L 19 12.9 L 19.4 13.9 L 20.6 15.1 L 20.6 18.1 L 19.2 19.5 L 14.4 19.5 L 13 18.1 L 13 15.1 Z M 14.8 15.9 L 18.8 15.9 L 18.8 17.5 L 14.8 17.5 Z" /></symbol>
<symbol id="i-tower" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M12 2.5 L15 5.5 L12 8.5 L9 5.5 Z M9 10.5 L15 10.5 L15 12 L16.5 12 L18 21.5 L6 21.5 L7.5 12 L9 12 Z M11 14 L13 14 L13 18.5 L11 18.5 Z" /></symbol>
<symbol id="i-inhib" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M12 2.5 L18 9.5 L12 16.5 L6 9.5 Z M12 6.5 L9.5 9.5 L12 12.5 L14.5 9.5 Z M4.5 18 L19.5 18 L21.5 19.8 L19.5 21.5 L4.5 21.5 L2.5 19.8 Z" /></symbol>
<symbol id="i-minion" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M 12 2 L 19.4 5.2 L 21.8 15.8 L 19.2 21 L 4.8 21 L 2.2 15.8 L 4.6 5.2 Z M 6.5 21 L 6.9 17.2 L 4.7 15 L 6.5 7.3 L 12 4.9 L 17.5 7.3 L 19.3 15 L 17.1 17.2 L 17.5 21 L 15.9 21 L 15.5 16.2 L 17.5 14.2 L 16.1 8.4 L 14.2 7.6 L 12 8 L 9.8 7.6 L 7.9 8.4 L 6.5 14.2 L 8.5 16.2 L 8.1 21 Z M 9.1 10.1 L 11.2 11.1 L 9.3 11.9 Z M 14.9 10.1 L 12.8 11.1 L 14.7 11.9 Z" /></symbol>
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
