import os
from typing import List
from PIL import Image, ImageDraw, ImageFont


def build_character_matrix(
    strip_paths: List[str],
    output_path: str = "temp/character_matrix_3x3.png",
    canvas_size: tuple = (1024, 1024),
    bg_color: tuple = (128, 128, 128)
) -> str:
    """
    Mencantumkan 1 hingga 3 jalur watak (setiap jalur 1x3: Depan, Sisi, Belakang)
    menjadi satu Master Composite Matrix 3x3 berlatar kelabu neutral (#808080).
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    matrix_canvas = Image.new("RGB", canvas_size, color=bg_color)
    
    total_slots = 3
    row_height = canvas_size[1] // total_slots
    canvas_width = canvas_size[0]

    for index in range(total_slots):
        if index < len(strip_paths) and os.path.exists(strip_paths[index]):
            with Image.open(strip_paths[index]) as strip_img:
                strip_img = strip_img.convert("RGBA")
                # Laraskan saiz jalur mengikut nisbah lebar kanvas tanpa herotan melampau
                strip_aspect = strip_img.width / strip_img.height
                target_height = row_height - 10
                target_width = int(target_height * strip_aspect)

                if target_width > canvas_width:
                    target_width = canvas_width
                    target_height = int(target_width / strip_aspect)

                resized_strip = strip_img.resize(
                    (target_width, target_height), Image.Resampling.LANCZOS
                )

                # Letak di bahagian tengah baris
                x_offset = (canvas_width - target_width) // 2
                y_offset = (index * row_height) + ((row_height - target_height) // 2)

                # Tampal dengan sokongan alpha mask jika imej PNG lut sinar
                matrix_canvas.paste(resized_strip, (x_offset, y_offset), mask=resized_strip.split()[3] if resized_strip.mode == 'RGBA' else None)
        else:
            # Jika watak kurang daripada 3 (cth: hanya Tuah & Oyen), biarkan baris kosong sebagai padding neutral
            pass

    # Lukis garis panduan pembahagi halus warna kelabu gelap
    draw = ImageDraw.Draw(matrix_canvas)
    for r in range(1, total_slots):
        y = r * row_height
        draw.line([(0, y), (canvas_width, y)], fill=(90, 90, 90), width=2)

    col_width = canvas_width // 3
    for c in range(1, 3):
        x = c * col_width
        draw.line([(x, 0), (x, canvas_size[1])], fill=(90, 90, 90), width=1)

    matrix_canvas.save(output_path, "PNG", quality=95)
    return output_path


if __name__ == "__main__":
    # Ujian lokal pantas
    test_strips = [
        "assets/characters/tuah_strip.png",
        "assets/characters/oyen_strip.png"
    ]
    generated = build_character_matrix(test_strips)
    print(f"Matrix berjaya dijana di: {generated}")