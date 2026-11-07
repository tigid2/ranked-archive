import { Section, Lede, Pending } from '../ui.jsx'

export default function Summary({ fb }) {
  if (!fb) {
    return (
      <Section no="01">
        <Pending text="이 판은 피드백 글이 아직 없어요. 아래 숫자 기록을 먼저 보여 드려요." />
      </Section>
    )
  }
  return (
    <Section no="01">
      <div className="sum-grid">
        <Lede text={fb.summary} />
        <ol className="fixes">
          {fb.keyFixes.map((f, i) => (
            <li key={i} className="fix"><span className="fix-no">{i + 1}</span><div><h3>{f.title}</h3><p>{f.body}</p></div></li>
          ))}
        </ol>
        <aside className="takeaway"><span className="label">다음 판 목표</span><p>{fb.takeaway}</p></aside>
      </div>
    </Section>
  )
}
