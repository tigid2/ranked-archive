// 실험 리포트: 본 리포트에 넣으려는 것(위)과 넣지 않으려는 것(아래)을 한 페이지에 모았어요.
// artifact용 한 파일에서만 보여요(공개 사이트 빌드에는 안 들어가요). 데이터는 report_data.py --lab.
// 위쪽 카드는 사용자가 확인하면 원래 섹션 파일(sections/)로 옮겨요. 번호(L1…)는 이야기할 때 쓰는 이름이에요.
import { useState, useEffect } from 'react'
import { SPRITE, Ci, Ii, Pi, num, signed, cx } from '../ui.jsx'
import Hero from '../sections/Hero.jsx'
import { Radar, PctBar, RangeRow, DiffChart } from './charts.jsx'
import './lab.css'
import { PhaseCard, DiffCard, MatchupCard, Lane14Card, BuildCard } from '../sections/Extra.jsx'

const sec = (s) => (s == null ? '–' : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`)
const pct = (v) => (v == null ? '–' : `${v}%`)
const p1 = (v) => (+v).toFixed(1)
const WHY = {
  "L1": "우리가 모은 판(챔피언당 100판 안팎)으로만 만들 수 있어서 숫자가 흔들려요. 생존 축은 아직 비어 있고, 다섯 축으로 합치면 예전에 정한 \"점수로 합치지 않기\"와도 부딪혀요.",
  "L2": "L1과 같은 이유예요. 위쪽 \"14분 라인전\" 표가 같은 질문(평균보다 잘했나)에 더 큰 표본으로 답해요.",
  "L5": "위쪽 차이 그래프(L4)와 같은 내용을 숫자로 한 번 더 보여 주는 표예요. 그래프 하나면 충분해요.",
  "L6": "우리가 모은 100판 안팎과 비교한 거예요. 같은 질문을 사이트의 수만 판 평균(위쪽 \"14분 라인전\")으로 바꿨어요. 10분, 15분 골드처럼 사이트에 없는 숫자가 꼭 필요해지면 그때 다시 꺼내요.",
  "L8": "사이트에는 서폿 위치 통계가 없어서 우리 데이터로만 비교할 수 있어요. 지금 리포트의 \"아군 서폿 위치\" 칸으로 충분하다고 봐요.",
  "L11": "원딜은 시야 규칙을 보류하기로 했어요. 와드 위치도 기록에 없어서 \"어디에 박았나\"는 볼 수 없어요.",
  "L12": "숫자가 아니라 글이 필요한 칸인데, 딥롤 페이지에서 레벨별 글을 찾지 못했어요. 숫자로 된 상성(승률, 2, 3, 6레벨 선점)은 위쪽 상성 칸에 넣었어요.",
  "L13": "OP.GG 상세 탭에서 이미 볼 수 있고, 원딜 피드백에서 이 숫자로 판단하는 일이 드물어요. 상대 팀 피해 구성만 빌드 칸으로 옮겼어요.",
  "L17": "같은 챔피언이면 판마다 똑같은 숫자예요. 한 판 리포트보다 챔피언 노트 페이지에 한 번만 두는 게 맞아요.",
  "L18": "이것도 챔피언마다 정해진 숫자예요. 이 판에서 누가 가져갔는지는 지금 리포트의 흐름, 팀 칸에 이미 있어요. 챔피언 노트 페이지로 보내요."
}

function Card({ id, title, sub, why, wide, children }) {
  return (
    <article className={cx('panel lab-card', wide && 'is-wide', why && 'is-low')}>
      <header className="lab-head">
        <h3>{title}</h3>
        <span className="lab-id num">{id}</span>
      </header>
      {sub && <p className="lab-sub">{sub}</p>}
      {why && <p className="lab-why"><b>넣지 않으려는 이유</b>{why}</p>}
      {children}
    </article>
  )
}

function Group({ no, title, children }) {
  return (
    <section className="sec lab-group" id={`s${no}`}>
      <header className="sec-head"><span className="sec-no" aria-hidden="true">{no}</span><h2>{title}</h2></header>
      <div className="lab-grid">{children}</div>
    </section>
  )
}

const Empty = ({ text }) => <p className="lab-empty">{text}</p>

// ================================================================ 위: 본 리포트에 넣으려는 것



// ================================================================ 아래: 넣지 않으려는 것

function LengthCard({ S }) {
  const lw = S?.length
  if (!lw) return <Card id="L17" title="게임 길이별 승률" why={WHY.L17}><Empty text="통계를 아직 가져오지 않았어요." /></Card>
  const lo = Math.min(...lw.map((b) => b.win)) - 2, hi = Math.max(...lw.map((b) => b.win))
  return (
    <Card id="L17" title="게임 길이별 승률" why={WHY.L17}>
      <div className="len-bars">
        {lw.map((b) => (
          <div key={b.from} className={cx('len', b.here && 'is-here')}>
            <span className="num len-v">{b.win}%</span>
            <span className="len-bar" style={{ height: `${10 + ((b.win - lo) / (hi - lo)) * 80}px` }} />
            <span className="small">{b.to < 99 ? `${b.from}~${b.to}분` : `${b.from}분+`}</span>
          </div>
        ))}
      </div>
      <p className="lab-note">진한 막대가 이 판 길이예요. 막대 높이는 차이가 보이게 늘려서 그렸어요.</p>
    </Card>
  )
}

function ObjCard({ S }) {
  const o = S?.objectives
  return (
    <Card id="L18" title="첫 킬, 첫 포탑, 첫 용" why={WHY.L18}>
      {o ? (
        <table className="tbl lab-tbl"><thead><tr><th></th><th>이 판</th><th>가져갔을 때 승률</th><th>뺏겼을 때 승률</th></tr></thead>
          <tbody>{o.map((x) => <tr key={x.name}><td>{x.name}</td><td>{x.mine ? <span className="pos">가져감</span> : <span className="muted">뺏김</span>}</td><td className={cx('num', x.mine && 'l14-me')}>{pct(x.winWith)}</td><td className={cx('num', !x.mine && 'l14-me')}>{pct(x.winWithout)}</td></tr>)}</tbody>
        </table>
      ) : <Empty text="통계를 아직 가져오지 않았어요." />}
    </Card>
  )
}

// ---------------------------------------------------------------- 01 요약
function StyleCard({ L }) {
  if (!L.radar) return <Card id="L1" title="플레이 스타일 그래프" wide why={WHY.L1}><Empty text="이 챔피언은 기준 데이터가 없어요." /></Card>
  return (
    <Card id="L1" title="플레이 스타일 그래프" wide why={WHY.L1}>
      <div className="lab-radar-wrap">
        <Radar axes={L.radar} />
        <div className="rd-parts">
          {L.radar.map((a) => (
            <div key={a.axis}>
              <b>{a.axis}</b> <span className="num">{a.value ?? '–'}</span>
              <span className="muted small"> = {a.parts.map((p) => `${p.label} ${p.pct ?? '모으는 중'}`).join(', ')}</span>
            </div>
          ))}
        </div>
      </div>
      <p className="lab-note">생존 축은 기준 데이터를 다시 모아야 생겨요. 그 전에는 나머지 네 축만 이어서 그려요. 숫자는 0~100이에요. 50이면 기준 판의 가운데, 70이면 기준 판 70%보다 잘한 거예요. 점선이 50이에요. 등급(A, B)은 붙이지 않았어요.</p>
    </Card>
  )
}

function PctCard({ L }) {
  const ms = (L.bench.metrics || []).filter((m) => m.pct != null)
  return (
    <Card id="L2" title="지표별 백분위 막대" wide why={WHY.L2}>
      {ms.length ? <div className="pct-list">{ms.map((m) => <PctBar key={m.key} m={m} />)}</div> : <Empty text="기준 데이터가 없어요." />}
      {L.bench.missing?.length > 0 && <p className="lab-note">기준 데이터를 다시 모으면 추가돼요: {L.bench.missing.join(', ')}</p>}
    </Card>
  )
}


function MinuteCard({ L, d }) {
  const rows = L.minute.filter((r) => r.m % 5 === 0 && r.m > 0)
  const end = L.minute[L.minute.length - 1]
  if (end.m % 5) rows.push(end)
  const cell = (a, b) => <td className="num">{num(a)} : {num(b)} <span className={cx('small', a - b > 0 ? 'pos' : a - b < 0 && 'muted')}>({signed(a - b)})</span></td>
  return (
    <Card id="L5" title="맞라인 분 단위 비교 (끝까지)" wide why={WHY.L5}>
      <div className="table-wrap">
        <table className="tbl lab-tbl">
          <thead><tr><th>시간</th><th>CS</th><th>골드</th><th>경험치</th><th>레벨</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.m}><td className="num">{r.m}분{r === end ? ' (끝)' : ''}</td>{cell(...r.cs)}{cell(...r.gold)}{cell(...r.xp)}<td className="num">{r.lv[0]} : {r.lv[1]}</td></tr>)}</tbody>
        </table>
      </div>
      <p className="lab-note">왼쪽이 {d.me.n}, 오른쪽이 {d.opp.n}예요.</p>
    </Card>
  )
}

// ---------------------------------------------------------------- 03 라인전
const LANE_KEYS = ['cs10', 'gold10', 'xp10', 'cs15', 'gold15', 'xp15', 'goldDiff15', 'csDiff15', 'xpDiff15']
function LaneBenchCard({ L }) {
  const ms = (L.bench.metrics || []).filter((m) => LANE_KEYS.includes(m.key))
  return (
    <Card id="L6b" title="10/15분 지표 (우리가 모은 판과 비교)" wide why={WHY.L6}>
      {ms.length ? <div className="pct-list">{ms.map((m) => <RangeRow key={m.key} m={m} />)}</div> : <Empty text="기준 데이터가 없어요." />}
      {L.bench.available && <p className="lab-note">기준: {L.bench.tiers?.join(', ')} {L.bench.games}판, 패치 {L.bench.patches?.join(', ')}</p>}
    </Card>
  )
}


function SupportCard({ L }) {
  const s = L.bench.support
  return (
    <Card id="L8" title="서폿 위치 비교" why={WHY.L8}>
      {s ? (
        <div className="lab-facts">
          <div><span className="label">서폿이 바텀에 있던 비율</span><b className="num">{Math.round(s.mineAtBotShare * 100)}%</b><span className="muted small"> / 기준 {Math.round(s.medianAtBotShare * 100)}%</span></div>
          <div><span className="label">서폿 있을 때 분당 CS</span><b className="num">{s.mineCsPerMinWith ?? '–'}</b><span className="muted small"> / 기준 {s.medianCsPerMinWith}</span></div>
          <div><span className="label">서폿 없을 때 분당 CS</span><b className="num">{s.mineCsPerMinWithout ?? '–'}</b><span className="muted small"> / 기준 {s.medianCsPerMinWithout}</span></div>
        </div>
      ) : <Empty text="기준 데이터가 없어요." />}
    </Card>
  )
}



function WardCard({ L }) {
  return (
    <Card id="L11" title="와드" wide why={WHY.L11}>
      <div className="table-wrap">
        <table className="tbl lab-tbl">
          <thead><tr><th></th><th>첫 와드</th><th>14분 전 설치</th><th>전체 설치</th><th>제거</th><th>제어 와드 구매</th></tr></thead>
          <tbody>{L.wards.map((w) => (
            <tr key={w.who} className={w.ours ? '' : 'is-opp'}>
              <td><Ci c={w.c} size="xs" /> {w.who}</td>
              <td className="num">{sec(w.ward1)}</td><td className="num">{w.wards14}</td><td className="num">{w.wards}</td>
              <td className="num">{w.wardsKilled}</td><td className="num">{w.ctrl}</td>
            </tr>))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

function MatchupMemoCard({ d }) {
  return (
    <Card id="L12" title={`상성 메모: ${d.me.n} vs ${d.opp.n}`} wide why={WHY.L12}>
      <div className="memo-skel">
        {['1레벨', '2레벨', '3레벨', '6레벨'].map((l) => <div key={l}><span className="label">{l}</span><span className="skel" /></div>)}
      </div>
      <p className="lab-note">글이 필요한 칸이라 아직 비워 뒀어요. 상대마다 한 번만 써서 저장해 두고 다음 판부터는 다시 읽기만 하면 토큰이 거의 안 들어요.</p>
    </Card>
  )
}

// ---------------------------------------------------------------- 05 팀
function TeamDetailCard({ L }) {
  const side = (ps, ours) => ps.map((p, i) => (
    <tr key={(ours ? 'o' : 't') + i} className={cx(!ours && 'is-opp', p.me && 'is-me')}>
      <td><Ci c={p.c} size="xs" /> <span className="small muted">{p.pos}</span></td>
      <td className="num">{num(p.taken)}</td><td className="num">{num(p.mitig)}</td><td className="num">{num(p.heal)}</td>
      <td className="num">{num(p.shield)}</td><td className="num">{p.cc}</td>
      <td className="num">{p.wards} / {p.wardsKilled} / {p.ctrl}</td>
    </tr>
  ))
  return (
    <Card id="L13" title="팀 상세 지표" wide why={WHY.L13}>
      <div className="table-wrap">
        <table className="tbl lab-tbl">
          <thead><tr><th></th><th>받은 피해</th><th>막은 피해</th><th>회복</th><th>아군 보호막</th><th>CC(초)</th><th>와드 설치/제거/제어</th></tr></thead>
          <tbody>{side(L.teamDetail.ours, true)}<tr className="lab-split"><td colSpan="7" /></tr>{side(L.teamDetail.theirs, false)}</tbody>
        </table>
      </div>
    </Card>
  )
}


// ---------------------------------------------------------------- 06 빌드



// ---------------------------------------------------------------- 페이지
export default function Lab({ data }) {
  const L = data.lab, S = L.site
  useEffect(() => { document.title = `실험 - ${data.me.n} 리포트` }, [data])
  return (
    <>
      <div dangerouslySetInnerHTML={{ __html: SPRITE }} style={{ display: 'contents' }} />
      <main className="wrap lab">
        <div className="lab-intro">
          <b>실험 리포트</b>
          <p>위쪽은 본 리포트에 넣으려는 것이에요. 지금 리포트의 같은 번호 섹션 안에 들어갈 모습 그대로 만들었어요. 아래쪽은 넣지 않으려는 것과 그 이유예요. 통계는 이번 패치, 에메랄드 이상 기준이에요.</p>
        </div>
        <Hero d={data} />
        <Group no="02" title="경기 흐름에 더할 것"><PhaseCard L={L} d={data} /><DiffCard L={L} d={data} /></Group>
        <Group no="03" title="라인전에 더할 것"><MatchupCard S={S} d={data} /><Lane14Card S={S} L={L} d={data} /></Group>
        <Group no="06" title="빌드에 더할 것"><BuildCard S={S} L={L} d={data} /></Group>
        <section className="sec lab-group lab-low" id="slow">
          <header className="sec-head"><span className="sec-no" aria-hidden="true">–</span><h2>넣지 않으려는 것</h2></header>
          <div className="lab-grid">
            <LengthCard S={S} /><ObjCard S={S} />
            <LaneBenchCard L={L} /><StyleCard L={L} /><PctCard L={L} />
            <MinuteCard L={L} d={data} /><SupportCard L={L} /><MatchupMemoCard d={data} />
            <TeamDetailCard L={L} /><WardCard L={L} />
          </div>
        </section>
        <div className="page-end" />
      </main>
    </>
  )
}
