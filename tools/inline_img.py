import base64, os, re, sys
src, dst = sys.argv[1], sys.argv[2]
base = os.path.dirname(src)
h = open(src, encoding="utf-8").read()
cache = {}
def rep(m):
    attr, path = m.group(1), m.group(2)
    if path not in cache:
        data = open(os.path.join(base, path), "rb").read()
        cache[path] = "data:image/png;base64," + base64.b64encode(data).decode()
    return f'{attr}="{cache[path]}"'
h = re.sub(r'(src|href)="(img/[^"]+)"', rep, h)
open(dst, "w", encoding="utf-8").write(h)
print(len(cache), "images,", len(h)//1024, "KB, leftover img/ refs:", h.count('"img/'))
