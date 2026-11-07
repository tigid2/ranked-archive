import { useEffect } from 'react'
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
  // 보고 있는 섹션을 메뉴에 표시해요.
  useEffect(() => {
    const nav = document.querySelector('.secnav ol')
    const links = [...nav.querySelectorAll('a')]
    const byId = new Map(links.map((a) => [a.getAttribute('href').slice(1), a]))
    const set = (id) => {
      links.forEach((l) => l.classList.toggle('on', l === byId.get(id)))
      const a = byId.get(id)
      if (a) nav.scrollTo({ left: a.offsetLeft - 16, behavior: 'smooth' })
    }
    const io = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && set(e.target.id)),
      { rootMargin: '-40% 0px -55% 0px' })
    document.querySelectorAll('section.sec').forEach((s) => io.observe(s))
    return () => io.disconnect()
  }, [])
  return (
    <nav className="secnav" aria-label="섹션 이동">
      <ol>{SECTIONS.map(([n, t]) => <li key={n}><a href={`#s${n}`}><span className="num">{n}</span>{t}</a></li>)}</ol>
    </nav>
  )
}

export default function Report({ data }) {
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
        <Summary fb={fb} />
        <Flow d={data} fb={fb} />
        <Lane d={data} fb={fb} />
        <Deaths d={data} fb={fb} />
        <Team d={data} />
        <Build d={data} fb={fb} />
        <Checklist fb={fb} />
        <Memo fb={fb} />
        <div className="page-end" />
      </main>
    </>
  )
}
