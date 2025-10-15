import pyvips
from pathlib import Path

def generate_iiif_tiles(source_path, output_dir, tile_size=512):
    image = pyvips.Image.new_from_file(source_path)
    base_name = Path(source_path).stem

    output_path = Path(output_dir) / base_name
    output_path.mkdir(parents=True, exist_ok=True)

    image.dzsave(
        str(output_path / base_name),
        tile_size=tile_size,
        overlap=0,
        suffix=".jpg",
        depth="onetile"  # or "onetile" / "onepixel" / "onetile"
    )

    # Return metadata for manifest generation
    return {
        "id": base_name,
        "width": image.width,
        "height": image.height,
        "tile_size": tile_size,
        "output_dir": str(output_path)
    }

# Example usage
meta = generate_iiif_tiles("sample.tif", "output_tiles")
print(meta)
