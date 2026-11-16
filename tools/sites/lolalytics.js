// lolalytics 챔피언 빌드 페이지(?tier=emerald_plus)를 내장 브라우저에서 열고 이 코드를 실행하면
// 숫자만 담은 JSON을 돌려줘요. 패치마다 한 번, 사람이 볼 때처럼 한 페이지씩만 읽어요.
// 쓰는 법: tools/sites/README.md
(async () => {
  for (let y = 0; y < document.documentElement.scrollHeight + 2000; y += 500) {
    window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 250))
  }
  await new Promise((r) => setTimeout(r, 1500))
  const T = []
  const walk = (n) => {
    if (n.nodeType === 3) { const t = n.textContent.trim(); if (t && t !== 'Loading...') T.push(t); return }
    if (n.nodeType !== 1) return
    if (['SCRIPT', 'STYLE', 'SVG', 'svg', 'CANVAS'].includes(n.tagName)) return
    if (n.tagName === 'IMG') {
      const m = n.src.match(/lolalytics\.com\/([a-z]+)\d+\/([^/.]+)\./)
      if (m) T.push({ kind: m[1], id: m[2], alt: n.alt })
      return
    }
    for (const c of n.childNodes) walk(c)
  }
  walk(document.querySelector('main'))
  const num = (t) => typeof t === 'string' && /^-?[\d,]+(\.\d+)?$/.test(t) ? +t.replace(/,/g, '') : null
  const isImg = (t, kind) => t && typeof t === 'object' && (!kind || t.kind === kind)
  const find = (seq, from = 0) => {
    for (let i = from; i <= T.length - seq.length; i++) if (seq.every((s, j) => T[i + j] === s)) return i + seq.length
    return -1
  }
  // 그림 여러 개 + 숫자 nNum개로 된 줄을 읽어요. 줄이 아닌 것이 나오면 멈춰요.
  const rows = (start, kind, nNum, stop) => {
    const out = []; let i = start
    while (i > 0 && i < T.length) {
      if (stop && stop(T[i])) break
      const imgs = []
      while (isImg(T[i], kind) || T[i] === 'x' || (imgs.length && T[i - 1] === 'x' && num(T[i]) !== null) || T[i] === 'No') {
        if (T[i] === 'No') { i += 2; imgs.push({ id: 'none' }); continue }
        if (isImg(T[i])) imgs.push(T[i]); i++
      }
      if (!imgs.length) break
      const ns = []
      while (ns.length < nNum && num(T[i]) !== null) ns.push(num(T[i++]))
      if (ns.length < nNum - 1) break
      out.push({ ids: imgs.map((x) => x.id), names: imgs.map((x) => x.alt), n: ns })
    }
    return out
  }
  const keep = (rs, minGames, gi) => rs.filter((r) => r.n[gi] >= minGames)
  const R = { url: location.href }
  const txt = T.filter((t) => typeof t === 'string')
  const after = (label) => { const i = txt.indexOf(label); return i > 0 ? num(txt[i - 2]) ?? num(txt[i - 1]) : null }
  R.patch = txt[txt.indexOf('Patch') + 1]
  R.tier = txt[txt.indexOf('Patch') - 1]
  R.winRate = after('Win Rate'); R.pickRate = after('Pick Rate'); R.banRate = after('Ban Rate')
  R.games = num(txt[txt.indexOf('Games') - 1])
  R.avgWinRate = num(txt[txt.findIndex((t) => /^Average .* Win Rate:$/.test(t)) + 1])
  const tb = (rs, map) => rs.map(map)
  R.spells = tb(keep(rows(find(['Summoner', 'Spells', 'Win Rate', 'Pick Rate', 'Games']), 'spell', 3), 1000, 2),
    (r) => ({ ids: r.ids.map(Number), win: r.n[0], pick: r.n[1], games: r.n[2] }))
  R.starting = tb(keep(rows(find(['Starting', 'Items Sets', 'Win Rate', 'Pick Rate', 'Games']), 'item', 3), 1000, 2),
    (r) => ({ ids: r.ids.map(Number), win: r.n[0], pick: r.n[1], games: r.n[2] }))
  const slot = (seq) => tb(keep(rows(find(seq), 'item', 4), 1000, 2),
    (r) => ({ id: +r.ids[0] || r.ids[0], name: r.names[0], win: r.n[0], pick: r.n[1], games: r.n[2], min: r.n[3] ?? null }))
  R.slots = [1, 2, 3, 4, 5].map((k) => slot(['Item', String(k), 'Win Rate', 'Pick Rate', 'Games', 'Time']))
  R.boots = slot(['Boots', 'Win Rate', 'Pick Rate', 'Games', 'Time'])
  // 3개짜리 세트: 'Click Items Below' 앞의 마지막 'Win Rate, Pick Rate, Games' 뒤
  const ci = T.indexOf('Click Items Below to Filter Builds by Item and Item Buy Position')
  let si = -1; for (let i = ci - 1; i > 0; i--) if (T[i] === 'Games' && T[i - 1] === 'Pick Rate') { si = i + 1; break }
  R.sets = tb(keep(rows(si, 'item', 3), 1000, 2), (r) => ({ ids: r.ids.map(Number), win: r.n[0], pick: r.n[1], games: r.n[2] }))
  // 룬: 'Click Keystones' 뒤에 나오는 룬 그림 + 숫자 3개. 앞 묶음은 주 룬, 뒤 묶음은 보조 룬
  const ki = T.indexOf('Click Keystones Below to Filter Builds')
  const oi = find(['Objective', 'Secure', 'Yield'])
  const runes = []
  for (let i = ki; i < oi; i++) if (isImg(T[i], 'rune') && num(T[i + 1]) !== null) runes.push({ id: +T[i].id, name: T[i].alt, win: num(T[i + 1]), pick: num(T[i + 2]), games: num(T[i + 3]) })
  const firstRepeat = runes.findIndex((r, i) => runes.findIndex((x) => x.id === r.id) < i)
  R.runesPrimary = runes.slice(0, firstRepeat < 0 ? runes.length : firstRepeat).filter((r) => r.games >= 1000)
  R.runesSecondary = (firstRepeat < 0 ? [] : runes.slice(firstRepeat)).filter((r) => r.games >= 1000)
  // 오브젝트
  R.objectives = {}
  for (let i = oi; i < T.length; i++) {
    if (typeof T[i] === 'string' && /^(First |Dragon Soul|Blue Side|Red Side)/.test(T[i])) {
      const ns = []; let j = i + 1; while (num(T[j]) !== null && ns.length < 4) ns.push(num(T[j++]))
      R.objectives[T[i]] = ns.length === 4 ? { secure: ns[0], secureWin: ns[1], yield: ns[2], yieldWin: ns[3] } : { share: ns[0], win: ns[1] }
    }
    if (T[i] === 'Water Soul') break
  }
  // 챔피언 평균
  R.stats = {}
  for (const k of ['Physical Damage:', 'Magic Damage:', 'True Damage:', 'Total Damage:', 'Damage Taken:', 'Healing:', 'Kills:', 'Deaths:', 'Assists:', 'Gold:', 'Minions Killed:', 'Jungle CS:']) {
    const i = txt.lastIndexOf(k); if (i > 0) R.stats[k.replace(':', '')] = num(txt[i + 1])
  }
  // 상성/궁합: 'Counter, Win Rate, Delta 1' 머리글마다 한 표. 줄 끝의 [챔피언] 숫자 5개만 읽어요.
  R.tables = []
  for (let i = 0; i < T.length; i++) {
    if (T[i] === 'Counter' && T[i + 1] === 'Win Rate') {
      const lane = isImg(T[i - 1], 'lane') ? T[i - 1].id : null; const list = []
      for (let j = i + 2; j < T.length && !(T[j] === 'Counter' && T[j + 1] === 'Win Rate') && T[j] !== 'Summoner'; j++) {
        if (isImg(T[j], 'champx') || isImg(T[j], 'champ')) {
          const ns = [1, 2, 3, 4, 5].map((k) => num(T[j + k]))
          if (ns.every((x) => x !== null)) list.push({ name: T[j].alt, win: ns[0], d1: ns[1], d2: ns[2], pick: ns[3], games: ns[4] })
        }
      }
      R.tables.push({ lane, list })
    }
  }
  return JSON.stringify(R)
})()
