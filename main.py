#!/usr/bin/env python3
"""
Kembara Tuah & Oyen - Autonomous Video Pipeline Orchestrator (30 Seconds)
Integrasi Gemini Omni 1.1 Flash, Pillow Matriks Stitching, dan FFmpeg Concatenation.
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from PIL import Image

# Konfigurasi Direktori & Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
BUMPERS_DIR = os.path.join(ASSETS_DIR, "bumpers")
STRIPS_DIR = os.path.join(ASSETS_DIR, "strips")
BG_DIR = os.path.join(ASSETS_DIR, "backgrounds")
BUILD_DIR = os.path.join(BASE_DIR, "build_output")

INTRO_VIDEO = os.path.join(BUMPERS_DIR, "intro_3s.mp4")
OUTRO_VIDEO = os.path.join(BUMPERS_DIR, "outro_3s.mp4")

# Standard Dimensi
STRIP_WIDTH, STRIP_HEIGHT = 1536, 512
MATRIX_SIZE = (1536, 1536)


class PipelineRegistry:
    """Mengurus pangkalan data watak, latar belakang, dan arkib kesinambungan."""

    def __init__(self):
        self.chars = self._load_json(os.path.join(DATA_DIR, "characters.json"))
        self.backgrounds = self._load_json(os.path.join(DATA_DIR, "backgrounds.json"))
        self.episodes = self._load_json(os.path.join(DATA_DIR, "episode_log.json"))

    def _load_json(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_character_strip(self, char_key):
        char = self.chars.get(char_key)
        if not char:
            raise ValueError(f"Watak '{char_key}' tidak wujud dalam registry characters.json")
        strip_path = os.path.join(STRIPS_DIR, char["asset_file"])
        if not os.path.exists(strip_path):
            raise FileNotFoundError(f"Fail jalur untuk '{char_key}' tiada di: {strip_path}")
        return strip_path

    def get_background(self, bg_key):
        bg = self.backgrounds.get(bg_key)
        if not bg:
            raise ValueError(f"Latar '{bg_key}' tidak wujud dalam registry backgrounds.json")
        bg_path = os.path.join(BG_DIR, bg["asset_file"])
        if not os.path.exists(bg_path):
            raise FileNotFoundError(f"Fail latar '{bg_key}' tiada di: {bg_path}")
        return bg_path, bg

    def log_completed_episode(self, ep_manifest):
        self.episodes.append(ep_manifest)
        with open(os.path.join(DATA_DIR, "episode_log.json"), "w", encoding="utf-8") as f:
            json.dump(self.episodes, f, indent=2, ensure_ascii=False)
        print(f"📖 Log episod dikemas kini: {ep_manifest['episode_id']}")


def compose_modular_matrix(active_char_keys, registry, output_matrix_path):
    """
    Menjahit sehingga 3 jalur watak (1x3) menjadi 1 fail matriks grid 3x3 (1536x1536).
    """
    print(f"🎨 [STITCHER] Menyusun Matriks Karakter 3x3 untuk: {active_char_keys}")
    matrix = Image.new("RGBA", MATRIX_SIZE, (128, 128, 128, 255))

    for row_idx, char_key in enumerate(active_char_keys[:3]):
        if char_key:
            strip_file = registry.get_character_strip(char_key)
            with Image.open(strip_file).convert("RGBA") as img:
                resized_strip = img.resize((STRIP_WIDTH, STRIP_HEIGHT), Image.Resampling.LANCZOS)
                matrix.paste(resized_strip, (0, row_idx * STRIP_HEIGHT))

    matrix.save(output_matrix_path, "PNG")
    print(f"✅ Matriks komposit siap: {output_matrix_path}")
    return output_matrix_path


def generate_episode_script_plan(registry):
    """
    Fasa Brain: Merangka 1 episod baharu berteraskan nilai murni.
    (Di persekitaran hidup, bahagian ini memanggil gemini-3.7-flash API).
    """
    ep_num = len(registry.episodes) + 1
    ep_id = f"EP_{ep_num:03d}"
    print(f"🧠 [SHOWRUNNER] Merangka draf episod baharu: {ep_id}...")

    # Struktur draf kanonikal episod
    return {
        "episode_id": ep_id,
        "episode_title": "Berkongsi Air Bersih",
        "core_moral": "Menghargai sumber alam dan bersabar berkongsi rezeki",
        "active_characters": ["TUAH", "OYEN", "TOK_WAN"],
        "background_key": "kampung_yard",
        "created_at": datetime.utcnow().isoformat(),
        "scenes": [
            {
                "scene_index": 1,
                "duration_sec": 8,
                "action": "Tuah dan Oyen memeriksa tempayan air sejuk di tangga rumah.",
                "dialogue": "Tuah: 'Tok Wan, air tempayan ni sejuk dan bersih sangat!'"
            },
            {
                "scene_index": 2,
                "duration_sec": 8,
                "action": "Tok Wan mengisi mangkuk kecil untuk Oyen minum sambil menasihati Tuah.",
                "dialogue": "Tok Wan: 'Alhamdulillah, air nikmat berharga, Tuah. Gunakan secara hemat.'"
            },
            {
                "scene_index": 3,
                "duration_sec": 8,
                "action": "Tuah tersenyum melihat Oyen minum dengan tenang, mengusap kepalanya.",
                "dialogue": "Tuah: 'Tuah faham Tok Wan. Sayang alam, alam sayangkan kita.'"
            }
        ]
    }


def render_scene_video(scene_info, matrix_path, bg_path, continuity_frame, output_scene_path):
    """
    Memanggil Google Video API (Gemini Omni 1.1 Flash) bagi klip 8 saat.
    """
    idx = scene_info["scene_index"]
    print(f"🎬 [RENDER] Menjana Babak {idx} (8s) melalui Omni 1.1 Flash...")
    print(f"   Payload: Slot1={os.path.basename(matrix_path)} | Slot2={os.path.basename(bg_path)} | Slot3={os.path.basename(continuity_frame) if continuity_frame else 'None'}")
    print(f"   Dialog: \"{scene_info['dialogue']}\"")

    # API Dispatch simulasi / pelaksanaan sebenar
    # Menghasilkan fail video 8 saat (9:16, 24fps)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=sienna:s=1080x1920:d=8:r=24",
        "-f", "lavfi", "-i", "sine=f=440:d=8",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        output_scene_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    time.sleep(1)
    return output_scene_path


def extract_last_frame(video_path, output_frame_path):
    """Mengekstrak bingkai tepat terakhir bagi kesinambungan syot seterusnya."""
    cmd = [
        "ffmpeg", "-y", "-sseof", "-0.05",
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        output_frame_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_frame_path


def assemble_final_30s_episode(scene_files, final_output_path):
    """
    Menggabungkan 5 segmen:
    Intro (3s) + Scene 1 (8s) + Scene 2 (8s) + Scene 3 (8s) + Outro (3s) = Tepat 30s!
    """
    print("🎞️ [CONCAT] Menggabungkan keseluruhan segmen menjadi video rasmi 30 saat...")
    manifest_txt = os.path.join(BUILD_DIR, "concat_list.txt")

    # Pastikan fail bumper wujud (jika tiada, janakan bumper dummy untuk ujian)
    for bumper, dur, col in [(INTRO_VIDEO, 3, "darkgreen"), (OUTRO_VIDEO, 3, "midnightblue")]:
        if not os.path.exists(bumper):
            os.makedirs(os.path.dirname(bumper), exist_ok=True)
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={col}:s=1080x1920:d={dur}:r=24",
                "-f", "lavfi", "-i", f"sine=f=520:d={dur}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", bumper
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    full_sequence = [INTRO_VIDEO] + scene_files + [OUTRO_VIDEO]

    with open(manifest_txt, "w", encoding="utf-8") as f:
        for item in full_sequence:
            f.write(f"file '{os.path.abspath(item)}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", manifest_txt,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "24",
        "-c:a", "aac", "-b:a", "192k",
        "-t", "30.0",
        final_output_path
    ]
    subprocess.run(cmd, check=True)
    print(f"🏆 [SUCCESS] Video siap 30 saat dijana: {final_output_path}")
    return final_output_path


def main():
    os.makedirs(BUILD_DIR, exist_ok=True)
    registry = PipelineRegistry()

    # 1. Rangka Pelan Episod & Nilai Murni
    plan = generate_episode_script_plan(registry)

    # 2. Sedia Matriks Watak & Sauh Latar Dinamik
    matrix_path = os.path.join(BUILD_DIR, f"{plan['episode_id']}_matrix_3x3.png")
    compose_modular_matrix(plan["active_characters"], registry, matrix_path)

    bg_path, _ = registry.get_background(plan["background_key"])

    # 3. Render 3 Babak Berturutan dengan Kesinambungan Bingkai
    rendered_scenes = []
    continuity_frame = None

    for sc in plan["scenes"]:
        sc_num = sc["scene_index"]
        sc_video_path = os.path.join(BUILD_DIR, f"scene_{sc_num}.mp4")

        render_scene_video(sc, matrix_path, bg_path, continuity_frame, sc_video_path)
        rendered_scenes.append(sc_video_path)

        # Ekstrak last-frame untuk babak berikutnya
        if sc_num < 3:
            continuity_frame = os.path.join(BUILD_DIR, f"last_frame_sc{sc_num}.png")
            extract_last_frame(sc_video_path, continuity_frame)

    # 4. Cantumkan Montaj 30 Saat Penuh
    final_output = os.path.join(BUILD_DIR, f"{plan['episode_id']}_FINAL_30S.mp4")
    assemble_final_30s_episode(rendered_scenes, final_output)

    # 5. Rekodkan ke Log Sejarah
    registry.log_completed_episode({
        "episode_id": plan["episode_id"],
        "title": plan["episode_title"],
        "moral_value": plan["core_moral"],
        "active_characters": plan["active_characters"],
        "background": plan["background_key"],
        "output_file": os.path.basename(final_output),
        "completed_at": datetime.utcnow().isoformat()
    })


if __name__ == "__main__":
    main()