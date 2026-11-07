"""죽음 지도에 쓰는 흑백 지도 이미지를 만들어요. (패치로 지도 그림이 바뀌었을 때만 다시 실행)

iOS Safari는 SVG 안 이미지에 CSS filter를 적용하지 않아서, 이미지 자체를 흑백으로 만들어 둬요.
순서: 회색조 → 밝기 0.62 → 대비 1.1

사용: python make_gray_map.py <map11.png> <저장할 경로, 예: data/map11_gray.png>
필요: pip install pillow --break-system-packages
"""
import sys

from PIL import Image, ImageEnhance

src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("L")
im = ImageEnhance.Brightness(im).enhance(0.62)
im = ImageEnhance.Contrast(im).enhance(1.1)
im.convert("RGB").save(dst)
print("saved", dst)
