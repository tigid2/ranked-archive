import { useCallback, useEffect, useState } from 'react'
import { usePin } from './fx.jsx'
import { SECTIONS, SPRITE } from './ui.jsx'
import Hero from './sections/Hero.jsx'
import Summary from './sections/Summary.jsx'
import Flow from './sections/Flow.jsx'
import Lane from './sections/Lane.jsx'
import Deaths from './sections/Deaths.jsx'
import Team from './sections/Team.jsx'
import Build from './sections/Build.jsx'
import { Checklist, Memo } from './sections/Check.jsx'

function SiteNav() {
  // 챔피언 노트, 상성 노트 페이지는 아직 없어서 링크를 막아 둬요.
  const tabs = [['경기 기록', true], ['챔피언 노트', false], ['상성 노트', false]]
  return (
    <nav className="sitenav" aria-label="페이지">
      <ul>{tabs.map(([t, on]) => <li key={t}><a className={on ? 'on' : ''} href="#">{t}</a></li>)}</ul>
    </nav>
  )
}

function SecNav() {
  // 보고 있는 섹션을 메뉴에 점으로 표시하고, 리포트를 얼마나 읽었는지 아래 선으로 보여 줘요.
  useEffect(() => {
    const bar = document.querySelector('.secnav')
    const nav = bar.querySelector('ol')
    const links = [...nav.querySelectorAll('a')]
    const byId = new Map(links.map((a) => [a.getAttribute('href').slice(1), a]))
    const set = (id) => {
      links.forEach((l) => l.classList.toggle('on', l === byId.get(id)))
      const a = byId.get(id)
      if (a) nav.scrollTo({ left: a.offsetLeft - 16, behavior: 'smooth' })
    }
    const io = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && set(e.target.id)),
      { rootMargin: '-40% 0px -55% 0px' })
    const secs = [...document.querySelectorAll('section.sec')]
    secs.forEach((s) => io.observe(s))
    let ticking = false
    const frame = () => {
      ticking = false
      if (!secs.length) return
      const top = secs[0].getBoundingClientRect().top + scrollY - innerHeight * 0.4
      const last = secs[secs.length - 1].getBoundingClientRect()
      const end = last.bottom + scrollY - innerHeight * 0.6
      bar.style.setProperty('--read', Math.min(1, Math.max(0, (scrollY - top) / Math.max(1, end - top))).toFixed(4))
    }
    const req = () => { if (!ticking) { ticking = true; requestAnimationFrame(frame) } }
    addEventListener('scroll', req, { passive: true }); addEventListener('resize', req)
    frame()
    return () => { io.disconnect(); removeEventListener('scroll', req); removeEventListener('resize', req) }
  }, [])
  return (
    <nav className="secnav" aria-label="섹션 이동">
      <ol>{SECTIONS.map(([n, t]) => <li key={n}><a href={`#s${n}`}><i className="sn-dot" aria-hidden="true" /><span className="num">{n}</span>{t}</a></li>)}</ol>
      <span className="sn-read" aria-hidden="true" />
    </nav>
  )
}

// 리포트 끝: 계속 스크롤하면 다음 판으로 넘어가요.
function PageEnd({ next }) {
  const [full, setFull] = useState(false)
  const onProgress = useCallback((p, el) => {
    const v = Math.min(1, p / 0.9)
    el.style.setProperty('--p', v.toFixed(3))
    const pct = el.querySelector('.pe-pct')
    if (pct) pct.textContent = `${Math.round(v * 100)}%`
    setFull(v >= 1)
  }, [])
  const ref = usePin(onProgress)
  useEffect(() => {
    // 공개 사이트에서는 끝까지 스크롤하면 다음 판 리포트로 넘어가요. artifact 한 파일에서는 이동하지 않아요.
    if (!full || __SINGLE__ || !next) return undefined
    const t = setTimeout(() => { location.href = `?id=${next.id}` }, 500)
    return () => clearTimeout(t)
  }, [full, next])
  if (!next) return <div className="page-end" />
  return (
    <section className={full ? 'pe full' : 'pe'} ref={ref}>
      <div className="pe-stage">
        <div className="crosses" aria-hidden="true"><i /><i /><i /><i /><i /><span className="fx-label">KEEP SCROLLING</span></div>
        <div className="pe-mid">
          <span className="fx-label">다음 판 <span className="num">{next.when}</span></span>
          <h2 className="pe-title">{next.champ} <span>vs</span> {next.opp}</h2>
          <span className={`chip ${next.win ? 'chip-pos' : 'chip-mid'}`}>{next.win ? '승리' : '패배'}</span>
          <div className="pe-prog"><span className="pe-bar"><i /></span><span className="pe-pct num">0%</span></div>
          <p className="pe-note">{__SINGLE__ ? '실제 사이트에서는 여기서 다음 판 리포트로 넘어가요. 지금은 한 파일로 보는 중이라 이동하지 않아요.' : '다음 판 리포트로 넘어가요.'}</p>
        </div>
      </div>
    </section>
  )
}

// over: 실험 시안(lab/Draft.jsx)이 섹션 몇 개만 바꿔 끼울 때 써요. 공개 사이트는 넘기지 않아요.
export default function Report({ data, over = {} }) {
  const S01 = over.Summary || Summary, S02 = over.Flow || Flow
  const fb = data.feedback || null
  useEffect(() => {
    document.title = `${data.me.n} ${data.hero.win ? '승리' : '패배'} 리포트`
  }, [data])
  return (
    <>
      <div dangerouslySetInnerHTML={{ __html: SPRITE }} style={{ display: 'contents' }} />
      <main className="wrap">
        <SiteNav />
        <Hero d={data} />
        <SecNav />
        <S01 fb={fb} d={data} />
        <S02 d={data} fb={fb} />
        <Lane d={data} fb={fb} />
        <Deaths d={data} fb={fb} />
        <Team d={data} />
        <Build d={data} fb={fb} />
        <Checklist fb={fb} />
        <Memo fb={fb} />
      </main>
      <PageEnd next={data.nav && data.nav.next} />
      {over.after}
    </>
  )
}
