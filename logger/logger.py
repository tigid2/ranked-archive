# -*- coding: utf-8 -*-
"""
롤 게임 중 기록 프로그램 (Windows용)

하는 일
  - 롤 게임이 시작되면 라이엇 공식 Live Client Data API(내 컴퓨터 안의 127.0.0.1)로
    1초마다 내 골드·체력·생존 여부를 확인해요.
  - 화면 아래쪽 내 스펠 칸 두 개의 밝기를 1초에 2번 확인해서, 스펠이 쿨타임인지 기록해요.
  - 내가 죽을 때마다 정확한 보유 골드, 죽기 직전 체력 흐름, 스펠 상태를 남겨요.
  - 게임이 끝나면 기록을 깃허브 저장소의 live 폴더에 올리고, '경기 기록 갱신'을 자동으로 실행해요.

게임 화면에는 아무것도 띄우지 않아요. 기록은 게임이 끝난 뒤 복기에만 써요.
"""

import base64
import json
import os
import socket
import ssl
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
GAMES_DIR = os.path.join(HERE, "games")
PENDING_DIR = os.path.join(HERE, "pending")
DEBUG_DIR = os.path.join(HERE, "debug")
CACHE_DIR = os.path.join(HERE, "cache")
LOG_PATH = os.path.join(HERE, "logger_log.txt")
SLOT_CACHE = os.path.join(HERE, "cache", "spell_slots.json")  # 한 번 찾은 스펠 칸 위치 (롤 창 크기별)

LIVE_URL = "https://127.0.0.1:2999/liveclientdata/allgamedata"
# 롤이 내 컴퓨터 안에서 쓰는 자체 인증서라 확인을 건너뛰어요. 127.0.0.1(내 컴퓨터)에만 쓰여요.
LOCAL_CTX = ssl._create_unverified_context()


def _web_ctx():
    """깃허브, Data Dragon 같은 인터넷 주소에 접속할 때 쓰는 인증서 목록이에요.
    윈도우 인증서 목록에 깃허브 쪽 인증서가 빠져 있으면 접속이 거부돼서(2026-11-07 업로드 실패 원인),
    파이썬용 인증서 목록(certifi)을 함께 써요. 인증서 확인은 끄지 않아요."""
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(cafile=certifi.where())
    except Exception:
        pass
    return ctx


WEB_CTX = _web_ctx()
PROGRESS_PATH = os.path.join(HERE, "games", "_progress.json")  # 게임 중 기록을 조금씩 저장해 두는 파일 (강제 종료 대비)
PROGRESS_EVERY = 30.0  # 진행 중 기록 저장 간격(초). 죽을 때는 바로 저장해요.
CALIB_UNTIL = 90.0     # 게임 시작 뒤 이 시간(초) 안에 스펠 칸의 실제 모습을 배워요 (이때는 두 스펠 모두 쓸 수 있어요)
LOCK_PORT = 47851

DEFAULT_CONFIG = {
    "github_token": "",
    "repo": "깃허브아이디/lol-review",
    "auto_update": True,
    "spell_check": True,
    "spell_checks_per_second": 4,
    "monitor": 1,
    "save_debug_images": True,
}

STEP = 0.1            # 기본 반복 간격(초). 이 간격마다 할 일이 있는지만 확인해요
POLL_EVERY = 1.0      # 게임 정보 확인 간격(초)
SNAPSHOT_EVERY = 5.0  # 흐름 기록 간격(초)
STALE_READY = 0.6     # 죽기 직전 마지막 확인이 이보다 오래됐으면 '들고 죽음'이라고 단정하지 않아요(초)
AFTER_DEATH_SECONDS = 2.0  # 죽은 직후 스펠 칸을 지켜보는 시간(초)
AFTER_DEATH_GAP = 0.25     # 그때 확인 간격(초)
IDLE_WAIT = 5.0       # 게임이 없을 때 확인 간격(초)
KEEP_DEBUG_IMAGES = 40   # debug 폴더에 남길 데스 이미지 수 (오래된 것부터 지워요)
KEEP_GAME_FILES = 100    # games 폴더에 남길 게임 기록 수 (깃허브에도 올라가 있어서 내 컴퓨터엔 최근 것만)


# ---------------------------------------------------------------- 공통

def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    try:
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 1_000_000:
            os.replace(LOG_PATH, LOG_PATH + ".old")
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    if sys.stdout:
        try:
            print(line)
        except Exception:
            pass


def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    return {**DEFAULT_CONFIG, **cfg}


def single_instance():
    """프로그램이 두 번 켜지지 않게 막아요."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        log("이미 실행 중이라 새로 켜지 않을게요.")
        sys.exit(0)
    return s


def poll_live():
    try:
        with urllib.request.urlopen(LIVE_URL, context=LOCAL_CTX, timeout=2) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def spell_key(spell):
    """'GeneratedTip_SummonerSpell_SummonerFlash_DisplayName' → 'SummonerFlash'"""
    raw = (spell or {}).get("rawDisplayName", "")
    parts = raw.split("_")
    for p in parts:
        if p.startswith("Summoner") and p != "SummonerSpell":
            return p
    return None


def champ_key(player):
    """'game_character_displayname_Jinx' → 'Jinx'"""
    raw = player.get("rawChampionName", "")
    return raw.rsplit("_", 1)[-1] if raw else player.get("championName", "")


def find_me(data):
    ap = data.get("activePlayer") or {}
    ids = {ap.get("riotId"), ap.get("summonerName"), ap.get("riotIdGameName")} - {None, ""}
    for p in data.get("allPlayers", []):
        if {p.get("riotId"), p.get("summonerName"), p.get("riotIdGameName")} & ids:
            return p
    return None


# ---------------------------------------------------------------- 롤 창 확인 (Windows)

def _setup_dpi():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


_U32 = None
LAST_BLOCKER = {"name": None}  # 롤 대신 그 자리에 보이던 창 (로그용)


def _user32():
    global _U32
    if _U32 is None:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        u.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        u.FindWindowW.restype = wintypes.HWND
        u.WindowFromPoint.argtypes = [wintypes.POINT]
        u.WindowFromPoint.restype = wintypes.HWND
        u.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        u.GetAncestor.restype = wintypes.HWND
        u.IsIconic.argtypes = [wintypes.HWND]
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        _U32 = (u, ctypes, wintypes)
    return _U32


def _window_name(u, ctypes, hwnd):
    title = ctypes.create_unicode_buffer(256)
    cls = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(hwnd, title, 256)
    u.GetClassNameW(hwnd, cls, 256)
    return f"{title.value or '(제목 없음)'} / {cls.value}"


def league_window_rect(point=None):
    """롤 게임 창의 위치와 크기를 돌려줘요. 단, 확인하려는 자리(point, 보통 스펠 칸)에
    실제로 롤 화면이 보이고 있을 때만요. 다른 창이 그 자리를 가리고 있거나 롤이 최소화돼 있으면 None이에요.
    (키보드 입력을 받는 창이 아니라 '그 자리에 보이는 창'을 확인해서, 보이지 않는 프로그램이
    잠깐 입력을 가져가도 롤 화면을 계속 읽을 수 있어요.)"""
    try:
        u, ctypes, wintypes = _user32()
        hwnd = u.FindWindowW("RiotWindowClass", None) or u.FindWindowW(None, "League of Legends (TM) Client")
        if not hwnd or u.IsIconic(hwnd) or not u.IsWindowVisible(hwnd):
            LAST_BLOCKER["name"] = "롤 게임 창이 없거나 최소화됨"
            return None
        rect = wintypes.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(rect))
        w, h = rect.right - rect.left, rect.bottom - rect.top
        if w < 400 or h < 300:
            LAST_BLOCKER["name"] = "롤 게임 창이 너무 작음"
            return None
        if point is None:
            point = (rect.left + w // 2, rect.top + int(h * 0.93))  # 화면 아래쪽 가운데(스펠 칸 근처)
        at = u.WindowFromPoint(wintypes.POINT(int(point[0]), int(point[1])))
        root = u.GetAncestor(at, 2) if at else None  # 2 = 가장 바깥 창
        if root != hwnd:
            LAST_BLOCKER["name"] = _window_name(u, ctypes, root) if root else "알 수 없는 창"
            return None
        return (rect.left, rect.top, w, h)
    except Exception as e:
        LAST_BLOCKER["name"] = f"확인 중 오류({e})"
        return None


# ---------------------------------------------------------------- 스펠 칸 읽기

class SpellTracker:
    """화면 아래쪽 내 스펠 칸 두 개를 찾아서 밝기로 쿨타임 여부를 판단해요."""

    def __init__(self, cfg):
        import cv2  # noqa: F401
        import mss
        import numpy  # noqa: F401
        self.cv2 = __import__("cv2")
        self.np = __import__("numpy")
        self.sct = mss.mss()
        mons = self.sct.monitors
        self.mon = mons[cfg["monitor"]] if cfg["monitor"] < len(mons) else mons[1]
        self.save_debug = cfg["save_debug_images"]
        self.keys = [None, None]
        self.templates = [None, None]
        self.slots = None       # [(x, y, size), (x, y, size)] 화면 기준
        self.ref = [[0, 0], [0, 0]]  # 슬롯별 '쓸 수 있을 때' 밝기, 채도
        self.seen = [deque(maxlen=200), deque(maxlen=200)]  # 아이콘이 또렷할 때 잰 (밝기, 채도)
        self.ref_crop = [None, None]   # 슬롯별 '쓸 수 있는 상태'의 실제 화면 모습
        self.ref_tcorr = [0.0, 0.0]    # 그 모습이 공식 아이콘과 얼마나 닮았는지
        self.history = deque(maxlen=60)  # (게임 시간, [상태1, 상태2])
        self.last_locate_try = 0
        self.last_frame = None
        self.ddragon_version = None
        self.slots_rect = None       # 스펠 칸을 찾을 때의 롤 창 위치·크기
        self.from_cache = False      # 저장해 둔 위치를 쓰는 중인지
        self.cache_rejected = False  # 저장해 둔 위치가 틀린 것 같아서 다시 찾는 중인지
        self.bad_streak = 0          # 저장된 위치에서 아이콘도 쿨타임도 아닌 모습이 이어진 횟수
        self.fg_state = None         # 롤 창이 맨 앞에 있는지 (바뀔 때만 로그에 남겨요)
        self.last_err_log = 0
        self.learned = [False, False]  # 실제 게임 화면에서 배운 '쓸 수 있을 때' 모습이 있는지
        self.calib = [[], []]          # 게임 시작 직후 모은 스펠 칸 모습
        self.fail_saved = False        # 스펠 칸을 못 찾았을 때 화면을 한 번 저장했는지
        self.last_full_search = 0      # 화면 전체를 다 뒤진 마지막 시간
        threading.Thread(target=self._precache_icons, daemon=True).start()

    # 아이콘 준비 ---------------------------------------------------
    def _version(self):
        if not self.ddragon_version:
            req = urllib.request.Request("https://ddragon.leagueoflegends.com/api/versions.json",
                                         headers={"User-Agent": "lol-live-logger"})
            with urllib.request.urlopen(req, timeout=10, context=WEB_CTX) as r:
                self.ddragon_version = json.loads(r.read().decode("utf-8"))[0]
        return self.ddragon_version

    def _icon(self, key):
        os.makedirs(CACHE_DIR, exist_ok=True)
        path = os.path.join(CACHE_DIR, f"{key}.png")
        if not os.path.exists(path):
            url = f"https://ddragon.leagueoflegends.com/cdn/{self._version()}/img/spell/{key}.png"
            req = urllib.request.Request(url, headers={"User-Agent": "lol-live-logger"})
            with urllib.request.urlopen(req, timeout=10, context=WEB_CTX) as r:
                data = r.read()
            with open(path, "wb") as f:
                f.write(data)
        # 경로에 한글이 있어도 읽을 수 있게 직접 읽어서 풀어요.
        return self.cv2.imdecode(self.np.fromfile(path, dtype=self.np.uint8), self.cv2.IMREAD_COLOR)

    def _precache_icons(self):
        """소환사의 협곡에서 쓸 수 있는 소환사 주문 아이콘을 미리 받아 둬요. (게임 중에 받다가 늦어지지 않게)"""
        try:
            url = f"https://ddragon.leagueoflegends.com/cdn/{self._version()}/data/ko_KR/summoner.json"
            req = urllib.request.Request(url, headers={"User-Agent": "lol-live-logger"})
            with urllib.request.urlopen(req, timeout=10, context=WEB_CTX) as r:
                data = json.loads(r.read().decode("utf-8"))["data"]
            for k, v in data.items():
                if "CLASSIC" in v.get("modes", []):
                    try:
                        self._icon(k)
                    except Exception:
                        pass
        except Exception:
            pass

    @staticmethod
    def _inset(img, ratio=0.04):
        """공식 아이콘 가장자리 4%를 잘라요. 게임 화면에서는 가장자리가 칸 테두리에 살짝 가려져서,
        이렇게 하면 실제 모습과 더 잘 맞아요(회복: 0.90 → 0.94)."""
        h = img.shape[0]
        p = int(round(h * ratio))
        return img[p:h - p, p:h - p].copy()

    def _ref_path(self, i, rect):
        return os.path.join(CACHE_DIR, f"ref_{rect[2]}x{rect[3]}_{self.keys[i]}.png")

    def _load_learned(self, rect):
        """예전 게임에서 배워 둔 실제 모습이 있으면 기준으로 써요."""
        for i in range(2):
            if self.learned[i] or not self.keys[i] or not self.slots:
                continue
            path = self._ref_path(i, rect)
            if not os.path.exists(path):
                continue
            try:
                img = self.cv2.imdecode(self.np.fromfile(path, dtype=self.np.uint8), self.cv2.IMREAD_COLOR)
                z = self.slots[i][2]
                if img is None or img.shape[0] != z:
                    continue
                self._set_learned(i, img, save=False)
                log(f"스펠 칸 기준: {self.keys[i]}는 예전 게임에서 배운 모습을 써요.")
            except Exception as e:
                log(f"배운 스펠 모습을 읽지 못했어요({self.keys[i]}): {e}")

    def _set_learned(self, i, img, save=True):
        cv2 = self.cv2
        z = img.shape[0]
        pad = max(2, int(z * 0.15))
        v = float(cv2.cvtColor(img[pad:z - pad, pad:z - pad], cv2.COLOR_BGR2HSV)[:, :, 2].mean())
        self.ref_crop[i], self.ref_tcorr[i], self.learned[i] = img, 1.0, True
        self.ref[i][0] = v
        self.seen[i].clear()
        self.seen[i].append((v, 0))
        if save and self.slots_rect:
            try:
                os.makedirs(CACHE_DIR, exist_ok=True)
                self.save_png(self._ref_path(i, self.slots_rect), img)
                if self.save_debug:
                    os.makedirs(DEBUG_DIR, exist_ok=True)
                    big = cv2.resize(img, (z * 4, z * 4), interpolation=cv2.INTER_NEAREST)
                    self.save_png(os.path.join(DEBUG_DIR, f"spell_ref_{self.keys[i]}.png"), big)
            except Exception as e:
                log(f"배운 스펠 모습 저장 실패: {e}")

    def _calibrate(self, i, img, game_time, v, blue, tcorr, flat):
        """게임 시작 직후(두 스펠 모두 쓸 수 있을 때) 실제 화면의 모습을 배워요.
        공식 아이콘과 그림이 조금 달라도, 이렇게 배운 모습과 비교하면 정확해요."""
        if self.learned[i] or game_time > CALIB_UNTIL:
            return
        if flat or blue >= 0.5 or tcorr < 0.3:
            self.calib[i].clear()  # 쿨타임이거나 가려진 모습이 섞이면 처음부터 다시 모아요
            return
        c = self.calib[i]
        c.append(img)
        if len(c) > 8:
            c.pop(0)
        if len(c) == 8 and all(self._ncc(x, c[-1]) >= 0.9 for x in c[:-1]):
            self._set_learned(i, c[-1])
            c.clear()
            log(f"스펠 칸 기준: {self.keys[i]}의 실제 모습을 배웠어요 (공식 아이콘과 닮은 정도 {tcorr:.2f})")

    def _save_fail_shot(self, frame, m, top):
        """스펠 칸을 못 찾았을 때 화면 아래쪽 가운데를 한 번 저장해요. (나중에 기준을 맞출 때 봐요)"""
        if self.fail_saved or not self.save_debug:
            return
        self.fail_saved = True
        try:
            h, w = frame.shape[:2]
            crop = frame[int(h * 0.55):, int(w * 0.30):int(w * 0.70)]
            os.makedirs(DEBUG_DIR, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.save_png(os.path.join(DEBUG_DIR, f"spell_search_fail_{stamp}.png"), crop)
            log("스펠 칸을 못 찾은 화면을 debug 폴더에 한 장 저장했어요.")
        except Exception as e:
            log(f"화면 저장 실패: {e}")

    def save_png(self, path, img):
        ok, buf = self.cv2.imencode(".png", img)
        if ok:
            with open(path, "wb") as f:
                f.write(buf.tobytes())

    def set_spells(self, keys):
        for i, k in enumerate(keys):
            if k and k != self.keys[i]:
                try:
                    self.templates[i] = self._inset(self._icon(k))
                    if self.keys[i] is not None:
                        log(f"스펠이 {self.keys[i]} → {k}로 바뀌어서 기준을 다시 잡을게요.")
                    self.keys[i] = k
                    self.ref[i] = [0, 0]
                    self.seen[i].clear()
                    self.ref_crop[i] = None
                    self.ref_tcorr[i] = 0.0
                    self.learned[i] = False
                    self.calib[i] = []
                    if self.slots and self.slots_rect:
                        self._load_learned(self.slots_rect)
                except Exception as e:
                    log(f"스펠 아이콘({k})을 받지 못했어요: {e}")

    # 위치 찾기 ------------------------------------------------------
    def _grab(self, left, top, width, height):
        shot = self.sct.grab({"left": left, "top": top, "width": width, "height": height})
        return self.np.asarray(shot)[:, :, :3].copy()  # BGRA → BGR

    def locate(self):
        """화면 아래쪽에서 두 스펠 아이콘을 여러 크기로 찾아요. 게임 시작 직후 한 번 하면 돼요.
        유체화 같은 스펠은 쓰면 같은 그림의 작은 버프 아이콘이 따로 뜨기 때문에,
        '같은 크기로 나란히 붙어 있는 두 아이콘'을 한 쌍으로 찾아요."""
        if any(t is None for t in self.templates):
            return False
        rect = league_window_rect()
        if rect is None:
            log(f"스펠 칸 찾기: 롤 화면이 안 보여서 다음에 다시 찾을게요 (보이는 창: {LAST_BLOCKER['name']})")
            return False
        # 예전에 같은 창 크기에서 찾은 위치가 있으면 그대로 써요.
        # (게임 도중에 켜져서 스펠이 쿨타임이라 아이콘을 못 찾는 경우에도 바로 확인할 수 있어요)
        try:
            with open(SLOT_CACHE, encoding="utf-8") as f:
                cache = json.load(f).get(f"{rect[2]}x{rect[3]}")
        except Exception:
            cache = None
        if cache and not self.cache_rejected:
            self.slots = [(rect[0] + x, rect[1] + y, z) for x, y, z in cache]
            self.slots_rect = rect
            self.from_cache = True
            log(f"스펠 칸 찾기: 저장해 둔 위치를 써요 (창 크기 {rect[2]}x{rect[3]})")
            self._load_learned(rect)
            return True
        cv2, np = self.cv2, self.np
        m = {"left": rect[0], "top": rect[1], "width": rect[2], "height": rect[3]}
        top = m["top"] + int(m["height"] * 0.55)
        frame = self._grab(m["left"], top, m["width"], m["height"] - (top - m["top"]))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # 크기 후보: 예전에 찾은 칸 크기 근처만 먼저 봐요. 전체 크기를 다 뒤지는 건 무거워서 30초에 한 번만 해요.
        try:
            with open(SLOT_CACHE, encoding="utf-8") as f:
                known = {int(e[2]) for v in json.load(f).values() for e in v}
        except Exception:
            known = set()
        now = time.time()
        if known and now - self.last_full_search < 30:
            sizes = [z for z in range(18, 72) if any(abs(z - k) <= 3 for k in known)]
        else:
            sizes = list(range(18, 72))
            self.last_full_search = now
        tcs = list(self.templates)
        tgs = [cv2.cvtColor(t, cv2.COLOR_BGR2GRAY) for t in tcs]
        best = None  # (점수 합, (x1, y1), (x2, y2), 크기, 점수1, 점수2)
        for size in sizes:
            peaks = []
            for tc, tg in zip(tcs, tgs):
                # 흑백(모양)과 컬러(색) 점수의 평균을 써요. 무늬가 잘게 들어간 아이콘(점멸, 탈진, 방어막 등)은
                # 위치가 반 칸만 어긋나도 흑백 점수가 많이 떨어지는데, 컬러를 같이 보면 덜 떨어져요.
                rg = cv2.matchTemplate(gray, cv2.resize(tg, (size, size), interpolation=cv2.INTER_AREA), cv2.TM_CCOEFF_NORMED)
                rc = cv2.matchTemplate(frame, cv2.resize(tc, (size, size), interpolation=cv2.INTER_AREA), cv2.TM_CCOEFF_NORMED)
                res = (rg + rc) / 2
                cand = []
                for _ in range(6):  # 점수가 높은 후보 6곳
                    _, sc, _, loc = cv2.minMaxLoc(res)
                    if sc < 0.45:
                        break
                    cand.append((sc, loc))
                    x0, y0 = max(0, loc[0] - size // 2), max(0, loc[1] - size // 2)
                    res[y0:loc[1] + size // 2 + 1, x0:loc[0] + size // 2 + 1] = -1
                peaks.append(cand)
            for s1, (x1, y1) in peaks[0]:
                for s2, (x2, y2) in peaks[1]:
                    # 두 스펠 칸은 같은 줄에 붙어 있어요. (1920x1080, 칸 26px일 때 33px 간격 = 칸 크기의 1.27배)
                    if abs(y1 - y2) <= max(2, size * 0.1) and size * 1.05 <= abs(x1 - x2) <= size * 1.8:
                        total = s1 + s2
                        if best is None or total > best[0]:
                            best = (total, (x1, y1), (x2, y2), size, s1, s2)
        if not best or best[4] < 0.55 or best[5] < 0.55 or best[0] < 1.25:
            sc = f"{best[4]:.2f}, {best[5]:.2f}" if best else "-"
            log(f"스펠 칸 찾기: 나란히 있는 두 아이콘을 못 찾았어요 (점수 {sc}) / 실패")
            self._save_fail_shot(frame, m, top)
            return False
        _, (x1, y1), (x2, y2), z, s1, s2 = best
        log(f"스펠 칸 찾기: 점수 {s1:.2f}, {s2:.2f} / 크기 {z} / 성공")
        self.slots = [(m["left"] + x1, top + y1, z), (m["left"] + x2, top + y2, z)]
        self.slots_rect = rect
        self.from_cache = False
        self._load_learned(rect)
        # 찾은 순간에는 두 스펠 모두 공식 아이콘과 닮았으니(쓸 수 있는 상태), 이 모습을 기준으로 저장해요.
        for i, (xx, yy) in enumerate(((x1, y1), (x2, y2))):
            img = frame[yy:yy + z, xx:xx + z].copy()
            tc = self._ncc(img, self.templates[i])
            if tc > self.ref_tcorr[i]:
                self.ref_crop[i], self.ref_tcorr[i] = img, tc
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                self.seen[i].append((float(hsv[:, :, 2].mean()), 0))
                self.ref[i][0] = max(self.ref[i][0], float(hsv[:, :, 2].mean()))
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            try:
                with open(SLOT_CACHE, encoding="utf-8") as f:
                    allc = json.load(f)
            except Exception:
                allc = {}
            allc[f"{rect[2]}x{rect[3]}"] = [(x - rect[0], y - rect[1], zz) for x, y, zz in self.slots]
            with open(SLOT_CACHE, "w", encoding="utf-8") as f:
                json.dump(allc, f)
        except Exception as e:
            log(f"스펠 칸 위치 저장 실패: {e}")
        if self.save_debug:
            os.makedirs(DEBUG_DIR, exist_ok=True)
            x0, x9 = min(x1, x2) - 40, max(x1, x2) + z + 40
            y0, y9 = min(y1, y2) - 30, max(y1, y2) + z + 30
            crop = frame[max(0, y0):y9, max(0, x0):x9].copy()
            for (xx, yy) in ((x1, y1), (x2, y2)):
                cv2.rectangle(crop, (xx - max(0, x0) - 1, yy - max(0, y0) - 1),
                              (xx - max(0, x0) + z, yy - max(0, y0) + z), (0, 255, 0), 1)
            self.save_png(os.path.join(DEBUG_DIR, "spell_slots_found.png"), crop)
        return True

    # 상태 판단 ------------------------------------------------------
    def _ncc(self, a, b):
        """두 그림이 얼마나 닮았는지 (-1~1). 밝기가 달라도 모양이 같으면 높게 나와요."""
        np, cv2 = self.np, self.cv2
        a = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float32)
        b = cv2.cvtColor(cv2.resize(b, (a.shape[1], a.shape[0])), cv2.COLOR_BGR2GRAY).astype(np.float32)
        a -= a.mean()
        b -= b.mean()
        den = float(np.sqrt((a * a).sum() * (b * b).sum()))
        return float((a * b).sum() / den) if den > 0 else 0.0

    def _measure(self, img, i):
        cv2 = self.cv2
        z = img.shape[0]
        pad = max(2, int(z * 0.15))
        inner = img[pad:z - pad, pad:z - pad]
        hsv = cv2.cvtColor(inner, cv2.COLOR_BGR2HSV)
        h, s_, v_ = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        v = float(v_.mean())
        flat = float(v_.std()) < 12  # 그림도 숫자도 없이 한 가지 색으로 덮여 있음 (다른 창이 가리는 경우 등)
        # 쿨타임일 때 아이콘 위에 덮이는 파란 판의 비율
        blue = float(((h >= 90) & (h <= 120) & (s_ > 100)).mean())
        tcorr = self._ncc(img, self.templates[i])          # 공식 아이콘과 닮은 정도
        rcorr = self._ncc(img, self.ref_crop[i]) if self.ref_crop[i] is not None else None  # 쓸 수 있을 때 모습과 닮은 정도
        return v, blue, tcorr, rcorr, flat

    def check(self, game_time, after_death=False):
        """두 스펠 칸의 상태를 기록해요.
        'ready'(쓸 수 있음), 'cooldown'(쿨타임),
        'unclear'(화면은 봤지만 판단이 애매함), 'unknown'(화면을 못 봄: 다른 창, 가려짐, 오류 등)
        after_death=True면 죽은 직후 확인용이라 기준값을 바꾸지 않고, (상태, 이미지)를 돌려줘요."""
        point = None
        if self.slots:
            point = (self.slots[0][0] + self.slots[0][2] // 2, self.slots[0][1] + self.slots[0][2] // 2)
        rect = league_window_rect(point)
        if not after_death:
            fg = rect is not None
            if fg != self.fg_state and self.fg_state is not None:
                log("스펠 칸 자리에 롤 화면이 다시 보여요." if fg else
                    f"스펠 칸 자리에 롤 화면이 안 보여요(그 자리에 보이는 창: {LAST_BLOCKER['name']}). "
                    "이동안 스펠은 '화면을 못 봄'으로 남겨요.")
            self.fg_state = fg
        if rect is None:
            # 다른 창을 보고 있어요. 이때는 화면을 보지 않고 '화면을 못 봄'으로 남겨요.
            if after_death:
                return ["unknown", "unknown"], None
            self.history.append((game_time, ["unknown", "unknown"]))
            return None
        if after_death and not self.slots:
            return ["unknown", "unknown"], None
        if self.slots and rect != self.slots_rect:
            log("롤 창 크기나 위치가 바뀌어서 스펠 칸을 다시 찾을게요.")
            self.slots = None
            self.last_locate_try = 0
        if not self.slots:
            if time.time() - self.last_locate_try > 5:
                self.last_locate_try = time.time()
                try:
                    self.locate()
                except Exception as e:
                    log(f"스펠 칸을 찾다 오류가 났어요: {e}")
            return None
        xs = [s[0] for s in self.slots]
        ys = [s[1] for s in self.slots]
        z = self.slots[0][2]
        left, top = min(xs), min(ys)
        try:
            frame = self._grab(left, top, max(xs) - left + z, max(ys) - top + z)
        except Exception as e:
            # 화면 잠금, 관리자 권한 창 등으로 잠깐 화면을 못 읽을 때가 있어요.
            if time.time() - self.last_err_log > 60:
                self.last_err_log = time.time()
                log(f"화면을 잠깐 읽지 못했어요({type(e).__name__}). 계속 시도할게요.")
            if after_death:
                return ["unknown", "unknown"], None
            self.history.append((game_time, ["unknown", "unknown"]))
            return None
        states, crops, looks = [], [], []
        for i, (x, y, zz) in enumerate(self.slots):
            img = frame[y - top:y - top + zz, x - left:x - left + zz].copy()
            crops.append(img)
            v, blue, tcorr, rcorr, flat = self._measure(img, i)
            looks.append(not flat and (tcorr >= 0.3 or blue >= 0.3 or (rcorr is not None and rcorr >= 0.5)))
            if not after_death:
                self._calibrate(i, img, game_time, v, blue, tcorr, flat)
                if self.learned[i]:
                    rcorr = self._ncc(img, self.ref_crop[i])
            # 공식 아이콘과 가장 닮은 순간의 모습을 '쓸 수 있는 상태'의 기준으로 저장해요.
            if (tcorr >= 0.6 or (self.learned[i] and rcorr is not None and rcorr >= 0.85)) and not after_death:
                self.seen[i].append((v, 0))
                vs = sorted(a for a, _ in self.seen[i])
                self.ref[i][0] = vs[min(int(len(vs) * 0.9), len(vs) - 1)]
                if tcorr > self.ref_tcorr[i] and not self.learned[i]:
                    self.ref_crop[i], self.ref_tcorr[i] = img, tcorr
                    rcorr = 1.0
            ref_v = self.ref[i][0]
            if flat:
                states.append("unknown")
                continue
            if self.ref_crop[i] is None or ref_v <= 0:
                # 아직 '쓸 수 있는 모습'을 한 번도 못 봤을 때(게임 도중에 켜졌고 쿨타임인 경우 등)는
                # 공식 아이콘과 비교해서 판단해요.
                if tcorr >= 0.6:
                    states.append("ready")
                elif tcorr < 0.45 and blue >= 0.5:
                    states.append("cooldown")
                else:
                    states.append("unclear")
                continue
            ratio_v = v / ref_v
            # 실제 화면 기준 (2026-11 연습 모드 측정)
            #  - 쓸 수 있음: 평소 모습과 95~100% 닮음. 죽은 뒤에는 밝기가 40% 정도로 어두워지지만 모양은 그대로예요.
            #  - 쿨타임: 파란 판 위에 숫자. 평소 모습과 13~26%만 닮고, 파란 부분이 75~80%예요.
            if rcorr >= 0.7:
                states.append("ready")
            elif rcorr < 0.45 and blue >= 0.5:
                states.append("cooldown")          # 파란 판 + 숫자
            elif rcorr < 0.35 and ratio_v < 0.8:
                states.append("cooldown")          # 다른 방식으로 가려진 쿨타임
            else:
                states.append("unclear")
        if after_death:
            return states, crops
        if self.from_cache:
            # 공식 아이콘과 그림이 조금 달라서 '애매함'이 이어질 수는 있어요(2026-11-07 자야 판).
            # 그래서 두 칸 모두 아이콘으로도, 쿨타임 판으로도 안 보이는 상태가 30초 이어질 때만 다시 찾아요.
            self.bad_streak = self.bad_streak + 1 if all(not lk for lk in looks) else 0
            if self.bad_streak >= 120:
                log("저장해 둔 스펠 칸 위치가 맞지 않는 것 같아서 새로 찾을게요.")
                self.slots, self.from_cache, self.cache_rejected, self.bad_streak = None, False, True, 0
        self.history.append((game_time, states))
        self.last_frame = crops
        return states

    def sample_before(self, t):
        """t초(데스 시간) 바로 전의 마지막 확인 결과를 (시간, 상태)로 돌려줘요."""
        cand = [h for h in self.history if h[0] <= t + 0.05]
        return cand[-1] if cand else None

    def states_around(self, t, seconds):
        return [h for h in self.history if t - seconds <= h[0] <= t]


# ---------------------------------------------------------------- 한 판 기록

class GameSession:
    def __init__(self, data, tracker):
        gd = data.get("gameData", {})
        self.mode = gd.get("gameMode", "")
        self.start_epoch = time.time() - gd.get("gameTime", 0)
        me = find_me(data) or {}
        self.me_names = {me.get("riotId"), me.get("summonerName"), me.get("riotIdGameName")} - {None, ""}
        self.champion = champ_key(me)
        self.tracker = tracker
        self.snapshots = []
        self.recent = deque(maxlen=30)  # (게임 시간, 골드, 체력%) 1초 단위
        self.deaths = []
        self.was_dead = False
        self.last_snapshot_t = -999
        self.last_game_time = 0
        self.last_poll_wall = time.time()
        self.ended = False
        self.debug_saved = 0
        self.post_death = None  # 죽은 직후 스펠 칸 확인 {until, idx, t}
        self.sheet = None       # 데스 한 번의 스펠 칸 모습 (이미지 한 장으로 저장)
        self.last_progress = time.time()
        self.resumed = []       # 강제 종료 뒤 이어서 기록한 때 [{at, lastSaved}]
        log(f"게임 시작 감지: {self.mode} / {self.champion}")
        self._resume(float(gd.get("gameTime", 0)))
        self.update(data)

    def _resume(self, now_t):
        """강제 종료 전에 저장해 둔 같은 판 기록이 있으면 이어 붙여요. 다른 판 기록이면 따로 정리해요."""
        p = read_progress()
        if not p:
            return
        same = (p.get("gameMode") == self.mode and p.get("champion") == self.champion
                and abs(p.get("startEpochMs", 0) / 1000 - self.start_epoch) <= 60)
        if not same:
            save_partial(p, "다른 판이 시작돼서")
            return
        self.start_epoch = p["startEpochMs"] / 1000
        self.deaths = p.get("deaths") or []
        self.snapshots = [x for x in (p.get("snapshots") or []) if x.get("t", 0) <= now_t]
        self.resumed = (p.get("resumed") or []) + [{"at": round(now_t, 1), "lastSaved": p.get("gameLength")}]
        lost = now_t - float(p.get("gameLength") or now_t)
        log(f"강제 종료 전 기록을 이어 붙였어요 (데스 {len(self.deaths)}번, 기록이 빈 시간 약 {int(lost)}초)")

    def save_progress(self):
        """진행 중 기록을 저장해요. 전원이 꺼져도 파일이 깨지지 않게 임시 파일에 쓴 뒤 바꿔 끼워요."""
        self.last_progress = time.time()
        try:
            os.makedirs(GAMES_DIR, exist_ok=True)
            rec = self.to_record()
            rec["savedAt"] = time.time()
            tmp = PROGRESS_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, PROGRESS_PATH)
        except Exception as e:
            log(f"진행 중 기록 저장 실패: {e}")

    def est_game_time(self):
        return self.last_game_time + (time.time() - self.last_poll_wall)

    def update(self, data):
        gd = data.get("gameData", {})
        t = float(gd.get("gameTime", 0))
        self.last_game_time, self.last_poll_wall = t, time.time()
        ap = data.get("activePlayer") or {}
        stats = ap.get("championStats") or {}
        me = find_me(data) or {}
        gold = float(ap.get("currentGold", 0))
        hp, maxhp = float(stats.get("currentHealth", 0)), float(stats.get("maxHealth", 0)) or 1
        hp_pct = round(hp / maxhp * 100)
        dead = bool(me.get("isDead"))

        if self.tracker:
            try:
                ss = me.get("summonerSpells") or {}
                self.tracker.set_spells([spell_key(ss.get("summonerSpellOne")), spell_key(ss.get("summonerSpellTwo"))])
            except Exception as e:
                log(f"스펠 정보 확인 오류: {e}")

        if not dead:
            self.recent.append((t, round(gold), hp_pct))
        if dead and not self.was_dead:
            self.record_death(data, t)
        self.was_dead = dead

        if t - self.last_snapshot_t >= SNAPSHOT_EVERY:
            sc = me.get("scores") or {}
            self.snapshots.append({"t": round(t, 1), "gold": round(gold), "hp": hp_pct, "level": ap.get("level"),
                                   "cs": sc.get("creepScore"), "k": sc.get("kills"), "d": sc.get("deaths"),
                                   "a": sc.get("assists"), "dead": dead})
            self.last_snapshot_t = t

        for ev in (data.get("events") or {}).get("Events", []):
            if ev.get("EventName") == "GameEnd":
                self.ended = True
        if time.time() - self.last_progress >= PROGRESS_EVERY:
            self.save_progress()

    def record_death(self, data, t_seen):
        # 정확한 데스 시간은 게임 이벤트에서 찾고, 없으면 확인한 시점을 써요.
        t_death = t_seen
        for ev in reversed((data.get("events") or {}).get("Events", [])):
            if ev.get("EventName") == "ChampionKill" and ev.get("VictimName") in self.me_names:
                t_death = float(ev.get("EventTime", t_seen))
                break
        if any(abs(d.get("t", -99) - t_death) < 3 for d in self.deaths):
            return  # 이어 붙인 기록에 이미 있는 데스예요
        alive = [r for r in self.recent if r[0] <= t_death]
        last = alive[-1] if alive else (t_death, None, None)
        hp_flow = [{"t": round(r[0], 1), "hp": r[2]} for r in alive if r[0] >= t_death - 10]
        entry = {"t": round(t_death, 1), "gold": last[1], "hpFlow": hp_flow, "spells": None}

        tr = self.tracker
        if tr and not tr.slots and any(tr.keys):
            # 스펠 칸을 아직 못 찾은 상태라 화면을 못 본 것과 같아요.
            entry["spells"] = [{"key": k, "state": "unknown", "age": None, "verdict": "not_visible"} for k in tr.keys]
        if tr and tr.slots:
            last = tr.sample_before(t_death)
            age = round(t_death - last[0], 2) if last else None
            window = tr.states_around(t_death + 0.05, 10)
            spells = []
            for i, key in enumerate(tr.keys):
                state = last[1][i] if last else "unknown"
                was_ready = any(h[1][i] == "ready" for h in window)
                if state == "unknown":
                    verdict = "not_visible"    # 화면을 못 봄 (다른 창, 가려짐, 오류)
                elif state == "unclear":
                    verdict = "uncertain"      # 화면은 봤지만 판단이 애매함
                elif state == "ready":
                    # 마지막으로 본 게 너무 오래전이면, 그 사이에 썼을 수도 있어서 단정하지 않아요.
                    verdict = "held" if age is not None and age <= STALE_READY else "uncertain"
                elif was_ready:
                    verdict = "used_before"    # 죽기 직전에 사용
                else:
                    verdict = "already_down"   # 이미 쿨타임
                spells.append({"key": key, "state": state, "age": age, "verdict": verdict})
            entry["spells"] = spells
            self.sheet = {"pre": tr.last_frame, "pre_states": [sp["state"] for sp in spells], "after": []}
        self.deaths.append(entry)
        if tr and tr.slots:
            entry["afterDeath"] = []
            self.post_death = {"until": time.time() + AFTER_DEATH_SECONDS, "idx": len(self.deaths) - 1,
                               "t": t_death, "saved": 0}
        log(f"데스 기록: {int(t_death // 60)}:{int(t_death % 60):02d} / 골드 {entry['gold']} / 스펠 {entry['spells']}")
        self.save_progress()

    def watch_after_death(self):
        """죽은 직후 스펠 칸을 확인해요. 죽은 뒤에는 스펠을 쓸 수 없으니까,
        이때 쓸 수 있는 상태면 '정말 들고 죽음', 쿨타임이면 '죽기 직전에 사용(또는 이미 쿨타임)'이에요."""
        pd = self.post_death
        if not pd or not self.tracker:
            return
        if time.time() > pd["until"]:
            self.post_death = None
            self.finalize_death(pd["idx"])
            return
        tr = self.tracker
        states, crops = tr.check(self.est_game_time(), after_death=True)
        dt = round(self.est_game_time() - pd["t"], 2)
        self.deaths[pd["idx"]].setdefault("afterDeath", []).append({"dt": dt, "states": states})
        if crops and getattr(self, "sheet", None) is not None and len(self.sheet["after"]) < 8:
            self.sheet["after"].append((dt, crops, states))

    def finalize_death(self, idx):
        entry = self.deaths[idx]
        after = [a for a in entry.get("afterDeath", []) if a["dt"] <= 1.6]
        for i, sp in enumerate(entry.get("spells") or []):
            # 연습 모드처럼 죽은 뒤 쿨타임이 초기화되는 경우가 있어서, 죽은 직후 가장 이른 확인만 써요.
            first = next((a["states"][i] for a in after if a["states"][i] in ("ready", "cooldown")), None)
            sp["afterDeath"] = first
            v = sp["verdict"]
            if first == "cooldown" and v == "held":
                sp["verdict"] = "used_before"      # 마지막 확인 뒤 아주 짧은 틈에 사용
            elif first == "ready" and v in ("uncertain", "not_visible"):
                sp["verdict"] = "held"             # 죽은 뒤에도 그대로 있으니 들고 죽음이 맞아요
            elif first == "cooldown" and v == "uncertain" and sp.get("state") == "ready":
                sp["verdict"] = "used_before"
        seen = [a["states"] for a in entry.get("afterDeath", [])]
        if seen and all(st == ["unknown", "unknown"] for st in seen):
            log(f"죽은 직후 스펠 칸 자리에 롤 화면이 안 보였어요 (그 자리에 보인 창: {LAST_BLOCKER['name']})")
        log(f"죽은 직후 확인까지 반영한 판정: {[(sp['key'], sp['verdict']) for sp in entry.get('spells') or []]}"
            f" / 죽은 직후 본 모습 {len(seen)}번: {seen[:3]}")
        self.save_sheet(entry)

    def save_sheet(self, entry):
        """한 번 죽을 때의 스펠 칸 모습을 이미지 한 장으로 모아서 저장해요. (위: 스펠1, 아래: 스펠2)"""
        tr, sh = self.tracker, getattr(self, "sheet", None)
        self.sheet = None
        if not (tr and tr.save_debug and sh and sh.get("pre") and self.debug_saved < 30):
            return
        try:
            cv2, np = tr.cv2, tr.np
            cols = [("pre", sh["pre"], sh["pre_states"])] + [(f"+{dt:.1f}", c, st) for dt, c, st in sh["after"]]
            z = sh["pre"][0].shape[0]
            cell = z * 2
            W, H = cell * len(cols), cell * 2 + 34
            img = np.full((H, W, 3), 255, np.uint8)
            mark = {"ready": "R", "cooldown": "C", "unclear": "?", "unknown": "X"}
            for c, (label, crops, states) in enumerate(cols):
                cv2.putText(img, label, (c * cell + 4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
                for r in range(2):
                    big = cv2.resize(crops[r], (cell - 8, cell - 8), interpolation=cv2.INTER_NEAREST)
                    y0, x0 = 20 + r * cell, c * cell + 4
                    img[y0:y0 + cell - 8, x0:x0 + cell - 8] = big
                    cv2.putText(img, mark.get(states[r], "?"), (x0 + 2, y0 + cell - 12),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            os.makedirs(DEBUG_DIR, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tr.save_png(os.path.join(DEBUG_DIR, f"death_{stamp}_{int(entry['t'])}s.png"), img)
            self.debug_saved += 1
        except Exception as e:
            log(f"데스 이미지 저장 실패: {e}")

    def to_record(self):
        return {
            "version": 2,
            "startEpochMs": int(self.start_epoch * 1000),
            "gameMode": self.mode,
            "champion": self.champion,
            "gameLength": round(self.last_game_time, 1),
            "spellCheck": bool(self.tracker and self.tracker.slots),
            "spellKeys": self.tracker.keys if self.tracker else None,
            "deaths": self.deaths,
            "snapshots": self.snapshots,
            "resumed": self.resumed,
        }


# ---------------------------------------------------------------- 깃허브

def gh_request(method, path, token, body=None):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "lol-live-logger",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20, context=WEB_CTX) as r:
        return r.status


def upload_pending(cfg):
    token, repo = cfg["github_token"].strip(), cfg["repo"].strip()
    if not token or "/" not in repo or repo.startswith("깃허브아이디"):
        log("config.json에 github_token과 repo를 넣으면 깃허브에 자동으로 올려요. 지금은 내 컴퓨터에만 저장할게요.")
        return
    os.makedirs(PENDING_DIR, exist_ok=True)
    uploaded = False
    for name in sorted(os.listdir(PENDING_DIR)):
        path = os.path.join(PENDING_DIR, name)
        with open(path, "rb") as f:
            content = base64.b64encode(f.read()).decode("ascii")
        try:
            gh_request("PUT", f"/repos/{repo}/contents/live/{name}", token,
                       {"message": f"게임 중 기록 추가 ({name})", "content": content})
            os.remove(path)
            uploaded = True
            log(f"깃허브에 올렸어요: live/{name}")
        except urllib.error.HTTPError as e:
            if e.code == 422:  # 이미 같은 이름의 파일이 있어요.
                os.remove(path)
                continue
            log(f"깃허브 업로드 실패({e.code}). 다음에 다시 시도할게요. 토큰 권한을 확인해 주세요.")
            return
        except Exception as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                log(f"깃허브 업로드 실패({e}). 인증서를 확인하지 못했어요. install.bat을 다시 실행해 주세요. 다음에 다시 시도할게요.")
            else:
                log(f"깃허브 업로드 실패({e}). 인터넷 연결을 확인해 주세요. 다음에 다시 시도할게요.")
            return
    if uploaded and cfg["auto_update"]:
        try:
            gh_request("POST", f"/repos/{repo}/actions/workflows/update.yml/dispatches", token,
                       {"ref": "main", "inputs": {"wait": "true"}})
            log("'경기 기록 갱신'을 실행했어요. 2~5분 뒤에 페이지에 올라와요.")
        except Exception as e:
            log(f"갱신 실행 실패({e}). 깃허브 Actions에서 직접 눌러 주세요.")


def read_progress():
    try:
        with open(PROGRESS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_partial(p, why):
    """끝까지 기록하지 못한 판(강제 종료 뒤 다시 이어지지 않음)을 '중간까지만 기록'으로 남겨요."""
    try:
        os.remove(PROGRESS_PATH)
    except OSError:
        pass
    p.pop("savedAt", None)
    p["partial"] = True
    stamp = datetime.fromtimestamp(p.get("startEpochMs", 0) / 1000).strftime("%Y%m%d_%H%M%S")
    name = f"{stamp}_{p.get('champion')}.json"
    os.makedirs(GAMES_DIR, exist_ok=True)
    with open(os.path.join(GAMES_DIR, name), "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=1)
    log(f"{why} 강제 종료 전 기록({name})을 중간까지만 기록된 판으로 정리했어요 (데스 {len(p.get('deaths') or [])}번)")
    if p.get("gameMode") == "CLASSIC" and float(p.get("gameLength") or 0) >= 300:
        os.makedirs(PENDING_DIR, exist_ok=True)
        with open(os.path.join(PENDING_DIR, name), "w", encoding="utf-8") as f:
            json.dump(p, f, ensure_ascii=False)


def prune(folder, keep, prefix="", suffix=""):
    """폴더에서 오래된 파일을 지워서 최근 keep개만 남겨요."""
    try:
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.startswith(prefix) and f.endswith(suffix)]
        files.sort(key=os.path.getmtime, reverse=True)
        for f in files[keep:]:
            os.remove(f)
    except Exception:
        pass


def finish(session, cfg):
    if session.post_death:
        session.finalize_death(session.post_death["idx"])
        session.post_death = None
    rec = session.to_record()
    stamp = datetime.fromtimestamp(session.start_epoch).strftime("%Y%m%d_%H%M%S")
    name = f"{stamp}_{rec['champion']}.json"
    os.makedirs(GAMES_DIR, exist_ok=True)
    with open(os.path.join(GAMES_DIR, name), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    try:
        os.remove(PROGRESS_PATH)
    except OSError:
        pass
    prune(DEBUG_DIR, KEEP_DEBUG_IMAGES, prefix="death_", suffix=".png")
    prune(DEBUG_DIR, 0, prefix="afterdeath_", suffix=".png")  # 예전 방식으로 저장된 사진은 정리해요
    prune(GAMES_DIR, KEEP_GAME_FILES, suffix=".json")
    log(f"게임 종료: {rec['gameMode']} / {int(rec['gameLength'] // 60)}분 / 데스 {len(rec['deaths'])}번 기록")
    if rec["gameMode"] == "CLASSIC" and rec["gameLength"] >= 300:
        os.makedirs(PENDING_DIR, exist_ok=True)
        with open(os.path.join(PENDING_DIR, name), "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)
        upload_pending(cfg)
    else:
        log("소환사의 협곡 일반 게임이 아니거나 5분 미만이라 깃허브에는 올리지 않을게요.")


# ---------------------------------------------------------------- 실행

def main():
    lock = single_instance()  # noqa: F841
    _setup_dpi()
    cfg = load_config()
    log("기록 프로그램을 시작했어요. 롤 게임이 시작되면 자동으로 기록해요.")
    try:
        import certifi  # noqa: F401
    except Exception:
        log("인증서 목록(certifi)이 없어서 깃허브 업로드가 실패할 수 있어요. install.bat을 다시 실행해 주세요.")
    old = read_progress()
    if old and time.time() - float(old.get("savedAt") or 0) > 2 * 3600:
        save_partial(old, "2시간 넘게 이어지지 않아서")

    tracker = None
    tracker_ok = False
    if cfg["spell_check"]:
        try:
            tracker_ok = True
            SpellTracker(cfg)  # 필요한 프로그램이 설치됐는지 확인
        except Exception as e:
            tracker_ok = False
            log(f"스펠 확인 기능을 쓸 수 없어요({e}). 'install.bat'을 다시 실행해 주세요. 골드·체력 기록은 계속해요.")
    upload_pending(cfg)

    session = None
    fails = 0
    last_poll = 0
    spell_gap = 1.0 / max(0.5, float(cfg["spell_checks_per_second"]))
    last_spell = 0
    while True:
        try:
            now = time.time()
            if now - last_poll >= (POLL_EVERY if session else IDLE_WAIT):
                last_poll = now
                data = poll_live()
                ok = bool(data and (data.get("activePlayer") or {}).get("championStats"))
                if ok:
                    fails = 0
                    if session is None:
                        if cfg["spell_check"] and tracker_ok:
                            try:
                                tracker = SpellTracker(cfg)
                            except Exception as e:
                                tracker = None
                                log(f"스펠 확인 기능 시작 실패: {e}")
                        session = GameSession(data, tracker)
                    else:
                        session.update(data)
                elif session is not None:
                    fails += 1
                    if session.ended or fails >= 5:
                        finish(session, cfg)
                        session, tracker = None, None
            if session and tracker and session.post_death and now - last_spell >= AFTER_DEATH_GAP:
                last_spell = now
                session.watch_after_death()
            elif session and tracker and not session.was_dead and now - last_spell >= spell_gap:
                last_spell = now
                tracker.check(session.est_game_time())
        except Exception:
            log("오류가 났지만 계속 실행할게요:\n" + traceback.format_exc())
            time.sleep(2)
        time.sleep(STEP)


if __name__ == "__main__":
    main()
