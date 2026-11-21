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
import math
import os
import socket
import ssl
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import zlib
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
MM_CACHE = os.path.join(HERE, "cache", "minimap.json")  # 한 번 맞춘 미니맵 아이콘 크기 (롤 창 크기별)

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
    "minimap_check": True,
    "minimap_checks_per_second": 1,
    "minimap_fight_checks_per_second": 1,   # 11-22부터 쓰지 않아요(겹칠 때도 1초에 1번). 아래 MM_FIGHT_FAST 참고
    "minimap_side": "right",
}

STEP = 0.1            # 기본 반복 간격(초). 이 간격마다 할 일이 있는지만 확인해요
POLL_EVERY = 1.0      # 게임 정보 확인 간격(초)
SNAPSHOT_EVERY = 5.0  # 흐름 기록 간격(초)
SPELL_BLUE_MIN = 0.15  # 스펠 칸에 쿨타임 파란 판이 이만큼만 남아 있어도(평소 모습과 안 닮았으면) 쿨타임으로 봐요
SPELL_READY_AFTER_CD = 0.85  # 쿨타임이던 칸은 평소 모습과 이만큼 닮아야 '쓸 수 있음'으로 바꿔요
SPELL_DIGIT_MIN = 0.03       # 쿨타임이던 칸에 흰 숫자가 이만큼 남아 있으면 아직 쿨타임으로 봐요
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
    if not raw:
        return player.get("championName", "")
    # 일부 챔피언은 'Character_Seraphine_Name'처럼 모양이 달라요(2026-11-16 세라핀이 'Name'으로 읽힘).
    parts = [x for x in raw.split("_") if x and x.lower() not in ("game", "character", "displayname", "name")]
    return parts[-1] if parts else raw.rsplit("_", 1)[-1]


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
        self.last_def = [None, None]     # 칸마다 마지막으로 확실했던 상태 ("ready" / "cooldown")
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
                    self.last_def[i] = None
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

    def _digit(self, img, i):
        """쿨타임 숫자(흰 글자)가 얼마나 있는지. 평소 모습과 밝기를 맞춘 뒤, 평소보다 훨씬 밝은 점의 비율이에요.
        죽어서 화면이 어두워져도 숫자는 주변보다 밝아서 잡혀요."""
        if self.ref_crop[i] is None:
            return 0.0
        cv2, np = self.cv2, self.np
        z = img.shape[0]
        pad = max(2, int(z * 0.15))
        a = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)[pad:z - pad, pad:z - pad]
        b = cv2.cvtColor(cv2.resize(self.ref_crop[i], (z, z)), cv2.COLOR_BGR2GRAY).astype(np.float32)[pad:z - pad, pad:z - pad]
        k = float(np.median(b)) / max(1.0, float(np.median(a)))
        return float(((a * k - b) > 70).mean())

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
                elif tcorr < 0.45 and blue >= SPELL_BLUE_MIN:
                    states.append("cooldown")
                else:
                    states.append("unclear")
                continue
            ratio_v = v / ref_v
            # 실제 화면 기준 (2026-11 연습 모드 측정)
            #  - 쓸 수 있음: 평소 모습과 95~100% 닮음. 죽은 뒤에는 밝기가 40% 정도로 어두워지지만 모양은 그대로예요.
            #  - 쿨타임: 파란 판 위에 숫자. 평소 모습과 13~26%만 닮고, 파란 부분이 75~80%예요.
            #  - 쿨타임이 줄어들수록 파란 판이 시계 방향으로 걷혀요. 180초 중 42초 남았을 때 파란 부분은 30%뿐이었어요
            #    (2026-11-16 자야 판, 이때 '애매함'으로 남았던 걸 고쳤어요).
            if rcorr >= 0.7:
                st = "ready"
            elif rcorr < 0.45 and blue >= SPELL_BLUE_MIN:
                st = "cooldown"                    # 파란 판(일부만 남아도) + 숫자
            elif rcorr < 0.35 and ratio_v < 0.8:
                st = "cooldown"                    # 다른 방식으로 가려진 쿨타임
            else:
                st = "unclear"
            # 쿨타임이 거의 끝나면 파란 판이 다 걷히고 숫자만 남아서 평소 모습과 꽤 닮아 보여요.
            # 바로 전까지 쿨타임이었다면, 숫자 없는 깨끗한 모습이 될 때까지는 쿨타임으로 봐요.
            if self.last_def[i] == "cooldown" and st != "cooldown" and \
                    (rcorr < SPELL_READY_AFTER_CD or self._digit(img, i) >= SPELL_DIGIT_MIN):
                st = "cooldown"
            states.append(st)
        if after_death:
            return states, crops
        if self.from_cache:
            # 공식 아이콘과 그림이 조금 달라서 '애매함'이 이어질 수는 있어요(2026-11-07 자야 판).
            # 그래서 두 칸 모두 아이콘으로도, 쿨타임 판으로도 안 보이는 상태가 30초 이어질 때만 다시 찾아요.
            self.bad_streak = self.bad_streak + 1 if all(not lk for lk in looks) else 0
            if self.bad_streak >= 120:
                log("저장해 둔 스펠 칸 위치가 맞지 않는 것 같아서 새로 찾을게요.")
                self.slots, self.from_cache, self.cache_rejected, self.bad_streak = None, False, True, 0
        for i, st in enumerate(states):
            if st in ("ready", "cooldown"):
                self.last_def[i] = st
        self.history.append((game_time, states))
        self.last_frame = crops
        return states

    def sample_before(self, t):
        """t초(데스 시간) 바로 전의 마지막 확인 결과를 (시간, 상태)로 돌려줘요."""
        cand = [h for h in self.history if h[0] <= t + 0.05]
        return cand[-1] if cand else None

    def states_around(self, t, seconds):
        return [h for h in self.history if t - seconds <= h[0] <= t]


# ---------------------------------------------------------------- 미니맵 읽기

MM_CALIB_FROM = 60.0        # 이 시간(초) 뒤부터 아이콘 크기를 맞춰요. 게임 시작 때는 우리 팀이 우물에 겹쳐 있어서요
MM_CALIB_EVERY = 15.0       # 크기 맞추기를 다시 해 보는 간격(초)
MM_CALIB_ROUNDS = 3         # 이만큼 모아서 가장 잘 맞는 크기를 골라요
MM_SIZES = list(range(8, 34, 2))  # 아이콘 안쪽 그림 크기 후보(px)
MM_KEEP = 40                # 이 점수(0~100) 이상인 후보만 기록해요. 진짜로 보였는지는 게임 뒤 analyze.py가 정해요
MM_SMALL = 96               # 안개(시야) 비교용으로 줄인 미니맵 크기(px)
LOADING_WAIT = 5            # 게임 시간이 이만큼(초) 지난 뒤부터 화면을 읽어요(로딩 화면 건너뛰기)
MM_BOX_ROUNDS = 5           # 미니맵 테두리를 찾을 때 모으는 화면 수
MM_BOX_TRIES = 3            # 테두리 찾기를 이만큼 해 보고 안 되면 영역 전체에서 찾아요
MM_BOX_PAD = 6              # 찾은 테두리 바깥으로 남기는 여유(px)
MM_CROP = 0.6               # 아이콘 크기를 맞출 때는 챔피언 그림 가운데 60%만 써요(테두리 색을 피하려고)
# --- 테두리 원으로 찾기 (2026-11-16) ---
# 미니맵의 챔피언 아이콘에는 1px짜리 색 테두리가 있어요(상대 팀 빨강, 우리 팀 파랑). 이 원을 먼저 찾고,
# 그 안의 그림이 누구인지는 "다른 아이콘에 가려지지 않은 부분"만 비교해서 정해요. 싸울 때 겹친 아이콘을 찾으려고 넣었어요.
MM_RING_MIN = 0.30          # 원 둘레 중 이만큼 이상 테두리 색이면 아이콘 후보로 봐요
MM_RING_UNKNOWN = 0.50      # 누구인지 못 정했어도 테두리가 이만큼 뚜렷하면 "이름 모르는 아이콘"으로 기록해요
MM_ID_FULL = 0.68           # 안 가려진 아이콘이 이 점수 이상 닮아야 그 챔피언으로 봐요
MM_ID_PART = 0.55           # 가려진 아이콘의 기준(보이는 부분만 비교)
MM_ID_MARGIN = 0.08         # 가려진 아이콘은 두 번째로 닮은 챔피언보다 이만큼 더 닮아야 해요
MM_ID_MINVIS = 0.25         # 그림이 이만큼도 안 보이면 누구인지 정하지 않아요
MM_PLAIN = 0.80             # 테두리 없이 그림만으로 찾았을 때의 기준(테두리 색을 못 읽는 화면 대비)
# --- 바로 전 위치로 이어 붙이기 (2026-11-16, 사용자 제안) ---
# 아이콘이 늘 겹쳐 있지는 않아요. 조금 전에 따로 보였던 챔피언이 그 근처의 "누구인지 못 정한 원"이 됐다면 같은 챔피언으로 봐요.
MM_TRACK_SEC = 3.0          # 이 시간(초) 안에 보였던 위치만 이어 붙여요
MM_TRACK_SPEED = 0.8        # 1초에 아이콘 지름의 이만큼까지 움직였다고 봐요(점멸·돌진 여유 포함)
MM_TRACK_MINSCORE = 0.30    # 보이는 부분이 그 챔피언과 이만큼도 안 닮았으면 이어 붙이지 않아요
# 이어 붙인 자리는 "추정"이에요. 점수를 55로 적어서 analyze.py의 "보였다" 기준(60)에 들어가지 않게 해요.
# 추정한 자리를 다시 다음 추정의 출발점으로 쓰지 않아요(추정이 꼬리를 물고 이어지지 않게).
MM_TRACK_TAG = 55
MM_FIGHT_FAST = False       # True로 바꾸면 예전처럼 겹칠 때 config의 minimap_fight_checks_per_second로 더 자주 읽어요
MM_FAST_SEC = 10.0          # 아이콘이 겹친 걸 본 뒤 이 시간(초) 동안 더 자주 읽어요
MM_RAW_EVERY = 180.0        # 확인용으로 아무 표시도 없는 미니맵 그림을 이 간격(초)으로 저장해요


# --- 미니맵용 원형 아이콘 (2026-11-16) ---
# Data Dragon의 네모 초상화는 미니맵 그림과 자른 범위가 달라서 잘 안 맞는 챔피언이 있었어요(비에고 0.55, 요네 0.77).
# 게임 파일에 든 미니맵용 원형 아이콘(CommunityDragon이 공개)으로 바꾸면 같은 화면에서 0.88, 0.93이 나와요.
# 처음 한 번 모든 챔피언 것을 cache/에 받아 두고, 그 뒤로는 저장된 파일만 써요.
MM_ICON_BASE = "https://raw.communitydragon.org/latest/game/assets/characters/"
# 파일 이름이 챔피언 이름과 다른 경우(옛 내부 이름)
MM_ICON_ODD = {"Blitzcrank": "steamgolem_circle.png", "Anivia": "cryophoenix_circle.png",
               "Orianna": "oriana_circle.png", "Chogath": "greenterror_circle.png",
               "XinZhao": "xinzhaorework_circle_0.png", "Zilean": "chronokeeper_circle.png",
               "Rammus": "armordillo_circle.png", "Shaco": "jester_circle.png"}
MM_ICON_DONE = os.path.join(CACHE_DIR, "mm_icons_done.json")


def _http_get(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "lol-live-logger"})
    with urllib.request.urlopen(req, timeout=timeout, context=WEB_CTX) as r:
        return r.read()


def _ddragon_version():
    return json.loads(_http_get("https://ddragon.leagueoflegends.com/api/versions.json").decode("utf-8"))[0]


def mm_icon_path(key):
    return os.path.join(CACHE_DIR, f"mm_{key}.png")


def fetch_mm_icon(key):
    """챔피언 한 명의 원형 아이콘을 받아서 cache/에 저장해요. 못 받으면 오류를 내요."""
    c = key.lower()
    names = [MM_ICON_ODD[key]] if key in MM_ICON_ODD else [f"{c}_circle.png", f"{c}_circle_0.png"]
    err = None
    for name in names:
        try:
            data = _http_get(f"{MM_ICON_BASE}{c}/hud/{name}")
            if data[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("그림 파일이 아니에요")
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(mm_icon_path(key), "wb") as f:
                f.write(data)
            return
        except Exception as e:
            err = e
    raise err


def prefetch_mm_icons():
    """모든 챔피언의 원형 아이콘을 한 번만 받아 둬요. 게임 기록과 따로 뒤에서 돌아요."""
    try:
        if os.path.exists(MM_ICON_DONE):
            return
        ver = _ddragon_version()
        keys = sorted(json.loads(_http_get(
            f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/champion.json", 20).decode("utf-8"))["data"])
        got, failed = 0, []
        for k in keys:
            if os.path.exists(mm_icon_path(k)):
                got += 1
                continue
            try:
                fetch_mm_icon(k)
                got += 1
            except Exception:
                failed.append(k)
            time.sleep(0.05)
        log(f"미니맵: 원형 아이콘 {got}/{len(keys)}개를 받아 뒀어요."
            + (f" 못 받은 챔피언: {', '.join(failed[:10])}" if failed else ""))
        if len(failed) <= 5:   # 거의 다 받았을 때만 끝난 걸로 적어요. 남은 건 그 챔피언이 나온 판에 다시 받아요.
            with open(MM_ICON_DONE, "w", encoding="utf-8") as f:
                json.dump({"version": ver, "count": got, "failed": failed}, f, ensure_ascii=False)
    except Exception as e:
        log(f"미니맵: 원형 아이콘 미리 받기를 못 했어요({e}). 다음에 켤 때 다시 해 볼게요.")



class MinimapTracker:
    """미니맵에서 10명의 챔피언 아이콘을 찾아 위치와 점수를 기록해요. 미니맵에는 우리 팀이 실제로 본 것만 나와요.
    미니맵의 정확한 위치와 크기는 몰라도 돼요. 화면 오른쪽 아래를 넉넉히 읽고,
    게임이 끝난 뒤 analyze.py가 Riot의 1분 단위 위치 기록과 맞춰서 맵 좌표로 바꿔요.
    게임 화면에는 아무것도 띄우지 않아요."""

    def __init__(self, cfg, grab=None, icon_loader=None):
        self.cv2 = __import__("cv2")
        self.np = __import__("numpy")
        if grab is None:
            import mss
            self.sct = mss.mss()
        self._grab_fn = grab
        self._icon_loader = icon_loader
        self.side = cfg.get("minimap_side", "right")
        self.save_debug = cfg.get("save_debug_images", False)
        self.players = []        # [{"key", "ally", "me"}]
        self.templates = {}      # 번호 → 아이콘 가운데 부분(원래 크기)
        self.icons = {}          # 번호 → 아이콘 전체(원래 크기)
        self.S = None            # 미니맵 아이콘 전체 지름(px). 맞춘 크기 / 0.6
        self.stat = {"ring": 0, "plain": 0, "track": 0, "unknown": 0}   # 어떤 방법으로 찾았는지(로그용)
        self.last_pos = {}       # 번호 → (게임 시간, x, y) 마지막으로 찾은 자리(미니맵 그림 기준)
        self.dead = set()        # 지금 죽어 있는 선수 번호(죽으면 아이콘이 사라져요)
        self.fast_until = -1.0   # 이 게임 시간까지는 더 자주 읽어요(아이콘이 겹쳤을 때)
        self.last_raw = -999
        self.scaled = {}         # 번호 → 맞춘 크기의 아이콘
        self.size = None         # 맞춘 아이콘 크기(px)
        self.size_from_cache = False
        self.verify_left = 0     # 저장해 둔 크기가 맞는지 확인할 남은 횟수
        self.calib_sum = {}      # 크기 → 점수 합
        self.calib_rounds = 0
        self.calib_tries = 0
        self.last_calib = -999
        self.calib_score = None
        self.region = None       # (left, top, side) 화면 기준
        self.box = None          # 영역 안에서 미니맵이 차지하는 정사각형 한 변(px). 모서리에 붙어 있어요. 못 찾으면 None
        self.box_sum, self.box_rounds, self.box_tries = None, 0, 0
        self.win = None          # 롤 창 크기 (w, h)
        self.frames = []         # [게임 시간, [[번호, x, y, 점수], ...]]  x, y는 읽은 영역 안의 위치(px)
        self.recent = deque(maxlen=15)  # (게임 시간, 줄인 회색 미니맵)
        self.ref = None          # 칸마다 지금까지 가장 밝았던 값 (시야가 있을 때의 밝기)
        self.last_full = None    # (게임 시간, 영역 그림, 찾은 것)
        self.ms = deque(maxlen=300)
        self.last_ms_log = time.time()
        self.fail_saved = False
        self.hidden_logged = False

    # 준비 -----------------------------------------------------------
    def set_players(self, data):
        if self.players:
            live = [p for p in data.get("allPlayers", []) if champ_key(p)]
            if len(live) == len(self.players):
                self.dead = {k for k, p in enumerate(live) if p.get("isDead")}
            return
        me = find_me(data) or {}
        my_team = me.get("team")
        ps = []
        for p in data.get("allPlayers", []):
            key = champ_key(p)
            if key:
                ps.append({"key": key, "ally": p.get("team") == my_team, "me": p is me})
        if not ps:
            return
        # 연습 모드에 혼자 있어도(1명) 내 아이콘으로 크기를 맞춰 볼 수 있게 해요.
        self.players = ps
        threading.Thread(target=self._load_templates, daemon=True).start()

    def _champ_icon(self, key):
        """미니맵에 실제로 쓰이는 원형 아이콘을 먼저 쓰고, 없으면 예전처럼 네모 초상화를 써요."""
        if self._icon_loader:
            return self._icon_loader(key)
        cv2, np = self.cv2, self.np
        path = mm_icon_path(key)
        if not os.path.exists(path):
            try:
                fetch_mm_icon(key)
            except Exception as e:
                log(f"미니맵: {key} 원형 아이콘을 받지 못해서 네모 초상화를 써요({e}).")
        if os.path.exists(path):
            img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            if img is not None:
                if img.ndim == 3 and img.shape[2] == 4:  # 투명한 바깥은 검정으로
                    a = img[..., 3:4].astype(np.float32) / 255.0
                    img = (img[..., :3].astype(np.float32) * a).astype(np.uint8)
                elif img.ndim == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                return img
        path = os.path.join(CACHE_DIR, f"champ_{key}.png")
        if not os.path.exists(path):
            data = _http_get(f"https://ddragon.leagueoflegends.com/cdn/{_ddragon_version()}/img/champion/{key}.png")
            with open(path, "wb") as f:
                f.write(data)
        return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)

    def _load_templates(self):
        for i, p in enumerate(self.players):
            try:
                img = self._champ_icon(p["key"])
                h = img.shape[0]
                c = int(round(h * (1 - MM_CROP) / 2))
                self.templates[i] = img[c:h - c, c:h - c].copy()
                self.icons[i] = img
            except Exception as e:
                log(f"미니맵: {p['key']} 아이콘을 받지 못했어요({e}). 이 챔피언은 미니맵에서 찾지 않아요.")
        log(f"미니맵: 챔피언 아이콘 {len(self.templates)}/{len(self.players)}개 준비")

    def _scale_all(self, size):
        cv2 = self.cv2
        self.scaled = {i: cv2.resize(t, (size, size), interpolation=cv2.INTER_AREA) for i, t in self.templates.items()}
        self.scaled_g = {i: cv2.cvtColor(t, cv2.COLOR_BGR2GRAY) for i, t in self.scaled.items()}
        self._prep_rings(size)

    def _prep_rings(self, size):
        """테두리 원 찾기에 쓰는 것들을 아이콘 크기에 맞춰 준비해요."""
        cv2, np = self.cv2, self.np
        S = int(round(size / MM_CROP))
        R = S / 2.0
        yy, xx = np.mgrid[:S, :S]
        c = (S - 1) / 2.0
        self.S, self.R, self.gy, self.gx = S, R, yy, xx
        self.disc = (((xx - c) ** 2 + (yy - c) ** 2) <= (S * 0.44) ** 2).astype(np.float32)  # 테두리 안쪽 그림
        self.full = {i: cv2.resize(t, (S, S), interpolation=cv2.INTER_AREA).astype(np.float32)
                     for i, t in self.icons.items()}

        def annulus(r0, r1):
            q = int(math.ceil(r1)) + 1
            ay, ax = np.mgrid[-q:q + 1, -q:q + 1]
            d = np.hypot(ax, ay)
            k = ((d >= r0) & (d <= r1)).astype(np.float32)
            return k / k.sum()

        self.k_ring = annulus(R - 1.2, R + 0.6)
        self.k_in = annulus(R * 0.55, R * 0.75)
        self.k_out = annulus(R + 2.2, R + 3.8)
        ang = np.radians(np.arange(0, 360, 5))
        self.acos, self.asin = np.cos(ang), np.sin(ang)

    # 화면 읽기 --------------------------------------------------------
    def _region(self):
        """롤 창 오른쪽 아래(설정에 따라 왼쪽 아래)의 정사각형 영역이에요. 미니맵을 가장 크게 해도 들어가는 크기예요."""
        probe = None
        if self.region:
            l, t, z = self.region
            probe = (l + z * 0.8, t + z * 0.8) if self.side == "right" else (l + z * 0.2, t + z * 0.8)
        rect = league_window_rect(probe)
        if rect is None and probe is not None:
            rect = league_window_rect()
            if rect is not None:
                return None  # 미니맵 자리에 다른 창이 있어요
        if rect is None:
            return None
        L, T, W, H = rect
        z = int(min(0.5 * H, 0.4 * W))
        left = L + W - z if self.side == "right" else L
        self.region = (left, T + H - z, z)
        if self.win != (W, H):
            if self.win is not None:
                log(f"미니맵: 롤 창 크기가 {self.win} → {(W, H)}로 바뀌어서 아이콘 크기를 다시 맞출게요.")
                self._reset_size()
            self.win = (W, H)
        return self.region

    def _grab(self, left, top, z):
        if self._grab_fn:
            return self._grab_fn(left, top, z)
        shot = self.sct.grab({"left": int(left), "top": int(top), "width": int(z), "height": int(z)})
        return self.np.asarray(shot)[:, :, :3].copy()

    def _reset_size(self):
        self.size, self.scaled = None, {}
        self.box, self.box_sum, self.box_rounds, self.box_tries = None, None, 0, 0
        self.size_from_cache = False
        self.calib_sum, self.calib_rounds = {}, 0

    # 아이콘 크기 맞추기 ------------------------------------------------
    def _find_box(self, frame):
        """읽는 영역 안에서 미니맵 테두리를 찾아요. 미니맵은 영역의 아래쪽 모서리에 붙은 정사각형이라,
        한 변의 길이만 찾으면 돼요. 왼쪽 변과 위쪽 변에 밝기가 뚝 끊기는 선이 길게 이어지는 크기를 골라요.
        게임 화면은 계속 바뀌고 테두리는 그대로라서, 여러 화면을 모아서 정해요.
        (2026-11-16 실제 게임에서 미니맵 바깥의 게임 화면을 챔피언 아이콘으로 잘못 찾아서 넣었어요)"""
        cv2, np = self.cv2, self.np
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if self.side != "right":
            g = g[:, ::-1]
        z = g.shape[0]
        gx = np.abs(g[:, 2:] - g[:, :-2])
        gy = np.abs(g[2:, :] - g[:-2, :])
        sc = np.zeros(z, dtype=np.float32)
        for s in range(max(120, z // 5), z - 4):
            o = z - s
            a = gx[o:z, max(0, o - 2):o + 1].max(axis=1)
            b = gy[max(0, o - 2):o + 1, o:z].max(axis=0)
            sc[s] = ((a > 25).mean() + (b > 25).mean()) / 2
        self.box_sum = sc if self.box_sum is None or self.box_sum.shape != sc.shape else self.box_sum + sc
        self.box_rounds += 1
        if self.box_rounds < MM_BOX_ROUNDS:
            return
        best = int(self.box_sum.argmax())
        score = float(self.box_sum[best]) / self.box_rounds
        self.box_tries += 1
        self.box_sum, self.box_rounds = None, 0
        if score >= 0.8:
            self.box = min(z, best + MM_BOX_PAD)
            log(f"미니맵: 테두리를 찾았어요. 한 변 {best}px (점수 {score:.2f}). 이 안에서만 아이콘을 찾아요.")
        elif self.box_tries >= MM_BOX_TRIES:
            log(f"미니맵: 테두리를 찾지 못해서(가장 잘 맞은 크기 {best}px, 점수 {score:.2f}) 영역 전체에서 아이콘을 찾아요.")

    def _sub(self, frame):
        """미니맵 부분만 잘라 낸 그림과, 그 그림이 영역 안에서 시작하는 자리(x, y)를 돌려줘요."""
        z = frame.shape[0]
        if not self.box or self.box >= z:
            return frame, 0, 0
        o = z - self.box
        if self.side == "right":
            return frame[o:, o:], o, o
        return frame[o:, :self.box], 0, o

    def _best(self, frame, tpl):
        res = self.cv2.matchTemplate(frame, tpl, self.cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = self.cv2.minMaxLoc(res)
        return mx, loc

    def _ally_score(self, gray, size):
        """우리 팀(나 포함) 아이콘이 이 크기에서 얼마나 잘 맞는지. 우리 팀은 항상 보여서 기준으로 써요.
        잘 맞는 3명의 평균을 써요(겹치거나 죽은 사람이 있어도 괜찮게). 빠르게 하려고 흑백으로 봐요."""
        cv2 = self.cv2
        scores = []
        for i, p in enumerate(self.players):
            if p["ally"] and i in self.templates:
                tpl = cv2.cvtColor(cv2.resize(self.templates[i], (size, size), interpolation=cv2.INTER_AREA),
                                   cv2.COLOR_BGR2GRAY)
                scores.append(self._best(gray, tpl)[0])
        scores.sort(reverse=True)
        top = scores[:3]
        return sum(top) / len(top) if top else 0.0

    def _cache_key(self):
        return f"{self.win[0]}x{self.win[1]}_{self.side}"

    def _load_cached_size(self):
        try:
            with open(MM_CACHE, encoding="utf-8") as f:
                return json.load(f).get(self._cache_key())
        except Exception:
            return None

    def _save_cached_size(self):
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            try:
                with open(MM_CACHE, encoding="utf-8") as f:
                    c = json.load(f)
            except Exception:
                c = {}
            c[self._cache_key()] = self.size
            with open(MM_CACHE, "w", encoding="utf-8") as f:
                json.dump(c, f)
        except Exception:
            pass

    def _calibrate(self, frame, t):
        self.last_calib = t
        gray = self.cv2.cvtColor(self._sub(frame)[0], self.cv2.COLOR_BGR2GRAY)
        cached = self._load_cached_size()
        if cached and not self.calib_rounds and self.calib_tries == 0:
            self.size, self.size_from_cache, self.verify_left = cached, True, 3
            self._scale_all(cached)
            log(f"미니맵: 저장해 둔 아이콘 크기 {cached}px를 써요 (창 {self._cache_key()})")
            return
        for z in MM_SIZES:
            self.calib_sum[z] = self.calib_sum.get(z, 0.0) + self._ally_score(gray, z)
        self.calib_rounds += 1
        if self.calib_rounds < MM_CALIB_ROUNDS:
            return
        best = max(self.calib_sum, key=self.calib_sum.get)
        # 2px 간격으로 찾은 뒤 바로 옆 크기도 확인해요
        near = {z: self._ally_score(gray, z) for z in (best - 1, best, best + 1) if z >= 6}
        best = max(near, key=near.get)
        mean = self.calib_sum.get(best, near[best] * MM_CALIB_ROUNDS) / MM_CALIB_ROUNDS
        self.calib_tries += 1
        if max(mean, near[best]) < 0.5:
            log(f"미니맵: 우리 팀 아이콘을 찾지 못했어요(가장 잘 맞은 크기 {best}px, 점수 {near[best]:.2f}). "
                f"잠시 뒤 다시 해 볼게요. 미니맵을 왼쪽에 두었다면 config.json의 minimap_side를 \"left\"로 바꿔 주세요.")
            self._save_fail(frame)
            self.calib_sum, self.calib_rounds = {}, 0
            return
        self.size, self.calib_score = best, round(near[best], 2)
        self._scale_all(best)
        self._save_cached_size()
        log(f"미니맵: 아이콘 크기 {best}px로 맞췄어요 (우리 팀 점수 {near[best]:.2f})")
        self._save_debug("minimap_calib", frame, self._detect(frame), t)

    def _save_fail(self, frame):
        if self.save_debug and not self.fail_saved:
            self.fail_saved = True
            self._write(os.path.join(DEBUG_DIR, f"minimap_fail_{datetime.now():%Y%m%d_%H%M%S}.png"), frame)

    # 찾기 ------------------------------------------------------------
    def _ring_masks(self, img):
        """테두리 색인 점들. 상대 팀 빨강, 우리 팀 파랑(색약 모드가 아닌 기본 색 기준)."""
        cv2 = self.cv2
        h, s, v = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2HSV))
        red = ((h < 10) | (h > 170)) & (s > 130) & (v > 140)
        blue = (h > 95) & (h < 115) & (s > 110) & (v > 140)
        return red, blue

    def _ring_cands(self, mask):
        """테두리 색 점이 아이콘 크기의 원 둘레에 모여 있는 자리를 찾아요.
        색이 넓게 칠해진 곳(강, 넥서스)은 원 안쪽과 바깥쪽도 같은 색이라서 빼요."""
        cv2, np = self.cv2, self.np
        m = mask.astype(np.float32)
        f = lambda k: cv2.filter2D(m, -1, k, borderType=cv2.BORDER_CONSTANT)
        sc = f(self.k_ring) - np.minimum(f(self.k_in), f(self.k_out))
        ys, xs = np.where((sc >= MM_RING_MIN) & (sc >= cv2.dilate(sc, np.ones((7, 7), np.uint8)) - 1e-6))
        keep = []
        for v, x, y in sorted(((float(sc[y, x]), int(x), int(y)) for y, x in zip(ys, xs)), reverse=True):
            if all((x - a) ** 2 + (y - b) ** 2 > 64 for _, a, b in keep):
                keep.append((v, x, y))
        return keep

    def _ring_hits(self, mask, x, y):
        """원 둘레를 5도씩 돌면서 테두리 색이 있는지."""
        np = self.np
        h, w = mask.shape
        hit = np.zeros(len(self.acos), bool)
        for r in (self.R - 1, self.R - 0.5, self.R, self.R + 0.5):
            px = np.clip(np.round(x + r * self.acos).astype(int), 0, w - 1)
            py = np.clip(np.round(y + r * self.asin).astype(int), 0, h - 1)
            hit |= mask[py, px]
        return hit

    def _score(self, img, vis, i, x0, y0):
        """왼쪽 위가 (x0, y0)인 자리의 그림이 i번 챔피언과 얼마나 닮았는지. 보이는 부분(vis)만 비교해요."""
        S = self.S
        if x0 < 0 or y0 < 0:
            return -1.0
        I = img[y0:y0 + S, x0:x0 + S]
        if I.shape[:2] != (S, S):
            return -1.0
        I = I.astype(self.np.float32)
        T = self.full[i]
        w = vis[..., None]
        n = float(vis.sum()) * 3
        if n < 90:
            return -1.0
        a = (I - float((I * w).sum()) / n) * w
        b = (T - float((T * w).sum()) / n) * w
        den = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
        return float((a * b).sum()) / den if den > 1e-6 else -1.0

    def _detect(self, frame, t=None):
        """① 색 테두리 원을 찾고 ② 겹친 원은 누가 앞인지 정한 다음 ③ 안 가려진 부분만으로 누구인지 맞춰요.
        ④ 그래도 못 찾은 챔피언은 예전처럼 그림만으로 한 번 더 찾아요(기준을 높게).
        돌려주는 값: [[번호, x, y, 점수], ...]. 번호 -1은 이름 모르는 상대 아이콘, -2는 이름 모르는 우리 팀 아이콘이에요."""
        cv2, np = self.cv2, self.np
        img, ox, oy = self._sub(frame)   # 좌표는 영역 기준으로 다시 돌려놔요(분석 쪽은 그대로)
        S, R = self.S, self.R
        hs = S // 2
        red, blue = self._ring_masks(img)
        cands = []
        for ally, mask in ((False, red), (True, blue)):
            for v, x, y in self._ring_cands(mask):
                cands.append({"ally": ally, "ring": v, "x": x, "y": y, "hit": self._ring_hits(mask, x, y), "occ": []})
        # 누가 앞인지: 상대 원 안쪽을 지나가는 내 테두리가 보이면 내가 앞이에요
        for ai, a in enumerate(cands):
            for b in cands[ai + 1:]:
                if math.hypot(a["x"] - b["x"], a["y"] - b["y"]) >= 2 * R - 1:
                    continue
                ia = np.hypot(a["x"] + R * self.acos - b["x"], a["y"] + R * self.asin - b["y"]) < R - 2
                ib = np.hypot(b["x"] + R * self.acos - a["x"], b["y"] + R * self.asin - a["y"]) < R - 2
                fa = float(a["hit"][ia].mean()) if ia.any() else 0.0
                fb = float(b["hit"][ib].mean()) if ib.any() else 0.0
                if abs(fa - fb) <= 0.15:
                    fa, fb = a["ring"], b["ring"]
                (b if fa >= fb else a)["occ"].append(a if fa >= fb else b)
                if t is not None:
                    self.fast_until = t + MM_FAST_SEC
        pairs = []
        for ci, c in enumerate(cands):
            best = {}
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    x0, y0 = c["x"] + dx - hs, c["y"] + dy - hs
                    vis = self.disc
                    if c["occ"]:
                        vis = vis.copy()
                        for o in c["occ"]:
                            vis[np.hypot(self.gx + x0 - o["x"], self.gy + y0 - o["y"]) <= R + 0.8] = 0
                    vf = float(vis.sum()) / float(self.disc.sum())
                    if vf < MM_ID_MINVIS:
                        continue
                    for i in self.full:
                        if self.players[i]["ally"] != c["ally"]:
                            continue
                        sc = self._score(img, vis, i, x0, y0)
                        if i not in best or sc > best[i][0]:
                            best[i] = (sc, vf, x0 + hs, y0 + hs)
            c["best"] = best
            for i, (sc, vf, x, y) in best.items():
                second = max((v[0] for j, v in best.items() if j != i), default=-1.0)
                pairs.append((sc, ci, i, vf, x, y, sc - second))
        found, used = {}, set()
        for sc, ci, i, vf, x, y, margin in sorted(pairs, reverse=True):
            if i in found or ci in used:
                continue
            if vf >= 0.9:
                ok = sc >= MM_ID_FULL
            else:
                ok = sc >= MM_ID_PART and margin >= MM_ID_MARGIN
            if ok:
                found[i] = [i, x + ox, y + oy, max(60, int(round(sc * 100)))]
                used.add(ci)
        self.stat["ring"] += len(found)
        # 그림만으로 한 번 더 (테두리 색을 못 읽은 경우 대비)
        gray = None
        z = self.size
        for i in self.full:
            if i in found or i not in self.scaled_g:
                continue
            if gray is None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            res = cv2.matchTemplate(gray, self.scaled_g[i], cv2.TM_CCOEFF_NORMED)
            best = (-1.0, None)
            for _ in range(2):
                _, mx, _, (x, y) = cv2.minMaxLoc(res)
                if mx < 0.4:
                    break
                cx, cy = x + z // 2, y + z // 2
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        sc = self._score(img, self.disc, i, cx + dx - hs, cy + dy - hs)
                        if sc > best[0]:
                            best = (sc, (cx + dx, cy + dy))
                res[max(0, y - z):y + z, max(0, x - z):x + z] = -1
            if best[1] is not None and best[0] >= MM_PLAIN:
                # 이미 찾은 아이콘과 같은 자리면 넣지 않아요
                if all(math.hypot(best[1][0] + ox - f[1], best[1][1] + oy - f[2]) > 6 for f in found.values()):
                    found[i] = [i, best[1][0] + ox, best[1][1] + oy, int(round(best[0] * 100))]
                    self.stat["plain"] += 1
        # 바로 전 위치로 이어 붙이기: 누구인지 못 정한 원 근처에, 조금 전까지 보이던 같은 팀 챔피언이 있으면 그 챔피언으로 봐요
        if t is not None:
            opts = []
            for ci, c in enumerate(cands):
                if ci in used or any(math.hypot(c["x"] + ox - f[1], c["y"] + oy - f[2]) <= 6 for f in found.values()):
                    continue
                for i, (lt, lx, ly) in self.last_pos.items():
                    if i in found or i in self.dead or self.players[i]["ally"] != c["ally"]:
                        continue
                    dt = t - lt
                    if not (0 < dt <= MM_TRACK_SEC):
                        continue
                    d = math.hypot(c["x"] - lx, c["y"] - ly)
                    b = c["best"].get(i)
                    if d <= MM_TRACK_SPEED * S * dt + 4 and b is not None and b[0] >= MM_TRACK_MINSCORE:
                        opts.append((d, ci, i))
            for d, ci, i in sorted(opts):
                if i not in found and ci not in used:
                    found[i] = [i, cands[ci]["x"] + ox, cands[ci]["y"] + oy, MM_TRACK_TAG]
                    used.add(ci)
                    self.stat["track"] += 1
            for i, f in found.items():
                if f[3] != MM_TRACK_TAG:
                    self.last_pos[i] = (t, f[1] - ox, f[2] - oy)
        out = list(found.values())
        for ci, c in enumerate(cands):
            if ci not in used and c["ring"] >= MM_RING_UNKNOWN and \
                    all(math.hypot(c["x"] + ox - f[1], c["y"] + oy - f[2]) > 6 for f in found.values()):
                out.append([-2 if c["ally"] else -1, c["x"] + ox, c["y"] + oy, int(round(c["ring"] * 100))])
                self.stat["unknown"] += 1
        return out

    def check(self, t):
        """1초에 한 번쯤 불러요. 미니맵 영역을 읽고 10명의 아이콘을 찾아 기록해요."""
        if not self.players or len(self.templates) < len(self.players) // 2:
            return
        reg = self._region()
        if reg is None:
            if not self.hidden_logged:
                self.hidden_logged = True
                log(f"미니맵: 롤 화면이 안 보여서 읽지 못했어요 (보이는 창: {LAST_BLOCKER['name']})")
            return
        self.hidden_logged = False
        t0 = time.perf_counter()
        frame = self._grab(*reg)
        cv2, np = self.cv2, self.np
        small = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (MM_SMALL, MM_SMALL), interpolation=cv2.INTER_AREA)
        self.ref = small.copy() if self.ref is None or self.ref.shape != small.shape else np.maximum(self.ref, small)
        self.recent.append((t, small))
        if self.box is None and self.box_tries < MM_BOX_TRIES:
            self._find_box(frame)
            if self.box is None and self.box_tries < MM_BOX_TRIES:
                return
        if self.size is None:
            if t >= MM_CALIB_FROM and t - self.last_calib >= MM_CALIB_EVERY:
                self._calibrate(frame, t)
            return
        dets = self._detect(frame, t)
        if self.size_from_cache and self.verify_left > 0:
            self.verify_left -= 1
            allies = sorted((d[3] for d in dets if self.players[d[0]]["ally"]), reverse=True)[:3]
            if len(allies) < 2 or sum(allies) / len(allies) < 50:
                if self.verify_left == 0:
                    log("미니맵: 저장해 둔 아이콘 크기가 안 맞는 것 같아서 다시 맞출게요.")
                    self._reset_size()
                    self.calib_tries = 1  # 저장된 크기를 다시 쓰지 않게
                    return
            else:
                self.verify_left = 0
        self.frames.append([round(t, 1), dets])
        self.last_full = (t, frame, dets)
        if self.save_debug and t - self.last_raw >= MM_RAW_EVERY:
            self.last_raw = t
            self._save_debug("minimap_sample", frame, dets, t)
        self.ms.append((time.perf_counter() - t0) * 1000)
        if time.time() - self.last_ms_log > 300:
            self.last_ms_log = time.time()
            st, self.stat = self.stat, {"ring": 0, "plain": 0, "track": 0, "unknown": 0}
            log(f"미니맵: 한 번 읽는 데 평균 {sum(self.ms) / len(self.ms):.0f}ms (최근 {len(self.ms)}번). "
                f"테두리로 찾음 {st['ring']}, 그림만으로 찾음 {st['plain']}, 바로 전 위치로 이어 붙임 {st['track']}, "
                f"이름 모르는 아이콘 {st['unknown']}")

    # 죽을 때 ---------------------------------------------------------
    @staticmethod
    def _pack(img):
        """회색 그림을 압축한 글자로 바꿔요. 분석 쪽에서 파이썬 기본 기능(zlib)만으로 풀 수 있어요."""
        return base64.b64encode(zlib.compress(img.tobytes(), 9)).decode("ascii")

    def death_snapshot(self, t_death, t_label):
        """죽기 직전 미니맵의 밝기(줄인 그림)와, 지금까지 가장 밝았던 밝기를 저장해요.
        둘을 비교하면 그때 어디가 안개(시야 없음)였는지 알 수 있어요."""
        if self.ref is None:
            return None
        before = [r for r in self.recent if r[0] <= t_death + 0.05]
        if not before:
            return None
        tt, small = before[-1]
        snap = {"t": round(tt, 1), "size": MM_SMALL, "cur": self._pack(small), "ref": self._pack(self.ref)}
        if self.last_full and self.last_full[0] <= t_death + 0.05:
            self._save_debug("minimap_death", self.last_full[1], self.last_full[2], t_label)
        return snap

    def _write(self, path, img):
        try:
            os.makedirs(DEBUG_DIR, exist_ok=True)
            ok, buf = self.cv2.imencode(".png", img)
            if ok:
                with open(path, "wb") as f:
                    f.write(buf.tobytes())
        except Exception as e:
            log(f"미니맵 이미지 저장 실패: {e}")

    def _save_debug(self, prefix, frame, dets, t):
        """확인용 그림 두 장을 저장해요. ① 아무 표시도 없는 미니맵(_raw) ② 찾은 아이콘 아래에 이름과 점수를 적은 그림.
        글자색: 파랑 = 우리 팀, 빨강 = 상대 팀, 노랑 = 나, 흰색 = 이름 모르는 아이콘.
        (예전에는 아이콘 위에 동그라미를 그려서, 저장된 그림으로는 테두리를 다시 시험할 수 없었어요)"""
        if not self.save_debug:
            return
        cv2 = self.cv2
        sub, ox, oy = self._sub(frame)
        name = f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}_{int(t)}s"
        self._write(os.path.join(DEBUG_DIR, name + "_raw.png"), sub)
        k = 3
        img = cv2.resize(sub, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)
        r = int((self.R or 15) * k)
        for i, x, y, sc in dets:
            if i < 0:
                col, label = (255, 255, 255), ("?ally" if i == -2 else "?enemy")
            else:
                p = self.players[i]
                col = (0, 220, 255) if p["me"] else ((255, 140, 0) if p["ally"] else (0, 0, 255))
                label = p["key"][:6]
            cx, cy = (x - ox) * k, (y - oy) * k
            cv2.line(img, (cx - 6, cy + r + 6), (cx + 6, cy + r + 6), col, 2)
            cv2.putText(img, f"{label} {sc}", (cx - r, cy + r + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
            cv2.putText(img, f"{label} {sc}", (cx - r, cy + r + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
        self._write(os.path.join(DEBUG_DIR, name + ".png"), img)

    def to_record(self):
        return {
            "version": 2,            # 2 = 테두리 원으로 찾기(2026-11-16). 번호 -1/-2는 이름 모르는 상대/우리 팀 아이콘
            "players": self.players,
            "iconFull": self.S,
            "size": self.size,
            "regionSide": self.region[2] if self.region else None,
            "box": self.box,
            "window": list(self.win) if self.win else None,
            "side": self.side,
            "calibScore": self.calib_score,
            "keepScore": MM_KEEP,
            "msAvg": round(sum(self.ms) / len(self.ms)) if self.ms else None,
            "frames": self.frames,
        }


# ---------------------------------------------------------------- 한 판 기록

class GameSession:
    def __init__(self, data, tracker, mm=None):
        gd = data.get("gameData", {})
        self.mode = gd.get("gameMode", "")
        self.start_epoch = time.time() - gd.get("gameTime", 0)
        me = find_me(data) or {}
        self.me_names = {me.get("riotId"), me.get("summonerName"), me.get("riotIdGameName")} - {None, ""}
        self.champion = champ_key(me)
        self.tracker = tracker
        self.mm = mm            # 미니맵 읽기 (없으면 None)
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
        if self.mm and p.get("minimap"):
            self.mm.frames = [f for f in (p["minimap"].get("frames") or []) if f[0] <= now_t]
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

        if self.mm:
            try:
                self.mm.set_players(data)
            except Exception as e:
                log(f"미니맵 준비 오류: {e}")
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
        if self.mm:
            try:
                entry["minimap"] = self.mm.death_snapshot(t_death, t_death)
            except Exception as e:
                log(f"미니맵 죽음 기록 오류: {e}")
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
            "minimap": self.mm.to_record() if self.mm else None,
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


def start_replay_worker(after_game):
    """게임 뒤 프로그램(replay_worker.py)을 따로 켜요. 리플레이를 받아 디코딩하고 1초 위치를 올려요.
    따로 돌아서 여기서 문제가 생겨도 이 기록 프로그램은 그대로예요. 다음 판이 시작되면 받기·디코딩을 미뤄요."""
    path = os.path.join(HERE, "replay_worker.py")
    if not os.path.exists(path):
        return
    try:
        import subprocess
        subprocess.Popen([sys.executable, path] + (["--after-game"] if after_game else []), cwd=HERE,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        log("리플레이 받기·디코딩을 따로 시작했어요. 진행은 replay_log.txt에 남아요.")
    except Exception as e:
        log(f"리플레이 프로그램 시작 실패({e})")


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
    prune(DEBUG_DIR, KEEP_DEBUG_IMAGES * 2, prefix="minimap_", suffix=".png")
    prune(DEBUG_DIR, 0, prefix="afterdeath_", suffix=".png")  # 예전 방식으로 저장된 사진은 정리해요
    prune(GAMES_DIR, KEEP_GAME_FILES, suffix=".json")
    log(f"게임 종료: {rec['gameMode']} / {int(rec['gameLength'] // 60)}분 / 데스 {len(rec['deaths'])}번 기록")
    if rec["gameMode"] == "CLASSIC" and rec["gameLength"] >= 300:
        os.makedirs(PENDING_DIR, exist_ok=True)
        with open(os.path.join(PENDING_DIR, name), "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)
        upload_pending(cfg)
        start_replay_worker(after_game=True)
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
    start_replay_worker(after_game=False)  # 지난번에 못 끝낸 리플레이가 있으면 이어서 해요
    if cfg["minimap_check"]:
        threading.Thread(target=prefetch_mm_icons, daemon=True).start()

    session = None
    fails = 0
    last_poll = 0
    spell_gap = 1.0 / max(0.5, float(cfg["spell_checks_per_second"]))
    last_spell = 0
    mm = None
    mm_gap = 1.0 / max(0.2, float(cfg["minimap_checks_per_second"]))
    # 11-22: 겹칠 때 더 자주 읽기를 껐어요. 거의 항상 겹침으로 잡혀서 게임 내내 1초에 약 2.4번 읽고 있었고,
    # 리포트는 미니맵 기록을 쓰지 않아요(위치는 리플레이 1초 위치). config.json에 예전 값 3이 남아 있어도 1초에 1번이에요.
    mm_fast_gap = mm_gap if not MM_FIGHT_FAST else min(mm_gap, 1.0 / max(0.2, float(cfg.get("minimap_fight_checks_per_second", 3))))
    last_mm = 0
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
                        mm = None
                        if cfg["minimap_check"] and tracker_ok:
                            try:
                                mm = MinimapTracker(cfg)
                            except Exception as e:
                                log(f"미니맵 읽기 시작 실패: {e}")
                        session = GameSession(data, tracker, mm)
                    else:
                        session.update(data)
                elif session is not None:
                    fails += 1
                    if session.ended or fails >= 5:
                        finish(session, cfg)
                        session, tracker, mm = None, None, None
            if session and tracker and session.post_death and now - last_spell >= AFTER_DEATH_GAP:
                last_spell = now
                session.watch_after_death()
            elif session and tracker and not session.was_dead and now - last_spell >= spell_gap \
                    and session.last_game_time >= LOADING_WAIT:
                last_spell = now
                tracker.check(session.est_game_time())
            # 로딩 화면에서는 게임 시간이 0에 멈춰 있어요. 이때 화면을 읽으면 로딩 화면의 스펠 그림을
            # 스펠 칸으로 잘못 저장하고, 미니맵 테두리 찾기도 실패해요(2026-11-17 애쉬 판, 로딩 48초).
            if session and mm and not session.was_dead and session.last_game_time >= LOADING_WAIT:
                gt = session.est_game_time()
                if now - last_mm >= (mm_fast_gap if gt <= mm.fast_until else mm_gap):
                    last_mm = now
                    mm.check(gt)
        except Exception:
            log("오류가 났지만 계속 실행할게요:\n" + traceback.format_exc())
            time.sleep(2)
        time.sleep(STEP)


if __name__ == "__main__":
    main()
