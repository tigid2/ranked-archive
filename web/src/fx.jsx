// 인터랙션 조각 모음 (2026-11-17 시안)
// 숫자 굴리기, 화면에 들어왔는지 보기, 글자 안 홀로그램 질감, 커서를 따라다니는 작은 지도
import { useEffect, useRef, useState } from 'react'
import './fx.css'

export const reduceMotion = () => typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches

// 페이지가 다 뜬 뒤(그림, 글꼴까지) 잠깐 쉬고 true가 돼요.
// 예전에는 4MB짜리 한 파일 리포트가 뜨는 동안 숫자와 점수 움직임이 다 끝나 버려서 볼 수가 없었어요(11-22).
let readyP = null
function pageReady() {
  if (!readyP) {
    readyP = new Promise((res) => {
      const go = () => {
        const f = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()
        f.then(() => setTimeout(res, 400))
      }
      if (document.readyState === 'complete') go()
      else window.addEventListener('load', go, { once: true })
    })
  }
  return readyP
}
export function useReady() {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    let on = true
    pageReady().then(() => on && setReady(true))
    return () => { on = false }
  }, [])
  return ready
}

// 화면에 한 번이라도 들어왔는지
export function useInView(margin = '0px 0px -12% 0px') {
  const ref = useRef(null)
  const [seen, setSeen] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el || seen) return undefined
    const io = new IntersectionObserver((es) => es.some((e) => e.isIntersecting) && setSeen(true), { rootMargin: margin })
    io.observe(el)
    return () => io.disconnect()
  }, [seen, margin])
  return [ref, seen]
}

// 자릿수마다 굴러가는 숫자
export function Roll({ value, digits }) {
  const str = String(Math.max(0, Math.round(value))).padStart(digits || 1, '0')
  return (
    <span className="rd-wrap" aria-label={String(value)}>
      {[...str].map((ch, i) => (
        <span key={str.length - i} className={i < str.length - 1 && /^0*$/.test(str.slice(0, i + 1)) ? 'rd lead' : 'rd'} aria-hidden="true">
          <span className="rd-s" style={{ transform: `translateY(${-ch * 10}%)` }}>{'0\n1\n2\n3\n4\n5\n6\n7\n8\n9'}</span>
        </span>
      ))}
    </span>
  )
}

// 0에서 목표 숫자까지 올라가는 숫자
export function Count({ to, fmt = (n) => String(n), ms = 900 }) {
  const [ref, inView] = useInView('0px')
  const ready = useReady()
  const seen = inView && ready
  const [v, setV] = useState(reduceMotion() ? to : 0)
  useEffect(() => {
    if (!seen || reduceMotion()) return undefined
    let raf, t0
    const step = (t) => {
      t0 = t0 || t
      const p = Math.min(1, (t - t0) / ms)
      setV(Math.round(to * (1 - Math.pow(1 - p, 3))))
      if (p < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [seen, to, ms])
  return <span ref={ref}>{fmt(v)}</span>
}

// 연한 홀로그램 질감 그림을 한 번 만들어서 CSS 변수 --holo 에 넣어요 (메인 페이지와 같은 그림)
let holoDone = false
export function ensureHolo() {
  if (holoDone || typeof document === 'undefined') return
  holoDone = true
  const tex = document.createElement('canvas'); tex.width = 800; tex.height = 500
  const t = tex.getContext('2d'), W = tex.width, H = tex.height
  let seed = 7
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647
  t.fillStyle = '#d3e2f7'; t.fillRect(0, 0, W, H)
  const cols = ['#8fd0ff', '#bca6ff', '#ffaedd', '#ffe89a', '#8ff0dc', '#ffffff', '#a3b8ff', '#ffc9b0', '#ffffff']
  for (let i = 0; i < 46; i++) {
    const x = rnd() * W, y = rnd() * H, r = 56 + rnd() * 190, c = cols[(rnd() * cols.length) | 0]
    const g = t.createRadialGradient(x, y, 0, x, y, r)
    g.addColorStop(0, c + 'e6'); g.addColorStop(1, c + '00')
    t.fillStyle = g; t.beginPath(); t.ellipse(x, y, r * (0.6 + rnd()), r * (0.35 + rnd() * 0.5), rnd() * 3.14, 0, 6.3); t.fill()
  }
  t.save(); t.translate(W / 2, H / 2); t.rotate(-0.5); t.globalCompositeOperation = 'soft-light'
  for (let i = 0; i < 70; i++) { t.fillStyle = `rgba(255,255,255,${0.12 + rnd() * 0.5})`; t.fillRect(-W + rnd() * W * 2, -H, 2 + rnd() * 36, H * 2) }
  t.restore()
  const im = t.getImageData(0, 0, W, H), d = im.data
  for (let i = 0; i < d.length; i += 4) { const n = (rnd() - 0.5) * 26; d[i] += n; d[i + 1] += n; d[i + 2] += n }
  t.putImageData(im, 0, 0)
  document.documentElement.style.setProperty('--holo', `url(${tex.toDataURL('image/jpeg', 0.86)})`)
}

// 글자 안 질감: area 안에서 마우스를 움직이면 마우스 근처 글자에만 질감이 드러나요
export function Foil({ children, radius = 150, area }) {
  const ref = useRef(null)
  useEffect(() => {
    ensureHolo()
    const el = ref.current
    const box = (area && el.closest(area)) || el
    const move = (e) => {
      const r = el.getBoundingClientRect()
      el.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100).toFixed(1))
      el.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100).toFixed(1))
      el.style.setProperty('--fr', `${e.buttons ? radius * 1.7 : radius}px`)
    }
    const leave = () => el.style.setProperty('--fr', '0px')
    box.addEventListener('pointermove', move)
    box.addEventListener('pointerleave', leave)
    return () => { box.removeEventListener('pointermove', move); box.removeEventListener('pointerleave', leave) }
  }, [radius, area])
  return <span className="foil" ref={ref}>{children}<span className="foil-fill" aria-hidden="true">{children}</span></span>
}

// 커서를 따라다니는 작은 상자 (죽음 줄 위에서 작은 지도를 보여 줘요)
export function Follower({ show, children }) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    let x = 0, y = 0, tx = 0, ty = 0, raf = 0, first = true
    const move = (e) => { tx = e.clientX; ty = e.clientY; if (first) { x = tx; y = ty; first = false } }
    const loop = () => {
      x += (tx - x) * 0.22; y += (ty - y) * 0.22
      el.style.transform = `translate3d(${x.toFixed(1)}px,${y.toFixed(1)}px,0)`
      raf = requestAnimationFrame(loop)
    }
    addEventListener('pointermove', move, { passive: true })
    raf = requestAnimationFrame(loop)
    return () => { removeEventListener('pointermove', move); cancelAnimationFrame(raf) }
  }, [])
  return <div className={`follower${show ? ' on' : ''}`} ref={ref} aria-hidden="true">{children}</div>
}

// 화면에 고정된 구역에서 얼마나 스크롤했는지 (0~1)
export function usePin(onProgress) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return undefined  // 다음 판이 없는 최신 판은 이 구역이 없어요
    let ticking = false
    const frame = () => {
      ticking = false
      const r = el.getBoundingClientRect()
      onProgress(Math.min(1, Math.max(0, -r.top / Math.max(1, r.height - innerHeight))), el)
    }
    const req = () => { if (!ticking) { ticking = true; requestAnimationFrame(frame) } }
    addEventListener('scroll', req, { passive: true }); addEventListener('resize', req)
    frame()
    return () => { removeEventListener('scroll', req); removeEventListener('resize', req) }
  }, [onProgress])
  return ref
}
