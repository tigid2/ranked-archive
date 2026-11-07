import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

// 두 가지로 빌드해요.
//  - 기본(npm run build): GitHub Pages용. docs/report/ 에 저장. 판별 데이터는 열릴 때 ../report-data/<경기ID>.json 을 읽어요.
//  - single(npm run build:single): artifact용 한 파일. web/dist-single/index.html 에 저장.
//    tools/report/single.py가 여기에 데이터, 아이콘, 글꼴을 넣어 완성해요.
const FONT_LINKS =
  '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&display=swap">' +
  '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">'

export default defineConfig(({ mode, command }) => {
  const single = mode === 'single'
  return {
    base: './',
    plugins: [
      react(),
      single && viteSingleFile(),
      {
        name: 'font-links',
        transformIndexHtml: (html) => html.replace('<!--FONTS-->', single ? '<style>/*FONTS*/</style>' : FONT_LINKS),
      },
    ].filter(Boolean),
    // 개발 서버에서는 docs/ 를 그대로 보여 줘서 /report-data/ 를 읽을 수 있게 해요. 빌드에는 넣지 않아요.
    publicDir: command === 'serve' ? '../docs' : false,
    define: { __SINGLE__: JSON.stringify(single) },
    build: {
      outDir: single ? 'dist-single' : '../docs/report',
      emptyOutDir: true,
      assetsInlineLimit: single ? 100000000 : 4096,
    },
    server: { fs: { allow: ['..'] } },
  }
})
