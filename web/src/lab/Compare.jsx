// 세 버전 비교(11-24, 7-0 6단계 전 검토용). 같은 섹션을 버전 1 → 2 → 3 순서로 세로로 이어 붙여요.
// 버전 1: 지금 공개 리포트(sections/), 버전 2: 첫 시안(Draft.jsx의 Summary2, Flow2와 DraftRest.jsx),
// 버전 3: 정보 위계 시안(Draft3.jsx). 버전 3은 01~03과 04 머리만 있어요.
// artifact 한 파일(window.__COMPARE__)에서만 보여요. 공개 사이트 빌드에는 들어가지 않아요.
import { Fragment } from 'react'
import { SPRITE, SECTIONS } from '../ui.jsx'
import Hero from '../sections/Hero.jsx'
import Summary from '../sections/Summary.jsx'
import Flow from '../sections/Flow.jsx'
import Lane from '../sections/Lane.jsx'
import Deaths from '../sections/Deaths.jsx'
import Team from '../sections/Team.jsx'
import Build from '../sections/Build.jsx'
import { Checklist } from '../sections/Check.jsx'
import { Summary2, Flow2 } from './Draft.jsx'
import { Lane2, Team2, Build2, Check2 } from './DraftRest.jsx'
import { Summary3, Flow3, Lane3, DeathHead } from './Draft3.jsx'
import './draft.css'
import './draft3.css'
import './compare.css'

const NAMES = { 1: '기본', 2: '디자인 개선', 3: '정보 위계' }
const SUBS = { 1: '지금 공개 리포트', 2: '첫 시안, 11-24 낮', 3: '2차 시안, 11-24 저녁' }

// 섹션마다 버전별로 무엇이 들어 있고 앞 버전에서 무엇이 바뀌었는지 한 줄씩 적어요. 좋고 나쁨은 적지 않아요.
const NOTE = {
  '01': {
    1: '요약 글, 개선점 2개, 다음 판 목표가 있고 그 아래에 플레이 스타일 그래프가 따로 있어요.',
    2: '격자 한 판에 묶었어요. 레이더 옆에 축마다 나와 평균 막대를 붙이고, 집중력 칸을 더했어요.',
    3: '요약과 개선점은 그대로예요. 막대 대신 14분 숫자 표(03의 점 그래프를 합침)를 붙이고, 집중력 칸을 뺐어요.',
  },
  '02': {
    1: '분당 골드 차이 그래프, 구간별 성적과 맞라인 차이, 유불리 운영, 집중력, 주요 순간 목록이 차례로 있어요.',
    2: '탭 4개(팀 골드, 맞라인 골드, CS, 레벨), 구간 누르기, 바텀 2대2 점선, 유불리 막대, 주요 순간 번호 격자로 바꿨어요.',
    3: '팀 골드 한 장으로 줄였어요. 내 죽음은 선 위 번호(누르면 이 아래 버전 3의 04에서 열려요), 변곡 주석, 오른쪽에 라인별 차이 막대를 넣었어요. 탭, 구간 누르기, 점선, 주요 순간 격자는 뺐어요.',
  },
  '03': {
    1: '라인전 숫자 칸, 레벨 도달 시간, 서폿 유무별 CS, 상성, 14분 라인전 표, 첫 귀환이 칸마다 따로 있어요.',
    2: '10분, 15분 맞라인 숫자, 레벨 선점, 첫 귀환, 서폿 있던 분, 14분 점 그래프를 격자 한 판에 묶었어요.',
    3: '14분 맞라인 차이와 서폿 있을 때, 없을 때 CS를 크게 두고, 상성 승률, 레벨 선점, 첫 귀환은 작은 참고 칸으로 내렸어요.',
  },
  '04': {
    1: '11-19 새 배치예요. 위 막대, 왼쪽 지도 무대, 오른쪽 죽음 목록, 아래 숫자 띠가 있어요.',
    2: '버전 2는 04를 바꾸지 않았어요. 죽음이 3번 이하인 판에서 첫 죽음을 펼쳐 두는 것만 달라서, 이 판에서는 버전 1과 같아요.',
    3: '머리에 큰 죽음 수와 죽음 x 유형 칸 표를 더하고, 아래 숫자 띠를 숨겼어요. 본문은 버전 1과 같아요.',
  },
  '05': {
    1: '두 팀 표가 있어요.',
    2: '표 위에 팀 비교 10개를 큰 숫자 칸으로 더했어요. 두 팀 표는 그대로예요.',
  },
  '06': {
    1: '완성 아이템 시점, 전체 구매 순서, 룬, 소환사 주문, 스킬, 빌드 비교 표가 따로 있어요.',
    2: '세 번 나오던 아이템을 한 칸으로 합쳤어요. 시간 축 위 완성 아이템에 평균 완성 시간을 붙이고, 룬과 주문 선택률은 각 칸 안으로 옮겼어요.',
  },
  '07': {
    1: '체크리스트 카드가 차례로 있어요.',
    2: '맨 위에 9칸 띠와 개수를 두고, 아래 카드를 3열로 놓았어요. 띠와 카드는 마우스를 올리면 서로 강조돼요.',
  },
}

function Band({ no, v, missing }) {
  return (
    <div className={missing ? 'cmp-band is-missing' : 'cmp-band'} id={`c${no}-${v}`}>
      <span className="cmp-v num">V{v}</span>
      <div className="cmp-name"><b>{NAMES[v]}</b><span className="muted">{SUBS[v]}</span></div>
      <p className="cmp-note">{missing ? '버전 3은 아직 만들지 않았어요. 01~04를 정한 뒤 이 섹션을 만들어요.' : NOTE[no][v]}</p>
    </div>
  )
}

function Nav() {
  const rows = SECTIONS.filter(([n]) => n !== '08')
  return (
    <nav className="secnav cmp-nav" aria-label="섹션 이동">
      <ol>{rows.map(([n, t]) => <li key={n}><a href={`#c${n}`}><span className="num">{n}</span>{t}<span className="muted small">{['01', '02', '03', '04'].includes(n) ? 'V1 V2 V3' : 'V1 V2'}</span></a></li>)}</ol>
    </nav>
  )
}

export default function Compare({ data: d }) {
  const fb = d.feedback || null
  const openDeath = (no) => window.dispatchEvent(new CustomEvent('open-death', { detail: no }))
  const groups = [
    ['01', [<Summary fb={fb} d={d} />, <Summary2 fb={fb} d={d} />, <Summary3 fb={fb} d={d} />]],
    ['02', [<Flow d={d} fb={fb} />, <Flow2 d={d} fb={fb} />, <Flow3 d={d} fb={fb} onDeath={openDeath} />]],
    ['03', [<Lane d={d} fb={fb} />, <Lane2 d={d} fb={fb} />, <Lane3 d={d} fb={fb} />]],
    ['04', [<Deaths d={d} fb={fb} />, null, <Deaths d={d} fb={fb} autoOpen head={DeathHead} noStrip />]],
    ['05', [<Team d={d} />, <Team2 d={d} />]],
    ['06', [<Build d={d} fb={fb} />, <Build2 d={d} fb={fb} />]],
    ['07', [<Checklist fb={fb} />, <Check2 fb={fb} />]],
  ]
  return (
    <>
      <div dangerouslySetInnerHTML={{ __html: SPRITE }} style={{ display: 'contents' }} />
      <main className="wrap cmp">
        <Hero d={d} />
        <div className="cmp-intro">
          <p><b>세 버전을 섹션끼리 이어 붙였어요.</b> 섹션마다 V1 기본, V2 디자인 개선, V3 정보 위계 순서로 내려가요. 각 버전 위 한 줄은 앞 버전에서 무엇이 바뀌었는지만 적었어요.</p>
          <p className="muted">V3는 01~03과 04 머리만 있어요. 05~07은 V1과 V2만 비교할 수 있어요. 08 메모는 어느 시안에서도 바꾸지 않아서 뺐어요.</p>
        </div>
        <Nav />
        {groups.map(([no, vs]) => (
          <div className="cmp-group" id={`c${no}`} key={no}>
            {[1, 2, 3].map((v) => (
              <Fragment key={v}>
                <Band no={no} v={v} missing={!vs[v - 1] && v === 3 && !NOTE[no][3]} />
                {vs[v - 1]}
              </Fragment>
            ))}
          </div>
        ))}
      </main>
    </>
  )
}
