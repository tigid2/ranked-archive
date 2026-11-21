# -*- coding: utf-8 -*-
"""replay_worker.py — 게임이 끝난 뒤 리플레이를 받아 디코딩하고, 1초 위치만 깃허브에 올려요.

기록 프로그램(logger.py)이 게임이 끝날 때와 처음 켜질 때 이 프로그램을 따로 실행해요.
따로 실행하니까 여기서 문제가 생겨도 기록 프로그램(스펠·미니맵)은 멈추지 않아요.

하는 일
1. 롤 클라이언트(LCU, 내 컴퓨터 안의 클라이언트 주소)에서 최근 솔로 랭크 판을 찾아요.
2. 아직 처리하지 않은 판은 리플레이를 받을 수 있을 때까지 기다렸다가 받아요.
3. 디코더(decoder_dir 폴더의 rofl_extract.py)로 10명의 1초 위치와 와드만 뽑아요.
4. 깃허브 raw/<경기ID>.pos.json.gz 로 올려요. 그러면 "리포트 만들기"가 자동으로 돌아요.
5. 걸린 시간(게임 끝 → 리플레이 준비 → 받기 → 디코딩 → 올리기)을 replay_log.txt와 올리는 파일에 남겨요.
6. 이 프로그램이 받은 리플레이만, 패치가 바뀌면 지워요(연구용으로 직접 받아 둔 리플레이는 건드리지 않아요).

리플레이 원본은 깃허브에 올리지 않아요. 디코더도 내 컴퓨터에만 있어요.
python replay_worker.py               최근 판 처리 (기록 프로그램이 켜질 때 부르는 방식)
python replay_worker.py --after-game  방금 끝난 판이 전적에 보일 때까지 기다린 뒤 처리 (게임 끝에 부르는 방식)
python replay_worker.py --check  클라이언트 연결, 리플레이 폴더, 최근 판 상태만 보여 줘요(아무것도 받지 않아요)
"""
import base64
import http.client
import glob
import json
import os
import socket
import ssl
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
LOG_PATH = os.path.join(HERE, "replay_log.txt")
STATE_PATH = os.path.join(HERE, "replay_state.json")
OUT_DIR = os.path.join(HERE, "replay_out")   # 올리기 전 결과 파일(올리고 나면 지워요)
LOCK_PORT = 47852
SOLO_QUEUE = 420

DEFAULTS = {
    "replay_check": True,
    # 디코더(decode.py, 표 tables_<패치>.json, rofl_extract.py)가 있는 폴더
    "decoder_dir": os.path.join(os.path.expanduser("~"), "Documents", "League of Legends", "Replays", "rofl-decoder"),
    # 롤 설치 폴더(lockfile을 찾을 때 써요). 못 찾으면 실행 중인 클라이언트 정보에서 찾아요.
    "league_dir": r"C:\Riot Games\League of Legends",
    "replay_wait_minutes": 30,     # 게임 끝나고 리플레이를 받을 수 있을 때까지 기다리는 최대 시간
    "replay_lookback_hours": 24,   # 이 시간 안에 끝난 판만 처리해요
    "replay_delete_old_patch": True,  # 이 프로그램이 받은 리플레이 중 지난 패치 것은 지워요
}

LOCAL_CTX = ssl._create_unverified_context()  # 클라이언트 자체 인증서. 127.0.0.1(내 컴퓨터)에만 써요.


def _web_ctx():
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(cafile=certifi.where())
    except Exception:
        pass
    return ctx


WEB_CTX = _web_ctx()


def log(msg):
    line = f"[{datetime.now().strftime('%m-%d %H:%M:%S')}] {msg}"
    try:
        print(line)
    except Exception:
        pass
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        if os.path.getsize(LOG_PATH) > 2_000_000:   # 로그가 너무 커지면 뒤쪽 절반만 남겨요
            with open(LOG_PATH, encoding="utf-8") as f:
                rest = f.read()[-1_000_000:]
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                f.write(rest)
    except Exception:
        pass


def load_config():
    cfg = {}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        pass
    return {**DEFAULTS, **cfg}


def load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"done": {}, "downloaded": {}}


def save_state(st):
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_PATH)


# ---------------------------------------------------------------- 롤 클라이언트(LCU)

class LCU:
    def __init__(self, port, password):
        self.base = f"https://127.0.0.1:{port}"
        self.auth = "Basic " + base64.b64encode(f"riot:{password}".encode()).decode()

    def req(self, method, path, body=None):
        r = urllib.request.Request(self.base + path, method=method,
                                   data=json.dumps(body).encode() if body is not None else None,
                                   headers={"Authorization": self.auth, "Accept": "application/json",
                                            "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=15, context=LOCAL_CTX) as resp:
                txt = resp.read().decode("utf-8", "replace")
                return resp.status, (json.loads(txt) if txt.strip() else None)
        except urllib.error.HTTPError as e:
            txt = e.read().decode("utf-8", "replace")
            try:
                return e.code, json.loads(txt)
            except Exception:
                return e.code, txt
        except (urllib.error.URLError, http.client.HTTPException, OSError):
            # 게임이 끝난 직후 클라이언트가 다시 뜨는 동안에는 연결이 끊길 수 있어요.
            # 예전에는 여기서 프로그램이 멈춰서 그 판의 위치 파일이 안 올라갔어요(11-22). 이제 '연결 안 됨'(0)으로 보고 다시 기다려요.
            return 0, None

    def get(self, path):
        return self.req("GET", path)

    def post(self, path, body=None):
        return self.req("POST", path, body if body is not None else {})


def find_lcu(cfg):
    """lockfile(이름:pid:포트:비밀번호:https)에서 클라이언트 주소를 찾아요. 클라이언트가 꺼져 있으면 None."""
    cands = [os.path.join(cfg["league_dir"], "lockfile")]
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"name='LeagueClientUx.exe'\").CommandLine"],
            capture_output=True, text=True, timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        for part in out.split('"'):
            if part.startswith("--install-directory="):
                cands.append(os.path.join(part.split("=", 1)[1], "lockfile"))
            if part.startswith("--app-port="):
                port = part.split("=", 1)[1]
            if part.startswith("--remoting-auth-token="):
                token = part.split("=", 1)[1]
        if "port" in locals() and "token" in locals():
            return LCU(port, token)
    except Exception:
        pass
    for p in cands:
        try:
            with open(p, encoding="utf-8") as f:
                _, _, port, pw, _ = f.read().strip().split(":")
            return LCU(port, pw)
        except Exception:
            continue
    return None


def wait_lcu(cfg, minutes):
    end = time.time() + minutes * 60
    while True:
        lcu = find_lcu(cfg)
        if lcu:
            code, _ = lcu.get("/lol-summoner/v1/current-summoner")
            if code == 200:
                return lcu
        if time.time() > end:
            return None
        time.sleep(20)


def recent_games(lcu):
    code, data = lcu.get("/lol-match-history/v1/products/lol/current-summoner/matches?begIndex=0&endIndex=9")
    if code != 200 or not isinstance(data, dict):
        return []
    return (data.get("games") or {}).get("games") or []


def replay_dir(lcu):
    code, data = lcu.get("/lol-replays/v1/rofls/path")
    if code == 200 and isinstance(data, str) and data:
        return data
    return os.path.join(os.path.expanduser("~"), "Documents", "League of Legends", "Replays")


def replay_state(lcu, g):
    """리플레이 상태: checking(확인 중) / download(받을 수 있음) / downloading / watch(받아 둠) /
    incompatible, missingOrExpired, lost, error(못 받음)"""
    gid = g["gameId"]
    code, data = lcu.get(f"/lol-replays/v1/metadata/{gid}")
    if code == 404 or not isinstance(data, dict):
        # 클라이언트가 아직 이 판을 모르면 등록해요(전적 화면을 열면 클라이언트가 하는 일과 같아요)
        lcu.post(f"/lol-replays/v1/metadata/{gid}/create-gameversion/{g.get('gameVersion', '')}"
                 f"/gametype/{g.get('gameType', 'MATCHED_GAME')}/queueId/{g.get('queueId', SOLO_QUEUE)}")
        code, data = lcu.get(f"/lol-replays/v1/metadata/{gid}")
    return (data or {}).get("state") if isinstance(data, dict) else f"http{code}"


def in_game():
    """다음 판이 이미 시작됐는지(게임 안 정보 주소 2999가 열려 있는지) 봐요."""
    try:
        with urllib.request.urlopen("https://127.0.0.1:2999/liveclientdata/gamestats", timeout=2, context=LOCAL_CTX):
            return True
    except Exception:
        return False


def wait_not_in_game():
    """게임 중에는 받기·디코딩을 미뤄요(게임 렉 방지). 게임이 끝나면 이어서 해요."""
    told = False
    while in_game():
        if not told:
            log("  게임 중이라 끝날 때까지 기다릴게요.")
            told = True
        time.sleep(30)


def wait_new_game(lcu, since, minutes=10):
    """게임이 끝난 직후에는 전적에 새 판이 바로 안 보일 수 있어요. 끝난 시각이 since 뒤인 판이 보일 때까지 기다려요."""
    end = time.time() + minutes * 60
    while time.time() < end:
        gs = recent_games(lcu)
        if any(g.get("gameCreation", 0) / 1000 + int(g.get("gameDuration", 0)) >= since for g in gs):
            return gs
        time.sleep(20)
    return recent_games(lcu)


# ---------------------------------------------------------------- 받기 → 디코딩 → 올리기

def fetch_replay(lcu, g, cfg, timing):
    """리플레이를 받아 파일 경로를 돌려줘요. 못 받으면 None."""
    gid = g["gameId"]
    rdir = replay_dir(lcu)
    path = os.path.join(rdir, f"{g.get('platformId', 'KR')}-{gid}.rofl")
    end_wait = time.time() + cfg["replay_wait_minutes"] * 60
    asked = 0
    last = None
    while time.time() < end_wait:
        wait_not_in_game()
        st = replay_state(lcu, g)
        if st != last:
            log(f"  {gid} 리플레이 상태: {st}")
            last = st
        if st == "watch":
            if not os.path.exists(path):   # 파일 이름 앞부분(지역)이 다르면 경기 번호로 찾아요
                path = next(iter(glob.glob(os.path.join(rdir, f"*-{gid}.rofl"))), path)
            if os.path.exists(path):
                break
        if st in ("download", "retryDownload") and time.time() - asked > 30:
            timing.setdefault("readyAt", time.time())
            body = {"componentType": "replay-button_match-history"}
            code, _ = lcu.post(f"/lol-replays/v1/rofls/{gid}/download/graceful", body)
            if code >= 400:
                code, _ = lcu.post(f"/lol-replays/v1/rofls/{gid}/download", body)
            log(f"  {gid} 리플레이 받기 요청 (응답 {code})")
            asked = time.time()
        elif st in ("incompatible", "missingOrExpired", "lost", "unsupported"):
            log(f"  {gid} 리플레이를 받을 수 없는 상태예요({st}). 이 판은 미니맵 기록만 써요.")
            return None
        time.sleep(5)
    else:
        log(f"  {gid} {cfg['replay_wait_minutes']}분 안에 리플레이를 받지 못했어요(마지막 상태: {last}). 다음에 다시 해 볼게요.")
        return False
    time.sleep(2)  # 파일 쓰기가 끝나도록 잠깐 기다려요
    timing["downloadedAt"] = time.time()
    return path


def decode(cfg, rofl, out_path):
    """디코더로 위치·와드 파일을 만들어요. 패치에 맞는 표가 없으면 None."""
    ddir = cfg["decoder_dir"]
    if not os.path.exists(os.path.join(ddir, "rofl_extract.py")):
        log(f"  디코더를 찾지 못했어요({ddir}). config.json의 decoder_dir을 확인해 주세요.")
        return None
    with open(rofl, "rb") as f:
        head = f.read(64)
    ver = head[15:15 + head[14]].decode("ascii", "replace")
    tables = find_tables(ddir, ver)
    if not tables:
        log(f"  패치 {ver} 표가 아직 없어요. 이 판은 미니맵 기록만 써요. (새 패치 표를 만들 때 이 리플레이를 써요)")
        return None
    if os.path.basename(tables) != f"tables_{ver}.json":
        log(f"  {ver} 표가 따로 없어서 같은 패치의 {os.path.basename(tables)}로 디코딩해 봐요(핫픽스 빌드). 결과가 이상하면 건너뛰어요.")
    wait_not_in_game()
    if not has_zstd() and not ensure_module("zstandard"):
        return None
    try:
        if ddir not in sys.path:
            sys.path.insert(0, ddir)
        import rofl_extract
        rofl_extract.save(rofl_extract.extract(tables, rofl), out_path)
    except Exception:
        log("  디코딩 실패:\n" + traceback.format_exc()[-1500:])
        return None
    return ver


def has_zstd():
    """디코더는 zstandard 또는 파이썬 3.14+ 기본 모듈 compression.zstd 중 하나만 있으면 돼요."""
    import importlib.util
    try:
        return bool(importlib.util.find_spec("zstandard") or importlib.util.find_spec("compression.zstd"))
    except ModuleNotFoundError:
        return False


def ensure_module(name):
    """디코더에 필요한 부품이 없으면 이 프로그램을 돌리는 파이썬에 바로 설치해요(install.bat을 안 돌렸거나 다른 파이썬일 때)."""
    import importlib
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        pass
    log(f"  {name}이(가) 없어서 설치할게요({sys.executable}).")
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet", name],
                           capture_output=True, text=True, timeout=300,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        importlib.invalidate_caches()
        import site
        if site.getusersitepackages() not in sys.path:
            sys.path.append(site.getusersitepackages())
        importlib.import_module(name)
        log(f"  {name} 설치 끝.")
        return True
    except Exception as e:
        out = (getattr(locals().get("r"), "stderr", "") or "")[-500:]
        log(f"  {name} 설치 실패({e}). install.bat을 한 번 실행해 주세요.\n{out}")
        return False


def find_tables(ddir, ver):
    """tables_<빌드>.json. 없으면 같은 패치(앞 두 자리, 예: 16.23)의 표 중 가장 최근 것(핫픽스는 보통 표가 같아요)."""
    exact = os.path.join(ddir, f"tables_{ver}.json")
    if os.path.exists(exact):
        return exact
    short = ".".join(ver.split(".")[:2]) + "."
    same = sorted(glob.glob(os.path.join(ddir, f"tables_{short}*.json")), key=os.path.getmtime, reverse=True)
    return same[0] if same else None


def retry_no_tables(cfg, st):
    """표가 없어서 건너뛴 판(no-tables): 그 뒤에 표가 생겼으면 받아 둔 리플레이로 다시 디코딩해서 올려요.
    LCU 전적과 24시간 제한 없이 replay_state.json의 downloaded만 봐요."""
    for gid, info in list(st["done"].items()):
        dl = st["downloaded"].get(gid)
        if info.get("result") != "no-tables" or not dl or not os.path.exists(dl["path"]):
            continue
        if not find_tables(cfg["decoder_dir"], str(dl.get("patch", ""))):
            continue
        mid = f"{os.path.basename(dl['path']).split('-')[0]}_{gid}"
        log(f"{mid} 새 표가 생겨서 다시 디코딩해요.")
        os.makedirs(OUT_DIR, exist_ok=True)
        out = os.path.join(OUT_DIR, f"{mid}.pos.json.gz")
        t0 = time.time()
        if not decode(cfg, dl["path"], out):
            continue
        add_timing(out, {"retry": True, "decodeSec": round(time.time() - t0, 1), "decodedAt": time.time()})
        if not upload(cfg, out, mid):
            return
        os.remove(out)
        st["done"][gid] = {"result": "uploaded", "at": time.time(), "retry": True}
        save_state(st)
        log(f"{mid} 올렸어요(다시 디코딩).")


def add_timing(out_path, timing):
    import gzip
    with gzip.open(out_path, "rt", encoding="utf-8") as f:
        d = json.load(f)
    d["timing"] = timing
    with gzip.open(out_path, "wb", compresslevel=9) as f:
        f.write(json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def upload(cfg, out_path, mid):
    token, repo = str(cfg.get("github_token", "")).strip(), str(cfg.get("repo", "")).strip()
    if not token or "/" not in repo:
        log("  config.json에 github_token과 repo가 없어서 올리지 못했어요.")
        return False
    with open(out_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("ascii")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/contents/raw/{mid}.pos.json.gz", method="PUT",
        data=json.dumps({"message": f"리플레이 위치 추가 ({mid})", "content": content}).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "lol-replay-worker",
                 "Content-Type": "application/json"})
    # 409는 같은 순간에 다른 기록이 올라가며 부딪힌 경우라서, 잠깐 기다렸다 다시 해요.
    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(req, timeout=30, context=WEB_CTX):
                return True
        except urllib.error.HTTPError as e:
            if e.code == 422:   # 이미 올라가 있어요
                return True
            err, again = e.code, e.code == 409 or e.code >= 500
        except Exception as e:
            err, again = e, True
        if not again or attempt == 4:
            break
        log(f"  깃허브 업로드 실패({err}). {attempt * 10}초 뒤 다시 해 볼게요.")
        time.sleep(attempt * 10)
    log(f"  깃허브 업로드 실패({err}). 다음에 다시 시도할게요.")
    return False


def prune_old(st, cur_patch, cfg):
    """이 프로그램이 받은 리플레이 중 지금 패치가 아닌 것은 지워요."""
    if not cfg["replay_delete_old_patch"] or not cur_patch:
        return
    short = ".".join(cur_patch.split(".")[:2])
    for gid, info in list(st["downloaded"].items()):
        if ".".join(str(info.get("patch", "")).split(".")[:2]) == short:
            continue
        try:
            if os.path.exists(info["path"]):
                os.remove(info["path"])
                log(f"지난 패치({info.get('patch')}) 리플레이를 지웠어요: {os.path.basename(info['path'])}")
            del st["downloaded"][gid]
        except Exception as e:
            log(f"리플레이 지우기 실패({e})")


def process(lcu, g, cfg, st):
    gid = str(g["gameId"])
    mid = f"{g.get('platformId', 'KR')}_{gid}"
    end_ms = g.get("gameCreation", 0) + int(g.get("gameDuration", 0)) * 1000
    timing = {"gameEnd": end_ms / 1000, "workerStart": time.time()}
    log(f"{mid} 처리 시작 (게임 끝난 지 {int(time.time() - end_ms / 1000)}초)")
    rofl = fetch_replay(lcu, g, cfg, timing)
    if rofl is False:
        return False            # 다음 실행 때 다시
    if rofl is None:
        st["done"][gid] = {"result": "no-replay", "at": time.time()}
        return True
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"{mid}.pos.json.gz")
    t0 = time.time()
    ver = decode(cfg, rofl, out)
    st["downloaded"][gid] = {"path": rofl, "patch": ver or str(g.get("gameVersion", ""))}
    if not ver:
        st["done"][gid] = {"result": "no-tables", "at": time.time()}
        return True
    timing["decodeSec"] = round(time.time() - t0, 1)
    timing["decodedAt"] = time.time()
    add_timing(out, timing)
    if not upload(cfg, out, mid):
        return False
    timing["uploadedAt"] = time.time()
    os.remove(out)
    st["done"][gid] = {"result": "uploaded", "at": time.time()}
    r = lambda k: f"{timing[k] - timing['gameEnd']:.0f}초" if k in timing else "-"
    log(f"{mid} 올렸어요. 게임 끝에서부터: 받을 수 있게 됨 {r('readyAt')} / 받기 끝 {r('downloadedAt')} / "
        f"디코딩 {timing['decodeSec']}초 / 올리기 끝 {r('uploadedAt')}")
    with open(os.path.join(HERE, "replay_timing.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"matchId": mid, **timing}) + "\n")
    return True


def main(check=False, after_game=False):
    started = time.time()
    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        print("이미 실행 중이에요.")
        return
    cfg = load_config()
    if not cfg["replay_check"] and not check:
        return
    lcu = wait_lcu(cfg, 0 if check else 10)
    if not lcu:
        log("롤 클라이언트를 찾지 못했어요. 다음에 클라이언트가 켜져 있을 때 다시 해 볼게요.")
        return
    if after_game and not check:
        # 기록 프로그램이 게임 끝에 부른 경우: 방금 끝난 판이 전적에 보일 때까지 기다려요(일반 게임이면 그냥 끝나요)
        all_games = wait_new_game(lcu, started - 5 * 60)
    else:
        all_games = recent_games(lcu)
    games = [g for g in all_games if g.get("queueId") == SOLO_QUEUE]
    if check:
        print("클라이언트 연결: 됨")
        print("리플레이 폴더:", replay_dir(lcu))
        print("디코더 폴더:", cfg["decoder_dir"], "있음" if os.path.isdir(cfg["decoder_dir"]) else "없음")
        print("zstd 압축 풀기:", "됨" if has_zstd() else "안 됨 (zstandard 설치 필요)")
        print("디코더 표:", [os.path.basename(p) for p in glob.glob(os.path.join(cfg["decoder_dir"], "tables_*.json"))])
        print(f"최근 솔로 랭크 {len(games)}판:")
        for g in games:
            code, md = lcu.get(f"/lol-replays/v1/metadata/{g['gameId']}")
            when = datetime.fromtimestamp(g.get("gameCreation", 0) / 1000).strftime("%m-%d %H:%M")
            print(f"  {g['gameId']} {when} 패치 {g.get('gameVersion')} 리플레이 상태: "
                  f"{md.get('state') if isinstance(md, dict) else code}")
        return
    st = load_state()
    try:
        retry_no_tables(cfg, st)
    except Exception:
        log("다시 디코딩 중 오류:\n" + traceback.format_exc())
    now = time.time()
    todo = [g for g in games if str(g["gameId"]) not in st["done"]
            and now - (g.get("gameCreation", 0) / 1000) < cfg["replay_lookback_hours"] * 3600]
    if not todo:
        log("새로 처리할 솔로 랭크 판이 없어요.")
    for g in sorted(todo, key=lambda g: g.get("gameCreation", 0)):
        try:
            process(lcu, g, cfg, st)
        except Exception:
            log("처리 중 오류:\n" + traceback.format_exc())
        save_state(st)
    if games:
        prune_old(st, str(games[0].get("gameVersion", "")), cfg)
        save_state(st)


if __name__ == "__main__":
    try:
        main(check="--check" in sys.argv, after_game="--after-game" in sys.argv)
    except Exception:
        log("오류:\n" + traceback.format_exc())
