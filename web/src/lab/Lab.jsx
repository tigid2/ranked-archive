// 실험 페이지(?lab=1): 리포트에 넣어 볼 항목을 섹션 순서대로 모아 둔 곳.
// 항목마다 번호(L1, L2…)가 있어요. 남길 항목은 이 조각을 원래 섹션 파일로 옮기면 돼요.
import { useState, useEffect } from 'react'
import { SPRITE, Ci, Ii, num, signed, cx } from '../ui.jsx'
import Hero from '../sections/Hero.jsx'
import { Radar, PctBar, RangeRow, DiffChart } from './charts.jsx'
import './lab.css'

const sec = (s) => (s == null ? '–' : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`)
const pct = (v) => (v == null ? '–' : `${v}%`)

function Card({ id, title, from, data, wide, children }) {
  return (
    <article className={cx('panel lab-card', wide && 'is-wide')}>
      <header className="lab-head">
        <span className="lab-id num">{id}</span>
        <h3>{title}</h3>
      </header>
      <p className="lab-meta"><span className={cx('lab-src', `src-${data}`)}>{{ game: '이 판', bench: '기준 데이터', none: '아직 없음' }[data]}</span>{from}</p>
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

// ---------------------------------------------------------------- 01 요약
function StyleCard({ L }) {
  if (!L.radar) return <Card id="L1" title="플레이 스타일 그래프" from="참고: your.gg" data="bench" wide><Empty text="이 챔피언은 기준 데이터가 없어요." /></Card>
  return (
    <Card id="L1" title="플레이 스타일 그래프" from="참고: your.gg 플레이 스타일 · 에메랄드~다이아 같은 챔피언과 비교" data="bench" wide>
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
    <Card id="L2" title="지표별 백분위 막대" from="참고: Mobalytics GPI · 점수 하나로 합치지 않고 지표마다 따로" data="bench" wide>
      {ms.length ? <div className="pct-list">{ms.map((m) => <PctBar key={m.key} m={m} />)}</div> : <Empty text="기준 데이터가 없어요." />}
      {L.bench.missing?.length > 0 && <p className="lab-note">기준 데이터를 다시 모으면 추가돼요: {L.bench.missing.join(', ')}</p>}
    </Card>
  )
}

function PhaseCard({ L, d }) {
  return (
    <Card id="L3" title="구간별 성적" from="참고: your.gg 약점 구간 분석 · 라인전(~14분) / 중반(~25분) / 후반" data="game" wide>
      <div className="table-wrap">
        <table className="tbl lab-tbl">
          <thead><tr><th>구간</th><th>{d.opp.n}와 골드 차이 변화</th><th>팀 골드 차이 변화</th><th>CS (나 : 상대)</th><th>내 킬/죽음/도움</th><th>팀 킬 : 데스</th></tr></thead>
          <tbody>
            {L.phases.map((p) => (
              <tr key={p.name}>
                <td><b>{p.name}</b> <span className="muted small num">{p.from}~{p.to ?? '끝'}분</span></td>
                <td className={cx('num', p.laneGold > 0 ? 'pos' : p.laneGold < 0 && 'neg-dark')}>{signed(p.laneGold)}</td>
                <td className={cx('num', p.teamGold > 0 ? 'pos' : p.teamGold < 0 && 'neg-dark')}>{signed(p.teamGold)}</td>
                <td className="num">{p.cs[0]} : {p.cs[1]}</td>
                <td className="num">{p.k} / <span className={p.d ? 'death' : ''}>{p.d}</span> / {p.a}</td>
                <td className="num">{p.teamK} : {p.teamD}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

// ---------------------------------------------------------------- 02 흐름
const TABS = [['gold', '골드'], ['cs', 'CS'], ['xp', '경험치'], ['lv', '레벨'], ['teamXp', '팀 경험치']]
function DiffCard({ L, d }) {
  const [t, setT] = useState('xp')
  const vals = L.minute.map((r) => (t === 'teamXp' ? r.teamXp : r[t][0] - r[t][1]))
  return (
    <Card id="L4" title="맞라인 차이 그래프 (경험치·레벨 탭 추가)" from="참고: OP.GG 경기 상세 · 지금 리포트의 골드 그래프 옆 탭으로" data="game" wide>
      <div className="lab-tabs">{TABS.map(([k, n]) => <button key={k} className={cx(t === k && 'on')} onClick={() => setT(k)}>{n}</button>)}</div>
      <DiffChart values={vals} />
      <p className="lab-note">{t === 'teamXp' ? '우리 팀 경험치 합 − 상대 팀 경험치 합' : `${d.me.n} − ${d.opp.n}`}. 위쪽이 우리가 앞선 구간이에요.</p>
    </Card>
  )
}

function MinuteCard({ L, d }) {
  const rows = L.minute.filter((r) => r.m % 5 === 0 && r.m > 0)
  const end = L.minute[L.minute.length - 1]
  if (end.m % 5) rows.push(end)
  const cell = (a, b) => <td className="num">{num(a)} : {num(b)} <span className={cx('small', a - b > 0 ? 'pos' : a - b < 0 && 'muted')}>({signed(a - b)})</span></td>
  return (
    <Card id="L5" title="맞라인 분 단위 비교 (끝까지)" from="참고: agent-lol · 지금은 15분까지만 있어요" data="game" wide>
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
    <Card id="L6" title="10/15분 지표를 기준과 비교" from="참고: LOL.PS, Rise to Challenger · 상자 = 기준 판 가운데 50%, 세로선 = 중앙값, 점 = 이 판" data="bench" wide>
      {ms.length ? <div className="pct-list">{ms.map((m) => <RangeRow key={m.key} m={m} />)}</div> : <Empty text="기준 데이터가 없어요." />}
      {L.bench.available && <p className="lab-note">기준: {L.bench.tiers?.join('·')} {L.bench.games}판, 패치 {L.bench.patches?.join(', ')}</p>}
    </Card>
  )
}

function MatchupCard({ L, d }) {
  const mu = L.bench.matchup
  return (
    <Card id="L7" title="상성 기준" from="참고: lolalytics 상성 · 이 원딜이 이 상대를 만났을 때" data="bench">
      {mu ? (
        <div className="lab-facts">
          <div><span className="label">기준 승률</span><b className="num">{mu.winRate}%</b><span className="muted small"> ({mu.n}판)</span></div>
          <div><span className="label">15분 골드 차이 (기준 중앙)</span><b className="num">{signed(mu.goldDiff15Median)}</b></div>
          <div><span className="label">이 판</span><b className={cx('num', mu.mine > mu.goldDiff15Median ? 'pos' : '')}>{signed(mu.mine)}</b></div>
        </div>
      ) : <Empty text={`${d.opp.n} 상대 기준 판이 10판이 안 돼서 숨겼어요. 다시 모으면 나올 수 있어요.`} />}
    </Card>
  )
}

function SupportCard({ L }) {
  const s = L.bench.support
  return (
    <Card id="L8" title="서폿 위치를 기준과 비교" from="우리 아이디어 · 라인전(2~14분) 동안" data="bench">
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

function BackCard({ L, d }) {
  const row = (c, b) => (
    <div className="back-row">
      <Ci c={c} size="sm" />
      {b ? (<>
        <b className="num">{sec(b.t)}</b>
        <span className="muted small num">골드 약 {num(b.gold)}{b.death ? ' · 죽고 산 것' : ''}</span>
        <span className="back-items">{b.items.map((it, i) => <Ii key={i} it={it} size="xs" />)}</span>
      </>) : <span className="muted">찾지 못함</span>}
    </div>
  )
  return (
    <Card id="L9" title="첫 귀환" from="우리 아이디어 · 시간, 그때 가진 골드, 산 아이템" data="game">
      {row(d.me, L.back.me)}
      {row(d.opp, L.back.opp)}
      <p className="lab-note">귀환 기록이 없어서 골드를 실제로 쓴 첫 구매로 짐작해요. 골드는 1분 기록 사이를 이어서 계산한 대략적인 값이에요.</p>
    </Card>
  )
}

function PlateCard({ L, d }) {
  const p = L.plates
  return (
    <Card id="L10" title="포탑 방패" from="우리 아이디어" data="game">
      <div className="lab-facts">
        <div><span className="label">내가 깬 방패 : {d.opp.n}</span><b className="num">{p.me} : {p.opp}</b></div>
        <div><span className="label">바텀에서 깬 방패 : 잃은 방패 (팀)</span><b className={cx('num', p.botTaken > p.botLost && 'pos')}>{p.botTaken} : {p.botLost}</b></div>
      </div>
    </Card>
  )
}

function WardCard({ L }) {
  return (
    <Card id="L11" title="와드" from="우리 아이디어 · 와드 위치는 Riot 기록에 없어요" data="game" wide>
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
    <Card id="L12" title={`상성 메모: ${d.me.n} vs ${d.opp.n}`} from="참고: 딥롤 챔피언 상대법 · 레벨 1~6 구간별로 유리/불리와 대처법" data="none" wide>
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
    <Card id="L13" title="팀 상세 지표" from="참고: OP.GG 상세 탭" data="game" wide>
      <div className="table-wrap">
        <table className="tbl lab-tbl">
          <thead><tr><th></th><th>받은 피해</th><th>막은 피해</th><th>회복</th><th>아군 보호막</th><th>CC(초)</th><th>와드 설치/제거/제어</th></tr></thead>
          <tbody>{side(L.teamDetail.ours, true)}<tr className="lab-split"><td colSpan="7" /></tr>{side(L.teamDetail.theirs, false)}</tbody>
        </table>
      </div>
    </Card>
  )
}

function MixCard({ L }) {
  const bar = (m, ours) => {
    const t = m.phys + m.magic + m.true || 1
    const segs = [['물리', m.phys], ['마법', m.magic], ['고정', m.true]]
    return (
      <div className="mix-row">
        <span className="label">{ours ? '우리 팀' : '상대 팀'}</span>
        <div className={cx('mix-bar', ours ? 'is-ours' : 'is-theirs')}>{segs.map(([n, v], i) => <span key={n} className={`mx-${i}`} style={{ width: `${(100 * v) / t}%` }} title={`${n} ${num(v)}`} />)}</div>
        <span className="small num">{segs.map(([n, v]) => `${n} ${Math.round((100 * v) / t)}%`).join(' · ')}</span>
      </div>
    )
  }
  return (
    <Card id="L14" title="팀 피해 구성" from="우리 아이디어 · 상대 조합에 방어 아이템이 필요했는지 보는 근거" data="game">
      {bar(L.dmgMix.ours, true)}
      {bar(L.dmgMix.theirs, false)}
    </Card>
  )
}

// ---------------------------------------------------------------- 06 빌드
function SlotCard({ L }) {
  const slots = L.bench.slots
  if (!slots) return <Card id="L15" title="코어 아이템 순서별 비교" from="참고: lolalytics, OP.GG" data="bench"><Empty text="기준 데이터가 없어요." /></Card>
  const core = (L.bench.metrics || []).filter((m) => m.key === 'core1Time' || m.key === 'core2Time')
  return (
    <Card id="L15" title="코어 아이템 순서별 비교" from="참고: lolalytics 아이템 칸, Mobalytics 완성 시간 · 시간은 완성 시간 중앙값" data="bench" wide>
      <div className="slot-grid">
        {slots.map((s, i) => (
          <div key={i} className="slot">
            <span className="label">{i + 1}번째 코어</span>
            {s.mine ? <div className="slot-mine"><Ii it={{ img: s.mine.img, n: s.mine.name }} size="sm" /><b>{s.mine.name}</b> <span className="num">{sec(s.mine.time)}</span>{s.rank && <span className="chip chip-line">기준 {s.rank}위</span>}</div> : <span className="muted">없음</span>}
            <ol className="slot-top">{s.top.map((b) => <li key={b.id}><Ii it={{ img: b.img, n: b.name }} size="xs" /> {b.name} <span className="muted small num">{b.share}% · 승률 {b.winRate}% · {sec(b.time)}</span></li>)}</ol>
          </div>
        ))}
      </div>
      {core.length > 0 && <div className="pct-list" style={{ marginTop: 16 }}>{core.map((m) => <RangeRow key={m.key} m={m} fmt={sec} />)}</div>}
    </Card>
  )
}

function RuneSpellCard({ L }) {
  const b = L.bench
  const list = (x) => x?.top?.length ? <ol className="slot-top">{x.top.map((t) => <li key={t.name}>{t.name} <span className="muted small num">{t.share}% · 승률 {pct(t.winRate)}</span></li>)}</ol> : <Empty text="기준 판이 모자라요." />
  return (
    <Card id="L16" title="룬·스펠 기준 비교" from="참고: OP.GG, lolalytics" data="bench">
      <span className="label">핵심 룬 + 보조 빌드 {b.keystone?.rank ? `· 내 선택 기준 ${b.keystone.rank}위` : '· 내 선택은 상위권 밖'}</span>
      {list(b.keystone)}
      <span className="label">소환사 주문 {b.spells?.rank ? `· 내 선택 기준 ${b.spells.rank}위` : '· 내 선택은 상위권 밖'}</span>
      {list(b.spells)}
    </Card>
  )
}

function LengthCard({ L }) {
  const lw = L.bench.lengthWin
  if (!lw?.length) return <Card id="L17" title="게임 길이별 승률" from="참고: lolalytics" data="bench"><Empty text="기준 데이터가 없어요." /></Card>
  const mx = Math.max(...lw.map((b) => b.winRate || 0), 60)
  return (
    <Card id="L17" title="게임 길이별 승률" from="참고: lolalytics · 이 챔피언이 언제 강한지" data="bench">
      <div className="len-bars">
        {lw.map((b) => (
          <div key={b.from} className={cx('len', b.here && 'is-here')}>
            <span className="num len-v">{b.winRate ?? '–'}%</span>
            <span className="len-bar" style={{ height: `${((b.winRate || 0) / mx) * 90}px` }} />
            <span className="small">{b.to < 99 ? `${b.from}~${b.to}분` : `${b.from}분+`}</span>
            <span className="muted small num">{b.n}판</span>
          </div>
        ))}
      </div>
      <p className="lab-note">진하게 표시한 막대가 이 판 길이예요. 판 수가 적은 구간은 숫자가 흔들려요.</p>
    </Card>
  )
}

function ObjCard({ L }) {
  const o = L.bench.objectives || {}
  const names = { fb: '첫 킬', ft: '첫 포탑', fd: '첫 용' }
  const keys = Object.keys(o)
  return (
    <Card id="L18" title="첫 킬·첫 포탑·첫 용" from="참고: lolalytics 오브젝트 표 · 가져갔을 때와 뺏겼을 때 승률" data="bench">
      {keys.length ? (
        <table className="tbl lab-tbl"><thead><tr><th></th><th>이 판</th><th>가져간 비율</th><th>가져갔을 때 승률</th><th>뺏겼을 때 승률</th></tr></thead>
          <tbody>{keys.map((k) => <tr key={k}><td>{names[k]}</td><td>{o[k].mine ? '가져감' : '뺏김'}</td><td className="num">{pct(o[k].share)}</td><td className="num">{pct(o[k].winWith)}</td><td className="num">{pct(o[k].winWithout)}</td></tr>)}</tbody>
        </table>
      ) : <Empty text="기준 데이터를 다시 모은 뒤에 나와요." />}
    </Card>
  )
}

// ---------------------------------------------------------------- 페이지
export default function Lab({ data }) {
  const L = data.lab
  useEffect(() => { document.title = `실험 · ${data.me.n} 리포트` }, [data])
  return (
    <>
      <div dangerouslySetInnerHTML={{ __html: SPRITE }} style={{ display: 'contents' }} />
      <main className="wrap lab">
        <div className="lab-intro">
          <b>실험 페이지</b>
          <p>리포트에 넣어 볼 항목을 모아 둔 곳이에요. 항목마다 번호가 있어요. 남길 것과 뺄 것을 번호로 알려 주세요. 표시: <span className="lab-src src-game">이 판</span> 경기 기록으로 계산, <span className="lab-src src-bench">기준 데이터</span> 에메랄드~다이아 같은 챔피언과 비교, <span className="lab-src src-none">아직 없음</span> 자리만 만든 것.</p>
        </div>
        <Hero d={data} />
        <Group no="01" title="경기 요약"><StyleCard L={L} /><PctCard L={L} /><PhaseCard L={L} d={data} /></Group>
        <Group no="02" title="경기 흐름"><DiffCard L={L} d={data} /><MinuteCard L={L} d={data} /></Group>
        <Group no="03" title="라인전">
          <LaneBenchCard L={L} /><MatchupCard L={L} d={data} /><SupportCard L={L} />
          <BackCard L={L} d={data} /><PlateCard L={L} d={data} /><WardCard L={L} /><MatchupMemoCard d={data} />
        </Group>
        <Group no="05" title="팀 기록"><TeamDetailCard L={L} /><MixCard L={L} /></Group>
        <Group no="06" title="빌드"><SlotCard L={L} /><RuneSpellCard L={L} /><LengthCard L={L} /><ObjCard L={L} /></Group>
        <div className="page-end" />
      </main>
    </>
  )
}
