import json
import os
import subprocess
import sys
import time
import mimetypes
from pathlib import Path
from typing import Any, Dict, List

from google import genai
from google.genai import types
from PIL import Image

from utils.matrix_stitcher import build_character_matrix


def load_json(filepath: str) -> Dict[str, Any]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath: str, data: Dict[str, Any]) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def extract_last_frame(video_path: str, output_image_path: str) -> str:
    """Mengekstrak bingkai terakhir daripada video MP4 untuk kesinambungan babak."""
    os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-sseof",
        "-0.1",
        "-i",
        video_path,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        output_image_path,
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_image_path


def concatenate_scenes_with_bumper(
    scene_videos: List[str], bumper_path: str, final_output: str
) -> str:
    """Mencantumkan babak (8s setiap satu) bersama bumper penutup (6s)."""
    os.makedirs(os.path.dirname(final_output), exist_ok=True)
    concat_list_path = "temp/concat_manifest.txt"

    with open(concat_list_path, "w", encoding="utf-8") as f:
        for vid in scene_videos:
            f.write(f"file '{Path(vid).resolve()}'\n")
        if os.path.exists(bumper_path):
            f.write(f"file '{Path(bumper_path).resolve()}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_list_path,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        final_output,
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return final_output


# Senarai model mengikut keutamaan — Veo 3.1 menggantikan Veo 2.0 (tamat 30 Jun 2026)
_VEO_PRIORITY = [
    "veo-3.1-generate-preview",
    "veo-3.1-fast-generate-preview",
    "veo-3.0-generate-preview",
]


def get_available_video_model(client: genai.Client) -> str:
    """Mengesahkan model janaan video Veo yang tersedia untuk API key semasa."""
    try:
        available = [m.name for m in client.models.list()]
        for candidate in _VEO_PRIORITY:
            if any(candidate in m for m in available):
                print(f"[Model] Menggunakan: {candidate}")
                return candidate
        # Jika tiada yang tersenarai, cuba model utama secara terus
        print(f"[Model] Senarai model tidak dapat disemak — cuba {_VEO_PRIORITY[0]}")
    except Exception as exc:
        print(f"[Model] Gagal senarai model ({exc}) — cuba {_VEO_PRIORITY[0]}")
    return _VEO_PRIORITY[0]


def render_scene_video(
    client: genai.Client,
    prompt_text: str,
    reference_images: List[str],
    output_video_path: str,
) -> str:
    """Memanggil API penjanaan video dengan sintaks terkini."""
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)

    target_model = get_available_video_model(client)

    # Convert image file paths to VideoGenerationReferenceImage objects
    api_reference_images = []
    for img_path in reference_images:
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                img_bytes = f.read()
            mime_type, _ = mimetypes.guess_type(img_path)
            if not mime_type:
                mime_type = "image/png"
            api_reference_images.append(
                types.VideoGenerationReferenceImage(
                    image=types.Image(
                        image_bytes=img_bytes,
                        mime_type=mime_type
                    )
                )
            )

    # Menggunakan generate_videos dengan keyword arguments sahaja (sintaks terkini)
    operation = client.models.generate_videos(
        model=target_model,
        source=types.GenerateVideosSource(
            prompt=prompt_text
        ),
        config=types.GenerateVideosConfig(
            aspect_ratio="9:16",
            duration_seconds=8,
            number_of_videos=1,
            person_generation="allow_adult",
            reference_images=api_reference_images if api_reference_images else None,
        ),
    )

    while not operation.done:
        time.sleep(10)
        operation = client.operations.get(operation)

    result = operation.result
    if result and result.generated_videos:
        video_bytes = result.generated_videos[0].video.video_bytes
        with open(output_video_path, "wb") as f:
            f.write(video_bytes)
        return output_video_path
    else:
        raise RuntimeError("Gagal menjana video babak daripada API.")


def run_pipeline():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Ralat: GEMINI_API_KEY tidak ditemui dalam environment variable.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    characters_db = load_json("data/characters.json")["characters"]
    backgrounds_db = load_json("data/backgrounds.json")["backgrounds"]
    episode_log = load_json("data/episode_log.json")

    manual_ep_id = os.getenv("MANUAL_EPISODE_ID", "").strip()
    next_idx = episode_log.get("next_episode_index", 1)
    target_ep_id = manual_ep_id if manual_ep_id else f"EP_{next_idx:03d}"

    theme = episode_log["upcoming_moral_themes"][0]
    location = next(
        (b for b in backgrounds_db if b["id"] == theme["recommended_location"]),
        backgrounds_db[0],
    )

    active_cast = theme["recommended_cast"]
    strip_paths = []
    for cast_id in active_cast:
        char = next((c for c in characters_db if c["id"] == cast_id), None)
        if char and os.path.exists(char["asset_strip_path"]):
            strip_paths.append(char["asset_strip_path"])

    matrix_file = build_character_matrix(
        strip_paths=strip_paths,
        output_path=f"temp/{target_ep_id}_matrix_3x3.png",
    )

    story_scenes = [
        {
            "id": 1,
            "action": "Tuah melutut mengusap lembut Oyen yang sedang lapar di hadapan rumah.",
            "dialogue": "Eh Oyen, kesiannya kamu. Mesti lapar sangat ni.",
        },
        {
            "id": 2,
            "action": "Tuah menghulurkan mangkuk ikan kecil lalu Oyen makan dengan gembira.",
            "dialogue": "Nah makan ikan ni. Kita kena selalu berbuat baik sesama makhluk.",
        },
        {
            "id": 3,
            "action": "Tuah memangku Oyen yang sudah kenyang sambil tersenyum ke arah kamera memberi pesanan moral.",
            "dialogue": "Sayangi haiwan di sekeliling kita ya kawan-kawan!",
        },
        {
            "id": 4,
            "action": "Tuah melambai tangan ke arah kamera sambil Oyen mengiau manja di sebelahnya.",
            "dialogue": "Jumpa lagi kawan-kawan! Bye bye!",
        },
    ]

    rendered_scenes = []
    prev_frame_path = None

    for scene in story_scenes:
        s_id = scene["id"]
        scene_output = f"temp/{target_ep_id}_scene_{s_id}.mp4"

        ref_slots = [matrix_file, location["asset_anchor_path"]]
        if prev_frame_path and os.path.exists(prev_frame_path):
            ref_slots.append(prev_frame_path)

        prompt = (
            f"Claymation animation style. 9:16 vertical ratio. "
            f"Location: {location['canonical_name']}. {location['lighting_default']}. "
            f"Action: {scene['action']} "
            f"Character Tuah speaks in Malay: '{scene['dialogue']}'. "
            f"Maintain high consistency with character reference matrix and environmental anchor."
        )

        video_path = render_scene_video(client, prompt, ref_slots, scene_output)
        rendered_scenes.append(video_path)

        prev_frame_path = f"temp/{target_ep_id}_frame_scene_{s_id}.png"
        extract_last_frame(video_path, prev_frame_path)

    bumper_path = "assets/bumpers/tiktok_outro_6s.mp4"
    # Duration could be 38s now with 4 scenes, so changing the file suffix to be generic
    final_output = f"output/{target_ep_id}_master.mp4"

    concatenate_scenes_with_bumper(rendered_scenes, bumper_path, final_output)

    new_record = {
        "episode_id": target_ep_id,
        "title": theme["title"],
        "moral_theme": theme["moral_value"],
        "active_cast": active_cast,
        "primary_location": location["id"],
        "date_rendered": "2026-09-11",
        "output_file": final_output,
        "status": "COMPLETED",
    }
    episode_log["history"].append(new_record)
    episode_log["next_episode_index"] = next_idx + 1
    episode_log["upcoming_moral_themes"].pop(0)

    save_json("data/episode_log.json", episode_log)
    print(f"Produksi selesai: {final_output}")


if __name__ == "__main__":
    run_pipeline()