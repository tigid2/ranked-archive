// 빌드 비교 개선 시안 (11-16). 본 리포트에는 아직 넣지 않았어요.
// window.__BUILD_V2__ 가 켜진 한 파일 html에서만 기존 칸 아래에 같이 나와요(비교용).
// 바뀐 점: ① 맨 위 한 줄 결론(선택은 흔한지, 완성은 빠른지) ② 완성 시간을 시간 막대로(평균 구간 vs 내 시점)
//          ③ 선택률·승률·다른 선택은 작게 내림 ④ 늦었으면 "어디서 확인할지" 한 줄
import { Ii, cx } from '../ui.jsx'
import { Card, BuildExtras, sec, p1 } from './Extra.jsx'

const delay = (m) => (m?.stat?.min == null ? null : m.time - (m.stat.min * 60 + 30))  // 평균은 'N분대'라 가운데(30초) 기준

function verdict(rows) {
  const done = rows.filter((r) => r.m)
  const common = done.filter((r) => r.m.rank === 1 || r.top?.[0]?.id === r.m.item.id).length  // 신발은 rank가 없어서 1위 아이템과 비교
  const rare = done.filter((r) => !r.m.stat || r.m.stat.pick < 5)
  const ds = done.map((r) => delay(r.m)).filter((v) => v != null)
  const late = ds.filter((v) => v >= 60), early = ds.filter((v) => v <= -60)
  const pick = rare.length
    ? `${rare.map((r) => r.label).join(', ')}는 흔하지 않은 선택이었어요`
    : common === done.length ? `${done.length}개 모두 가장 많이 가는 아이템이었어요` : '대부분 많이 가는 아이템이었어요'
  let speed = '완성 시간은 평균과 비슷했어요'
  if (late.length >= Math.ceil(ds.length / 2)) speed = `완성은 평균보다 ${sec(Math.min(...late))}~${sec(Math.max(...late))} 늦었어요`
  else if (early.length >= Math.ceil(ds.length / 2)) speed = `완성은 평균보다 빨랐어요`
  return { pick, speed, isLate: late.length >= Math.ceil(ds.length / 2), choiceOk: !rare.length }
}

export function BuildCardV2({ S, L, d }) {
  if (!S?.slots) return null
  const rows = [...S.slots.map((s) => ({ label: `${s.no}코어`, m: s.mine, top: s.top })), ...(S.boots ? [{ label: '신발', m: S.boots, top: S.boots.top }] : [])]
  const v = verdict(rows)
  const maxT = Math.max(d.hero.durationSec, ...rows.map((r) => (r.m?.stat?.min ?? 0) * 60 + 60))
  const end = Math.ceil(maxT / 300) * 300
  const x = (t) => `${(100 * t) / end}%`
  const ticks = Array.from({ length: end / 300 + 1 }, (_, i) => i * 5)
  return (
    <Card title="빌드 비교 · 개선 시안" wide>
      <div className="b2-verdict">
        <div className={cx('b2-v', v.choiceOk ? 'is-ok' : 'is-warn')}><span className="label">고른 아이템</span><b>{v.pick}</b></div>
        <div className={cx('b2-v', v.isLate ? 'is-warn' : 'is-ok')}><span className="label">완성 속도</span><b>{v.speed}</b></div>
      </div>
      {v.isLate && v.choiceOk && <p className="b2-hint">빌드 선택보다 <b>골드를 버는 속도</b>가 문제였을 수 있어요. 02 흐름의 CS·골드 차이에서 어느 구간부터 벌어졌는지 확인해 보세요.</p>}
      <div className="b2-tl">
        <div className="b2-axis"><span />{<div className="b2-ticks">{ticks.map((m) => <span key={m} style={{ left: x(m * 60) }}>{m}분</span>)}</div>}</div>
        {rows.map((r) => {
          const df = delay(r.m)
          const a = r.m?.stat?.min
          return (
            <div key={r.label} className="b2-row">
              <div className="b2-who">
                <span className="b2-slot">{r.label}</span>
                {r.m ? <><Ii it={r.m.item} size="sm" /><span className="b2-name">{r.m.item.n}</span></> : <span className="muted small">완성 못 함</span>}
              </div>
              <div className="b2-track">
                {a != null && <span className="b2-avg" style={{ left: x(a * 60), width: x(60) }} title={`평균 ${a}분대`} />}
                {r.m && a != null && Math.abs(df) >= 60 && <span className={cx('b2-gap', df > 0 && 'is-late')} style={{ left: x(Math.min(r.m.time, a * 60 + 30)), width: x(Math.abs(df)) }} />}
                {r.m && <span className={cx('b2-me', df != null && df >= 60 && 'is-late')} style={{ left: x(r.m.time) }}><time className="num">{sec(r.m.time)}</time></span>}
              </div>
              <div className="b2-meta">
                {r.m && df != null && <b className={cx('num', df >= 60 ? 'neg-dark' : df <= -60 ? 'pos' : 'muted')}>{Math.abs(df) < 60 ? '평균과 비슷' : `${sec(Math.abs(df))} ${df > 0 ? '늦음' : '빠름'}`}</b>}
                <span className="small muted num">{r.m?.stat ? `선택률 ${p1(r.m.stat.pick)}% · 승률 ${p1(r.m.stat.win)}%` : '선택률 1% 미만'}</span>
              </div>
            </div>
          )
        })}
        <div className="b2-legend small muted"><span><i className="b2-lg-avg" />같은 챔피언 평균 완성 구간</span><span><i className="b2-lg-me" />내 완성 시점</span></div>
      </div>
      <details className="b2-more">
        <summary>다른 선택 보기</summary>
        <ul>{rows.map((r) => (
          <li key={r.label}><span className="b2-slot">{r.label}</span>{r.top.filter((o) => o.id !== r.m?.item.id).slice(0, 2).map((o) => (
            <span key={o.id} className="bd-alt"><Ii it={o.item} size="xs" /><span className="num small">{p1(o.pick)}% · 승 {p1(o.win)}%</span></span>
          ))}</li>
        ))}</ul>
      </details>
      <BuildExtras S={S} L={L} />
    </Card>
  )
}
