// 실험 리포트에서 본 리포트로 옮긴 칸(11-16). 데이터는 report_data.py의 plus.
// L = d.plus, S = d.plus.site(사이트 통계). 정리(겹침 묶기, 시각화)는 다음 단계에서 해요.
import { useState } from 'react'
import { Ci, Ii, Pi, num, signed, cx } from '../ui.jsx'
import { Radar, DiffChart } from '../lab/charts.jsx'
import '../lab/lab.css'

const sec = (s) => (s == null ? '–' : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`)
const p1 = (v) => (+v).toFixed(1)
const Empty = ({ text }) => <p className="lab-empty">{text}</p>

function Card({ title, sub, wide, children }) {
  return (
    <article className={cx('panel lab-card', wide && 'is-wide')}>
      <div className="panel-head"><h3>{title}</h3></div>
      {sub && <p className="lab-sub">{sub}</p>}
      {children}
    </article>
  )
}

export const Grid = ({ children }) => <div className="lab-grid x-grid">{children}</div>

// 플레이 스타일: 14분 숫자를 같은 챔피언 평균의 몇 배인지로 그려요. 평균 = 가운데 점선, 평균의 2배 = 바깥 끝.
// 사이트는 평균만 주므로 "상위 몇 %"가 아니에요. 한 판짜리라 출렁임이 커서 2배에서 잘라요.
const STYLE = [['성장', ['14분 CS']], ['전투', ['분당 챔피언 피해']], ['관여', ['14분 전 킬', '14분 전 도움']], ['생존', ['14분 전 죽음']], ['압박', ['포탑 방패']]]
export function StyleCard({ S, d }) {
  const rows = S?.lane14?.rows
  if (!rows) return null
  const by = Object.fromEntries(rows.map((r) => [r.label, r]))
  const axes = STYLE.map(([axis, keys]) => {
    const rs = keys.map((k) => by[k]).filter(Boolean)
    if (!rs.length) return { axis, value: null }
    const me = rs.reduce((a, r) => a + r.me, 0), avg = rs.reduce((a, r) => a + r.avg, 0)
    let x = rs[0].dir < 0 ? (me === 0 ? 2 : avg / me) : (avg ? me / avg : 1)
    x = Math.min(2, Math.max(0, x))
    return { axis, value: Math.round(x * 50), text: `${x.toFixed(1)}배`, me, avg }
  })
  return (
    <Card title="플레이 스타일" sub={`14분까지 숫자를 ${d.me.n} 평균(에메랄드 이상)과 비교했어요. 점선이 평균이고, 바깥 끝이 평균의 2배예요.`} wide>
      <div className="lab-radar-wrap">
        <Radar axes={axes} />
        <div className="rd-parts">
          {axes.map((a) => (
            <div key={a.axis}>
              <b>{a.axis}</b> <span className="num">{a.text ?? '–'}</span>
              {a.me != null && <span className="muted small num"> 나 {+a.me.toFixed(1)} / 평균 {+a.avg.toFixed(1)}</span>}
            </div>
          ))}
          <p className="small muted">생존은 적게 죽을수록 커져요. 한 번도 안 죽으면 끝까지 차요.</p>
        </div>
      </div>
    </Card>
  )
}

export function PhaseCard({ L, d }) {
  return (
    <Card title="구간별 성적" sub="어느 구간에서 벌어지고 어느 구간에서 따라잡았는지 한 줄씩 보여 줘요." wide>
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


// ---- 02 흐름: 맞라인 차이 그래프. 지금 리포트의 골드 그래프에 탭만 더해요.
const TABS = [['gold', '골드'], ['cs', 'CS'], ['xp', '경험치'], ['lv', '레벨']]
export function DiffCard({ L, d }) {
  const [t, setT] = useState('gold')
  const vals = L.minute.map((r) => r[t][0] - r[t][1])
  return (
    <Card title={`${d.opp.n}${d.oppWith.slice(d.opp.n.length)}의 차이`} sub="지금 리포트의 골드 그래프에 CS·경험치·레벨 탭을 더해요. 위쪽이 내가 앞선 구간이에요." wide>
      <div className="lab-tabs">{TABS.map(([k, n]) => <button key={k} className={cx(t === k && 'on')} onClick={() => setT(k)}>{n}</button>)}</div>
      <DiffChart values={vals} />
    </Card>
  )
}


// ---- 03 라인전: 이 상성은 원래 어떤가 (승률 + 2·3·6레벨 선점)
export function MatchupCard({ S, d }) {
  const mu = S?.matchup
  if (!mu) return <Card title={`${d.me.n} vs ${d.opp.n} 상성`}><Empty text="이 상대는 통계 판 수가 모자라서 비워 뒀어요." /></Card>
  const base = S.champ?.win
  const main = mu.kr || mu.world
  const gap = base != null ? +(main.win - base).toFixed(1) : null
  return (
    <Card title={`${d.me.n} vs ${d.opp.n} 상성`} sub={`${d.me.n}가 ${d.opp.n}를 만난 판만 모은 통계예요.`}>
      <div className="mu-top">
        <div className="mu-main">
          <span className="label">상성 승률</span>
          <b className={cx('num', main.win < 49 ? 'neg-dark' : main.win > 51 && 'pos')}>{main.win.toFixed(1)}<small>%</small></b>
          {gap != null && <span className="small muted">{d.me.n} 평소 승률 {base}%보다 <b className="num">{Math.abs(gap)}%p</b> {gap < 0 ? '낮아요' : '높아요'}</span>}
        </div>
        <dl className="mu-src">
          {mu.kr && <div><dt>한국</dt><dd className="num">{mu.kr.win.toFixed(1)}% <span className="muted">{num(mu.kr.games)}판</span></dd></div>}
          {mu.world && <div><dt>전 세계</dt><dd className="num">{mu.world.win.toFixed(1)}% <span className="muted">{num(mu.world.games)}판</span></dd></div>}
        </dl>
      </div>
      {mu.lv?.length > 0 && (
        <div className="mu-lv">
          <span className="label">{d.me.n}가 레벨을 먼저 찍는 비율</span>
          {mu.lv.map((r) => (
            <div key={r.lv} className="mu-lv-row">
              <span className="num mu-lv-n">{r.lv}레벨</span>
              <div className="mu-track"><span className={cx('mu-fill', r.first >= 50 && 'is-good')} style={{ width: `${r.first}%` }} /><i /></div>
              <span className="num mu-lv-v">{r.first}%</span>
              {r.mine == null ? <span className="chip chip-unknown">기록 없음</span>
                : <span className={cx('chip', r.mine ? 'chip-pos' : 'chip-line')}>이 판: {r.mine ? '내가 먼저' : '상대가 먼저'}</span>}
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

// ---- 03 라인전: 14분 숫자를 같은 챔피언 평균, 이 판 상대와 한 표에 (L6 + L9 + L10)
export function Lane14Card({ S, L, d }) {
  const ln = S?.lane14
  const fmt = (v) => (Number.isInteger(v) ? num(v) : v.toFixed(1))
  const backRow = (c, b) => (
    <div className="back-row">
      <Ci c={c} size="sm" />
      {b ? (<>
        <b className="num">{sec(b.t)}</b>
        <span className="muted small num">골드 약 {num(b.gold)}{b.death ? ' · 죽어서 귀환' : ''}</span>
        <span className="back-items">{b.items.map((it, i) => <Ii key={i} it={it} size="xs" />)}</span>
      </>) : <span className="muted">찾지 못함</span>}
    </div>
  )
  return (
    <Card title="14분 라인전" sub={`${d.me.n} 평균은 한국 에메랄드 이상 ${ln ? num(ln.games) : ''}판의 평균이에요.`} wide>
      {ln ? (
        <div className="table-wrap">
          <table className="tbl lab-tbl l14">
            <thead><tr><th></th><th>나</th><th>{d.me.n} 평균</th><th>평균과 차이</th><th>{d.opp.n} (이 판)</th></tr></thead>
            <tbody>{ln.rows.map((r) => {
              const diff = r.me - r.avg
              const good = diff * r.dir > 0, even = Math.abs(diff) < (Math.abs(r.avg) * 0.05 || 0.5)
              return (
                <tr key={r.label}>
                  <td>{r.label}</td>
                  <td className="num l14-me">{fmt(r.me)}</td>
                  <td className="num muted">{fmt(r.avg)}</td>
                  <td className={cx('num', even ? 'muted' : good ? 'pos' : 'neg-dark')}>{even ? '비슷' : `${diff > 0 ? '+' : '−'}${fmt(Math.abs(Math.round(diff * 10) / 10))}`}</td>
                  <td className="num l14-opp">{fmt(r.opp)}</td>
                </tr>
              )
            })}</tbody>
          </table>
        </div>
      ) : <Empty text="이 챔피언은 아직 평균 숫자를 가져오지 않았어요." />}
      <div className="l14-back">
        <span className="label">첫 귀환</span>
        {backRow(d.me, L.back.me)}
        {backRow(d.opp, L.back.opp)}
      </div>
    </Card>
  )
}

// ---- 06 빌드: 내 선택을 통계와 한 표에 (L15 + L16 + L14)
export function BuildCard({ S, L, d }) {
  if (!S?.slots) return <Card title="빌드 비교" wide><Empty text="이 챔피언은 아직 빌드 통계를 가져오지 않았어요." /></Card>
  const late = (t, min) => {
    if (min == null) return null
    const df = t - (min * 60 + 30)  // 평균은 '11분대'처럼 분 단위라 가운데(30초)를 기준으로 봐요
    if (Math.abs(df) < 60) return <span className="muted small">평균과 비슷</span>
    return <span className={cx('small', df > 0 ? 'neg-dark' : 'pos')}>{sec(Math.abs(df))} {df > 0 ? '늦음' : '빠름'}</span>
  }
  const others = (top, mineId) => top.filter((o) => o.id !== mineId).slice(0, 2).map((o) => (
    <span key={o.id} className="bd-alt"><Ii it={o.item} size="xs" /><span className="num small">{p1(o.pick)}% · 승 {p1(o.win)}%</span></span>
  ))
  const row = (label, m, top) => (
    <tr key={label}>
      <td className="bd-slot">{label}</td>
      {m ? (<>
        <td><span className="bd-item"><Ii it={m.item} size="sm" /><b>{m.item.n}</b></span></td>
        <td className="num"><b>{sec(m.time)}</b> <span className="muted small">/ 평균 {m.stat?.min ?? '–'}분대</span><br />{m.stat && late(m.time, m.stat.min)}</td>
        <td className="num">{m.stat ? <>{p1(m.stat.pick)}%{m.rank && <span className="muted small"> · {m.rank}번째로 많음</span>}</> : <span className="muted small">1% 미만</span>}</td>
        <td className="num">{m.stat ? `${p1(m.stat.win)}%` : '–'}</td>
      </>) : <td colSpan="4" className="muted">이 판에서는 완성하지 못했어요</td>}
      <td><div className="bd-alts">{others(top, m?.item.id)}</div></td>
    </tr>
  )
  const o = S.order, sp = S.spells, mx = L.dmgMix.theirs
  const tot = mx.phys + mx.magic + mx.true || 1
  return (
    <Card title="빌드 비교" sub={`에메랄드 이상 ${d.me.n} ${num(S.champ.games)}판의 선택과 나란히 놓았어요. 승률은 그 아이템을 그 순서로 산 판의 승률이에요.`} wide>
      <div className="table-wrap">
        <table className="tbl lab-tbl bd">
          <thead><tr><th></th><th>내 선택</th><th>완성 시간</th><th>선택률</th><th>승률</th><th>다른 선택</th></tr></thead>
          <tbody>
            {S.slots.map((s) => row(`${s.no}코어`, s.mine && { ...s.mine }, s.top))}
            {S.boots && row('신발', S.boots, S.boots.top)}
          </tbody>
        </table>
      </div>
      <div className="bd-extra">
        {o && (
          <div>
            <span className="label">구매 순서</span>
            <div className="bd-order">{o.mine.map((it, i) => <span key={i}>{i > 0 && <i aria-hidden="true">→</i>}<Ii it={it} size="sm" /></span>)}</div>
            <p className="small">{o.stat ? <><b className="num">{p1(o.stat.pick)}%</b>가 고른 순서 ({o.rank}번째로 많음) · 승률 <b className="num">{p1(o.stat.win)}%</b></> : <span className="muted">많이 가는 순서 6개 안에 없어요</span>}</p>
          </div>
        )}
        <div>
          <span className="label">룬</span>
          <div className="bd-runes">{S.runes.map((r, i) => (
            <span key={i} className={cx('bd-rune', r.main && 'is-main')}><Pi p={r} cls="ic ic-sm ic-rune" /><span className="num small">{r.stat ? `${r.stat.pick}%` : '3% 미만'}</span></span>
          ))}</div>
          <p className="small muted">숫자는 그 룬을 고른 비율이에요.</p>
        </div>
        <div>
          <span className="label">소환사 주문</span>
          <div className="bd-runes">{sp.mineSpells.map((x) => <Pi key={x.key} p={x} cls="ic ic-sm" />)}</div>
          <p className="small">{sp.mine ? <><b className="num">{p1(sp.mine.pick)}%</b>가 고른 조합 · 승률 <b className="num">{p1(sp.mine.win)}%</b></> : <span className="muted">선택률 1% 미만</span>}</p>
        </div>
        <div>
          <span className="label">상대 팀 피해 구성</span>
          <div className="mix-bar is-theirs bd-mix">{[mx.phys, mx.magic, mx.true].map((v, i) => <span key={i} className={`mx-${i}`} style={{ width: `${(100 * v) / tot}%` }} />)}</div>
          <p className="small num">물리 {Math.round((100 * mx.phys) / tot)}% · 마법 {Math.round((100 * mx.magic) / tot)}% · 고정 {Math.round((100 * mx.true) / tot)}%</p>
        </div>
      </div>
    </Card>
  )
}

