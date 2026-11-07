import { Section, Pending } from '../ui.jsx'

const MARK = { good: ['좋음', 'chip-pos'], mid: ['보통', 'chip-mid'], bad: ['아쉬움', 'chip-bad'] }

export function Checklist({ fb }) {
  if (!fb) return <Section no="07"><Pending text="체크리스트는 피드백 글을 쓰면 채워져요." /></Section>
  const cnt = { good: 0, mid: 0, bad: 0 }
  fb.checklist.forEach((c) => { if (c.mark in cnt) cnt[c.mark]++ })
  return (
    <Section no="07">
      <ul className="ck-sum">
        {Object.entries(cnt).map(([k, v]) => <li key={k}><span className={`chip ${MARK[k][1]}`}>{MARK[k][0]}</span><b>{v}</b></li>)}
      </ul>
      <ol className="cklist">
        {fb.checklist.map((c, i) => (
          <li key={i} className={`ck ck-${c.mark}`}>
            <span className="ck-no">{String(i + 1).padStart(2, '0')}</span>
            {MARK[c.mark] && <span className={`chip ${MARK[c.mark][1]}`}>{MARK[c.mark][0]}</span>}
            <h3>{c.name}</h3><p>{c.why}</p>
          </li>
        ))}
      </ol>
    </Section>
  )
}

export function Memo({ fb }) {
  const m = (fb && fb.memo) || ''
  return (
    <Section no="08">
      {m ? <div className="memo"><p>{m}</p></div> : <div className="memo is-empty"><p>이 판은 메모가 없어요.</p></div>}
    </Section>
  )
}
