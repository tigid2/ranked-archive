import { createRoot } from 'react-dom/client'
import '../../tools/report/report.css'
import Report from './Report.jsx'
import Lab from './lab/Lab.jsx'

// 데이터 읽는 순서: artifact용 한 파일이면 파일 안의 window.__REPORT__,
// 아니면 주소의 ?id=<경기ID> (또는 #<경기ID>)로 ../report-data/<경기ID>.json 을 읽어요.
const root = createRoot(document.getElementById('root'))

function Message({ title, body }) {
  return (
    <main className="wrap">
      <div className="memo is-empty" style={{ marginTop: 48 }}>
        <p><b>{title}</b><br />{body}</p>
      </div>
    </main>
  )
}

async function start() {
  const q = new URLSearchParams(location.search)
  // ?lab=1 이면 실험 페이지(넣어 볼 항목 모음)를 보여 줘요. artifact 한 파일은 window.__LAB__로 정해요.
  const View = (window.__LAB__ || q.get('lab')) ? Lab : Report
  if (window.__REPORT__) {
    root.render(<View data={window.__REPORT__} />)
    return
  }
  const id = q.get('id') || location.hash.replace(/^#/, '')
  if (!/^[A-Z0-9]+_\d+$/.test(id || '')) {
    root.render(<Message title="경기 ID가 없어요" body="주소 끝에 ?id=KR_0000000000 처럼 경기 ID를 붙여 주세요." />)
    return
  }
  try {
    const res = await fetch(`../report-data/${id}.json`, { cache: 'no-cache' })
    if (!res.ok) throw new Error(res.status)
    root.render(<View data={await res.json()} />)
  } catch (e) {
    root.render(<Message title="리포트를 찾지 못했어요" body={`${id} 판의 리포트 데이터가 아직 없어요. 경기 기록 갱신이 끝났는지 확인해 주세요.`} />)
  }
}
start()
