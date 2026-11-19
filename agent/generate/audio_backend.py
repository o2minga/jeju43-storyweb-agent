"""TTS(Windows SAPI)·BGM(절차적 합성) 실제 오디오 생성 백엔드.

내레이션은 Windows에 내장된 System.Speech(SAPI) 한국어 음성(기본 "Microsoft Heami
Desktop")으로 실제 합성한다 — 클라우드 API 키가 필요 없는 대신 Windows에서만
동작한다. Windows가 아니거나 해당 음성이 없으면 synthesize_narration()이 False를
반환하고, 호출부(step04_audio.py)가 placeholder로 조용히 폴백한다(파이프라인을
막지 않는다).

BGM은 numpy로 낮은 화음 여러 개를 겹친 잔잔한 앰비언트 패드를 절차적으로 합성한다 —
외부 음원이 아니므로 저작권 문제 없이 항상 만들 수 있다(license="self-generated").
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

logger = logging.getLogger("agent.generate.audio_backend")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TTS_SCRIPT = REPO_ROOT / "scripts" / "tts-sapi.ps1"
DEFAULT_VOICE = "Microsoft Heami Desktop"

# 제주 바람·파도를 연상시키는 낮은 화음 4개(펜타토닉, G2 기준). 서로 살짝 디튠해 단조로운
# 순정 사인파처럼 들리지 않게 한다.
_PAD_FREQS_HZ = (98.00, 130.81, 146.83, 196.00)


def synthesize_narration(text: str, out_path: Path, voice_name: str = DEFAULT_VOICE) -> bool:
    """Windows SAPI로 text를 out_path(.wav)에 합성한다. 성공하면 True."""
    if shutil.which("powershell") is None:
        logger.warning("powershell을 찾을 수 없어 TTS를 건너뜁니다 (Windows 전용 기능) — placeholder로 폴백")
        return False

    out_path.parent.mkdir(parents=True, exist_ok=True)
    text_path = out_path.with_suffix(".tts-input.txt")
    text_path.write_text(text, encoding="utf-8")

    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(_TTS_SCRIPT),
                "-TextPath", str(text_path),
                "-OutPath", str(out_path),
                "-VoiceName", voice_name,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("TTS(SAPI) 실행 실패 — placeholder로 폴백: %s", exc)
        return False
    finally:
        text_path.unlink(missing_ok=True)

    if result.returncode != 0 or not out_path.exists():
        logger.warning(
            "TTS(SAPI) 실패(returncode=%s) — placeholder로 폴백: %s",
            result.returncode,
            result.stderr.strip(),
        )
        return False
    return True


def wav_duration_sec(path: Path) -> float:
    with wave.open(str(path), "rb") as f:
        return f.getnframes() / float(f.getframerate())


def synthesize_bgm(out_path: Path, duration_sec: float = 60.0, sample_rate: int = 44100) -> None:
    """차분한 앰비언트 패드를 절차적으로 합성해 로열티 프리 BGM(.wav)을 만든다."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)

    signal = np.zeros_like(t)
    for i, freq in enumerate(_PAD_FREQS_HZ):
        detune = 1.0 + (i - len(_PAD_FREQS_HZ) / 2) * 0.0015
        signal += np.sin(2 * np.pi * freq * detune * t) / len(_PAD_FREQS_HZ)

    # 느린 LFO로 음량이 숨쉬듯 변하게 해 단조로움을 줄인다.
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.05 * t)
    signal *= lfo

    # 시작/끝 페이드 — <audio loop>로 반복 재생될 때 이음매 클릭음을 없앤다.
    fade_len = min(int(sample_rate * 2.0), len(signal) // 2)
    if fade_len > 0:
        fade_in = np.linspace(0, 1, fade_len)
        signal[:fade_len] *= fade_in
        signal[-fade_len:] *= fade_in[::-1]

    peak = np.max(np.abs(signal)) or 1.0
    signal = signal / peak * 0.35  # 낭독 대비 조용한 배경 음량으로 정규화
    pcm = (signal * 32767).astype(np.int16)

    with wave.open(str(out_path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm.tobytes())
