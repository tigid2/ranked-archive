// 03~07 새 배치 시안(11-24, 7-0 5단계). 01, 02 시안(Draft.jsx)과 같은 벤토 격자와 원칙을 써요.
// 원칙: 같은 질문에 답하는 숫자는 한 칸에, 숫자 하나로 충분하면 큰 숫자로, 글은 그림에 붙는 한 줄로.
// artifact 한 파일(window.__DRAFT__)에서만 보여요. 공개 사이트는 sections/의 본 리포트 그대로예요.
import { useState } from 'react'
import { Section, Pending, Ci, Ii, Pi, Gi, BfRow, num, mmss, fix, cx } from '../ui.jsx'
import { TeamTable } from '../sections/Team.jsx'
import { sec, p1 } from '../sections/Extra.jsx'

const Xm = () => <i className="xm" aria-hidden="true" />
const toSec = (t) => { const [m, s] = String(t).split(':').map(Number); return m * 60 + (s || 0) }
const gapTxt = (s) => (s >= 60 ? `${Math.floor(s / 60)}분 ${s % 60 ? `${s % 60}초` : ''}`.trim() : `${s}초`)

// ================================================================ 03 라인전
// 1줄: 라인전 글(7칸) + 큰 숫자 3개(5칸) / 2줄: 맞라인 숫자(5칸) + 레벨 선점과 첫 귀환(7칸, 둘 다 '누가 먼저'라서 한 칸) / 3줄: 서폿 유무(5칸) + 14분 숫자(7칸)
function LaneNums({ d, L, mu, base }) {
  const bk = L.botAdcKills
  const main = mu && (mu.kr || mu.world)
  const gap = main && base != null ? +(main.win - base).toFixed(1) : null
  return (
    <div className="s2-focus l2-nums">
      <span className="label">라인전 결과</span>
      <dl>
        <div>
          <dt>{d.me.n} vs {d.opp.n} 상성 승률{main && <small>{mu.kr ? '한국' : '전 세계'} {num(main.games)}판{gap != null && `, 평소보다 ${Math.abs(gap)}%p ${gap < 0 ? '낮음' : '높음'}`}</small>}</dt>
          <dd>{main ? <><b className="num">{main.win.toFixed(1)}</b><small>%</small></> : <span className="muted small">통계 판 수가 모자라요</span>}</dd>
        </div>
        {bk ? (
          <div>
            <dt>바텀 원딜 킬, 내가 잡음 : 내가 죽음<small>14분까지 바텀 근처. 서폿이 막타를 친 것도 세요</small></dt>
            <dd><b className={cx('num', bk.opp > bk.me && 'pos')}>{bk.opp}</b><i>:</i><b className={cx('num', bk.me > 0 && 'death')}>{bk.me}</b></dd>
          </div>
        ) : (
          <div><dt>라인전 솔로킬, 나 : 상대</dt><dd><b className="num">{L.soloKills.me}</b><i>:</i><b className="num">{L.soloKills.opp}</b></dd></div>
        )}
        <div><dt>가장 크게 앞선 CS</dt><dd><b className="num pos">+{L.maxCsAdv}</b></dd></div>
      </dl>
    </div>
  )
}

function Back({ c, b }) {
  return (
    <div className="l2-back-row">
      <Ci c={c} size="sm" />
      {b ? (<>
        <b className="num">{sec(b.t)}</b>
        <span className="muted small num">골드 약 {num(b.gold)}{b.death ? ', 죽어서 귀환' : ''}</span>
        <span className="back-items">{b.items.map((it, i) => <Ii key={i} it={it} size="xs" />)}</span>
      </>) : <span className="muted">찾지 못함</span>}
    </div>
  )
}

// 레벨마다 한 열: 누가 몇 초 먼저 찍었는지 큰 숫자 + 두 사람 시간 + 이 상성에서 보통 누가 먼저 찍는지
function LevelRace({ d, L, mu }) {
  const stat = Object.fromEntries(((mu && mu.lv) || []).map((r) => [String(r.lv), r]))
  return (
    <div className="l2-lv" style={{ gridTemplateColumns: `repeat(${L.levels.length}, minmax(0, 1fr))` }}>
      {L.levels.map((v) => {
        const a = toSec(v.me), b = toSec(v.opp), df = b - a
        const st = stat[v.lv]
        return (
          <div key={v.lv} className={cx('l2-lv-col', df > 0 ? 'is-me' : df < 0 && 'is-opp')}>
            <span className="l2-lv-n">{v.lv}<small>레벨</small></span>
            <b className="l2-lv-big num">{df === 0 ? '같이' : gapTxt(Math.abs(df))}</b>
            <span className="l2-lv-who">{df === 0 ? '같은 시간에 찍음' : `${df > 0 ? d.me.n : d.opp.n}가 먼저`}</span>
            <dl className="l2-lv-t">
              <div className={cx(df > 0 && 'on')}><dt>{d.me.n}</dt><dd className="num">{v.me}</dd></div>
              <div className={cx(df < 0 && 'on')}><dt>{d.opp.n}</dt><dd className="num">{v.opp}</dd></div>
            </dl>
            {st ? (
              <div className="l2-lv-st">
                <div className="mu-track"><span className={cx('mu-fill', st.first >= 50 && 'is-good')} style={{ width: `${st.first}%` }} /><i /></div>
                <span className="small">보통 <b className="num">{st.first}%</b> 판에서 {d.me.n}가 먼저</span>
              </div>
            ) : <div className="l2-lv-st"><span className="small muted">이 레벨은 비교할 통계가 없어요</span></div>}
          </div>
        )
      })}
    </div>
  )
}

// 14분 숫자: 줄마다 평균을 가운데(점선)에 두고 나와 상대를 점으로. 끝은 평균의 2배예요.
function Lane14Dots({ d, ln }) {
  const fmt = (v) => (Number.isInteger(v) ? num(v) : v.toFixed(1))
  const pos = (v, avg) => Math.min(100, Math.max(0, (avg ? v / avg : 1) * 50))
  return (
    <div className="l2-dots">
      <div className="l2-dot-row l2-dot-h">
        <span />
        <span className="l2-dot-scale small num"><span>0</span><span>평균</span><span>2배</span></span>
        <span className="label">나</span><span className="label">평균</span><span className="label">{d.opp.n}</span>
      </div>
      {ln.rows.map((r) => {
        const good = (r.me - r.avg) * r.dir > 0
        return (
          <div key={r.label} className="l2-dot-row">
            <span className="l2-dot-k">{r.label}{r.dir < 0 && <small>적을수록 좋아요</small>}</span>
            <div className="l2-dot-track">
              <i className="l2-dot-avg" />
              <span className="l2-dot opp" style={{ left: `${pos(r.opp, r.avg)}%` }} title={`${d.opp.n} ${fmt(r.opp)}`} />
              <span className={cx('l2-dot me', good ? 'good' : 'low')} style={{ left: `${pos(r.me, r.avg)}%` }} title={`나 ${fmt(r.me)}`} />
            </div>
            <b className="num">{fmt(r.me)}</b>
            <span className="num muted">{fmt(r.avg)}</span>
            <span className="num muted">{fmt(r.opp)}</span>
          </div>
        )
      })}
    </div>
  )
}

export function Lane2({ d, fb }) {
  const L = d.lane, P = d.plus, S = P && P.site
  const me = d.me.n, opp = d.opp.n
  const mu = S && S.matchup, ln = S && S.lane14
  const s = L.support
  return (
    <Section no="03">
      <div className="bento l2">
        <div className="cell l2-lede"><Xm />
          {fb && fb.laneText ? <p className="l2-lede-t">{fb.laneText}</p> : <Pending text="라인전 글은 피드백 글을 쓰면 채워져요." />}
        </div>
        <div className="cell l2-numcell"><Xm /><LaneNums d={d} L={L} mu={mu} base={S && S.champ && S.champ.win} /></div>

        <div className="cell l2-vs"><Xm />
          <div className="s2-head"><span className="label">10분, 15분 맞라인 숫자</span></div>
          <div className="bf-head">
            <span className="bf-who"><Ci c={d.me} size="sm" /><span className="me-name">{me}</span></span>
            <span className="bf-who">{opp}<Ci c={d.opp} size="sm" /></span>
          </div>
          <div className="bf">{L.rows.map((r) => <BfRow key={r.label} label={r.label} mine={r.me} theirs={r.opp} />)}</div>
        </div>
        <div className="cell l2-lvcell"><Xm />
          <div className="s2-head"><span className="label">레벨을 누가 먼저 찍었나</span></div>
          <LevelRace d={d} L={L} mu={mu} />
          {P && P.back && <div className="l2-back"><span className="label">첫 귀환</span><Back c={d.me} b={P.back.me} /><Back c={d.opp} b={P.back.opp} /></div>}
        </div>

        {s && (
          <div className="cell l2-sup"><Xm />
            <div className="s2-head"><span className="label">아군 서폿이 바텀에 있던 분 ({me} : {opp} CS)</span></div>
            <div className="sup-strip">{s.atBot.map((c) => <span key={c.min} className={c.in ? 'in' : ''}>{c.min}</span>)}</div>
            <ul className="legend l2-sup-lg"><li><span className="lg lg-sup-in" />서폿 있음</li><li><span className="lg lg-sup-out" />서폿 없음</li></ul>
            <dl className="l2-sup-cs">
              <div><dt>서폿 있을 때 CS</dt><dd><b className="num">{s.with.me}</b><i>:</i><b className="num">{s.with.opp}</b></dd></div>
              <div><dt>서폿 없을 때 CS</dt><dd><b className="num">{s.without.me}</b><i>:</i><b className="num">{s.without.opp}</b></dd></div>
            </dl>
          </div>
        )}
        <div className={cx('cell l2-14', !s && 'is-full')}><Xm />
          <div className="s2-head"><span className="label">14분 숫자, 나와 {me} 평균(에메랄드 이상{ln ? ` ${num(ln.games)}판` : ''})과 {opp}</span>
            <span className="s2-key"><i className="l2-k-me" />나 <i className="l2-k-opp" />{opp} <i className="s2-key-avg" />평균</span></div>
          {ln ? <Lane14Dots d={d} ln={ln} /> : <p className="lab-empty">이 챔피언은 아직 평균 숫자를 가져오지 않았어요.</p>}
        </div>
      </div>
    </Section>
  )
}

// ================================================================ 05 팀 기록
// 맨 위: 팀 비교 10개를 큰 숫자 칸으로(5열 2줄). 오브젝트는 아이콘을 붙여요. 아래 두 팀 표는 그대로예요.
const OBJ_ICON = { 포탑: 'tower', 드래곤: 'dragon', '공허 유충': 'grub', 바론: 'baron' }
const short = (v) => (v >= 10000 ? `${+(v / 1000).toFixed(1)}k` : num(v))
export function Team2({ d }) {
  const T = d.team
  return (
    <Section no="05">
      <ol className="bento t2">
        {T.compare.map((r) => {
          const [a, b] = r.v, tot = a + b || 1
          const win = r.neutral ? '' : a > b ? 'mine' : b > a ? 'theirs' : ''
          return (
            <li key={r.label} className={cx('cell', win)}><Xm />
              <span className="label">{OBJ_ICON[r.label] && <Gi name={OBJ_ICON[r.label]} />}{r.label}</span>
              <div className="t2-v"><b className="num t2-a">{short(a)}</b><i>:</i><b className="num t2-b">{short(b)}</b></div>
              <div className="bf-bar t2-bar"><span className="bf-a" style={{ width: `${(100 * a / tot).toFixed(1)}%` }} /><span className="bf-b" style={{ width: `${(100 * b / tot).toFixed(1)}%` }} /></div>
            </li>
          )
        })}
      </ol>
      <p className="t2-key small muted">왼쪽 숫자가 우리 팀, 오른쪽 숫자가 상대 팀이에요. 받은 피해는 많고 적음이 좋고 나쁨이 아니라서 색을 칠하지 않아요.</p>
      <TeamTable t={T.ours} maxDmg={T.maxDmg} />
      <TeamTable t={T.theirs} maxDmg={T.maxDmg} />
    </Section>
  )
}

// ================================================================ 06 빌드
// 아이템이 세 번 나오던 것(완성 시점, 구매 순서, 빌드 비교)을 한 칸으로: 시간 축 위 완성 아이템에 평균 완성 시간을 붙이고,
// 비교 표는 선택률과 승률만, 전체 구매 순서는 같은 칸 아래에. 룬과 소환사 주문의 선택률은 각 칸 안으로 옮겨요.
const lateOf = (t, min) => {
  if (min == null) return null
  const df = t - (min * 60 + 30)  // 평균이 '11분대'처럼 분 단위라 가운데(30초)를 기준으로 봐요
  if (Math.abs(df) < 60) return { txt: '평균과 비슷', cls: 'muted' }
  return { txt: `평균보다 ${sec(Math.abs(df))} ${df > 0 ? '늦음' : '빠름'}`, cls: df > 0 ? 'late' : 'pos' }
}

function ItemTimeline2({ d, fb, S }) {
  const dur = d.hero.durationSec
  const pos = (t) => t / (dur * 1000) * 100
  const mine = d.build.timeline.me
  const statOf = (id) => {
    const sl = S && S.slots && S.slots.find((x) => x.mine && x.mine.item.id === id)
    return sl && sl.mine.stat
  }
  let gap = null
  if (mine.length >= 2) {
    const j = Math.min(parseInt((fb && fb.build && fb.build.gapAfter) || 1, 10) - 1, mine.length - 2)
    const t1 = mine[j].t, t2 = mine[j + 1].t
    gap = (<>
      <span className="itl-gap" style={{ left: `${pos(t1).toFixed(2)}%`, width: `${(pos(t2) - pos(t1)).toFixed(2)}%` }} />
      <span className="itl-gap-l" style={{ left: `${((pos(t1) + pos(t2)) / 2).toFixed(2)}%` }}>{mmss(t2 - t1)}</span>
    </>)
  }
  const ticks = []
  for (let m = 0; m <= Math.floor(dur / 60); m += 5) ticks.push(m)
  return (
    <div className="itl bd2-itl">
      <div className="itl-row mine bd2-row-me">
        <div className="itl-who"><Ci c={d.me} size="sm" /><span className="me-name">{d.me.n}</span></div>
        <div className="itl-track">
          {gap}
          {mine.map((x, i) => {
            const st = statOf(x.item.id), lt = st && lateOf(Math.round(x.t / 1000), st.min)
            return (
              <div key={i} className="itl-it bd2-it" style={{ left: `${pos(x.t).toFixed(2)}%` }}>
                <Ii it={x.item} size="md" />
                <time>{mmss(x.t)}</time>
                {st && <span className={cx('bd2-avg', lt && lt.cls)}>평균 {st.min}분대{lt && lt.cls !== 'muted' ? `, ${lt.txt.replace('평균보다 ', '')}` : ''}</span>}
              </div>
            )
          })}
        </div>
      </div>
      <div className="itl-row theirs">
        <div className="itl-who"><Ci c={d.opp} size="sm" /><span>{d.opp.n}</span></div>
        <div className="itl-track">{d.build.timeline.opp.map((x, i) => <div key={i} className="itl-it" style={{ left: `${pos(x.t).toFixed(2)}%` }}><Ii it={x.item} size="sm" /><time>{mmss(x.t)}</time></div>)}</div>
      </div>
      <div className="itl-axis"><div /><div>{ticks.map((m) => <span key={m} style={{ left: `${(m * 60000 / (dur * 1000) * 100).toFixed(2)}%` }}>{m}:00</span>)}</div></div>
    </div>
  )
}

function PickTable({ S }) {
  const others = (top, id) => top.filter((o) => o.id !== id).slice(0, 2).map((o) => (
    <span key={o.id} className="bd-alt"><Ii it={o.item} size="xs" /><span className="num small">{p1(o.pick)}%, 승 {p1(o.win)}%</span></span>
  ))
  const row = (label, m, top, time) => (
    <tr key={label}>
      <td className="bd-slot">{label}</td>
      {m ? (<>
        <td><span className="bd-item"><Ii it={m.item} size="sm" /><span><b>{m.item.n}</b>{time && <span className="bd2-boot small num">{sec(m.time)} 완성{m.stat ? `, 평균 ${m.stat.min}분대` : ''}</span>}</span></span></td>
        <td className="num bd2-pick">{m.stat ? <>
          <span className="bd2-pbar"><i style={{ width: `${m.stat.pick}%` }} /></span>
          <b>{p1(m.stat.pick)}%</b>{m.rank && <span className="muted small">, {m.rank}번째로 많음</span>}</> : <span className="muted small">1% 미만</span>}</td>
        <td className="num">{m.stat ? `${p1(m.stat.win)}%` : '–'}</td>
      </>) : <td colSpan="3" className="muted">이 판에서는 완성하지 못했어요</td>}
      <td><div className="bd-alts">{others(top, m && m.item.id)}</div></td>
    </tr>
  )
  return (
    <div className="table-wrap">
      <table className="tbl lab-tbl bd bd2-tbl">
        <thead><tr><th></th><th>내 선택</th><th>고른 비율</th><th>승률</th><th>다른 선택</th></tr></thead>
        <tbody>
          {S.slots.map((s) => row(`${s.no}코어`, s.mine, s.top))}
          {S.boots && row('신발', S.boots, S.boots.top, true)}
        </tbody>
      </table>
    </div>
  )
}

export function Build2({ d, fb }) {
  const B = d.build, R = B.runes, P = d.plus, S = P && P.site
  const fbb = (fb && fb.build) || {}
  const rstat = Object.fromEntries(((S && S.runes) || []).map((r) => [r.n, r.stat]))
  const pct = (n) => (S ? <span className="bd2-rp num">{rstat[n] ? `${rstat[n].pick}%` : '3% 미만'}</span> : null)
  const cell = (p, cls, key) => <div key={key} className={cx('r-cell', cls)}><Pi p={p} cls="ic ic-md ic-rune" /><span>{p.n}</span>{pct(p.n)}</div>
  const o = S && S.order, sp = S && S.spells, mx = P && P.dmgMix && P.dmgMix.theirs
  const tot = mx ? mx.phys + mx.magic + mx.true || 1 : 1
  return (
    <Section no="06">
      <div className="bento bd2">
        <div className="cell bd2-time"><Xm />
          <div className="s2-head"><span className="label">완성 아이템, {d.opp.n}와 같은 시간 축{S && S.slots ? `. 내 아이템 아래는 에메랄드 이상 ${d.me.n} ${num(S.champ.games)}판의 평균 완성 시간이에요` : ''}</span>
            <span className="s2-key"><i className="bd2-k-gap" />빨간 선: 피드백에서 짚은 완성 사이 시간</span></div>
          <ItemTimeline2 d={d} fb={fb} S={S} />
          {fbb['아이템'] && <p className="bd2-note">{fbb['아이템']}</p>}
        </div>

        {S && S.slots ? (
          <div className="cell bd2-cmp"><Xm />
            <div className="s2-head"><span className="label">내가 고른 아이템을 다른 {d.me.n}들은 얼마나 고르나. 승률은 그 아이템을 그 순서로 산 판의 승률이에요</span></div>
            <PickTable S={S} />
          </div>
        ) : (
          <div className="cell bd2-cmp"><Xm /><p className="lab-empty">이 챔피언은 아직 빌드 통계를 가져오지 않았어요.</p></div>
        )}
        <div className="cell bd2-side"><Xm />
          {o && (
            <div className="bd2-side-b">
              <span className="label">완성 순서</span>
              <div className="bd-order">{o.mine.map((it, i) => <span key={i}>{i > 0 && <i aria-hidden="true">→</i>}<Ii it={it} size="sm" /></span>)}</div>
              {o.stat ? <p className="bd2-big"><b className="num">{p1(o.stat.pick)}<small>%</small></b><span className="small">가 같은 순서로 가요({o.rank}번째로 많음). 승률 <b className="num">{p1(o.stat.win)}%</b></span></p>
                : <p className="small muted">많이 가는 순서 6개 안에 없어요</p>}
            </div>
          )}
          {mx && (
            <div className="bd2-side-b">
              <span className="label">상대 팀이 넣은 피해 구성</span>
              <div className="mix-bar is-theirs bd-mix">{[mx.phys, mx.magic, mx.true].map((v, i) => <span key={i} className={`mx-${i}`} style={{ width: `${(100 * v) / tot}%` }} />)}</div>
              <p className="small num">물리 {Math.round((100 * mx.phys) / tot)}%, 마법 {Math.round((100 * mx.magic) / tot)}%, 고정 {Math.round((100 * mx.true) / tot)}%</p>
            </div>
          )}
        </div>

        <div className="cell bd2-buys"><Xm />
          <div className="s2-head"><span className="label">전체 구매 순서 (큰 아이콘이 완성 아이템)</span></div>
          <ol className="bt-list">
            {B.buys.map((g, i) => (
              <li key={i}>
                <div className="bt-items">{g.items.map((it, j) => (it.done ? <Ii key={j} it={it} size="md" extra="is-core" /> : <Ii key={j} it={it} size="xs" />))}</div>
                <time>{mmss(g.t)}</time>
              </li>
            ))}
          </ol>
        </div>

        <div className="cell bd2-rune"><Xm />
          <div className="s2-head"><span className="label">룬{S ? `. 숫자는 다른 ${d.me.n}들이 그 룬을 고른 비율이에요` : ''}</span></div>
          <div className="runes">
            <div className="r-h p"><Pi p={R.primary} cls="ic ic-xs ic-rune" />{R.primary.n}</div>
            <div className="r-h s"><Pi p={R.secondary} cls="ic ic-xs ic-rune" />{R.secondary.n}</div>
            <div className="r-big p"><Pi p={R.keystone} cls="ic ic-lg ic-rune" /><span>{R.keystone.n}</span>{pct(R.keystone.n)}</div>
            {R.sub.map((p, j) => cell(p, j === 0 ? 'psub s1' : 'psub', `s${j}`))}
            {R.minor.map((p, j) => cell(p, 'pmin', `m${j}`))}
            <div className="r-shards">{R.shards.map((s, j) => <Pi key={j} p={s} cls="ic ic-rune" />)}</div>
          </div>
          {fbb['룬'] && <p className="bd2-note">{fbb['룬']}</p>}
        </div>
        <div className="cell bd2-spell"><Xm />
          <div className="s2-head"><span className="label">소환사 주문, 쓴 횟수</span></div>
          <ul className="spells">
            {B.spells.map((s) => <li key={s.key}><Pi p={s} cls="ic ic-md" /><span>{s.n}</span><b>{s.casts}<small>번</small></b></li>)}
          </ul>
          {sp && <p className="small bd2-sp">{sp.mine ? <>이 조합은 다른 {d.me.n}의 <b className="num">{p1(sp.mine.pick)}%</b>가 골라요. 승률 <b className="num">{p1(sp.mine.win)}%</b></> : <span className="muted">이 조합은 선택률 1% 미만이에요</span>}</p>}
          {fbb['소환사 주문'] && <p className="bd2-note">{fbb['소환사 주문']}</p>}
          <div className="s2-head bd2-gap"><span className="label">스킬 쓴 횟수</span><span className="small muted num">논타깃 스킬 적중 {B.skillshotsHit}번, 피한 스킬 {B.skillshotsDodged}번</span></div>
          <ul className="skills">
            {B.skills.map((s) => (
              <li key={s.key}>
                <span className="sk-k">{s.img && <Pi p={s} cls="ic ic-xs" />}{s.key}</span>
                <b>{s.casts}</b><span className="muted">분당 {fix(s.perMin, 1)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Section>
  )
}

// ================================================================ 07 체크리스트
// 맨 위 9칸 띠(표시 색 + 번호)와 오른쪽 끝 개수, 아래 카드 3열. 띠 칸과 카드는 마우스를 올리면 서로 강조돼요.
// 항목 순서는 바꾸지 않아요(판끼리 비교할 때 순서가 같아야 해요).
const MARK = { good: ['좋음', 'chip-pos'], mid: ['보통', 'chip-mid'], bad: ['아쉬움', 'chip-bad'], memo: ['메모', 'chip-line'] }
export function Check2({ fb }) {
  const [on, setOn] = useState(null)
  if (!fb) return <Section no="07"><Pending text="체크리스트는 피드백 글을 쓰면 채워져요." /></Section>
  const L = fb.checklist
  const cnt = { good: 0, mid: 0, bad: 0 }
  L.forEach((c) => { if (c.mark in cnt) cnt[c.mark]++ })
  const hv = (i) => ({ onPointerEnter: () => setOn(i), onPointerLeave: () => setOn(null) })
  return (
    <Section no="07">
      <div className="c2-band">
        <ol className="c2-strip" style={{ gridTemplateColumns: `repeat(${L.length}, minmax(0, 1fr))` }}>
          {L.map((c, i) => (
            <li key={i} className={cx(`c2-s c2-${c.mark in MARK ? c.mark : 'memo'}`, on === i && 'on')} {...hv(i)} title={c.name}>
              <span className="num">{String(i + 1).padStart(2, '0')}</span>
              <em>{(MARK[c.mark] || MARK.memo)[0]}</em>
            </li>
          ))}
        </ol>
        <ul className="c2-cnt">
          {Object.entries(cnt).map(([k, v]) => <li key={k}><span className={`chip ${MARK[k][1]}`}>{MARK[k][0]}</span><b className="num">{v}</b></li>)}
        </ul>
      </div>
      <ol className="bento c2-cards">
        {L.map((c, i) => (
          <li key={i} className={cx('cell', `ck-${c.mark}`, on === i && 'on')} {...hv(i)}><Xm />
            <div className="c2-h">
              <span className="c2-no num">{String(i + 1).padStart(2, '0')}</span>
              {MARK[c.mark] && c.mark !== 'memo' && <span className={`chip ${MARK[c.mark][1]}`}>{MARK[c.mark][0]}</span>}
            </div>
            <h3>{c.name}</h3>
            <p>{c.why}</p>
          </li>
        ))}
      </ol>
    </Section>
  )
}
