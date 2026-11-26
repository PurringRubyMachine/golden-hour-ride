"""Photos of the ground from above: turned onto the terrain square as ground.jpg, through a build (no network)."""

import json
import shlex
import warnings

import numpy as np
import pytest
import rasterio
from conftest import E0, N0, UTM, write_dtm
from pyproj import Transformer
from rasterio.transform import from_origin

from tools.coursebuilder import BuildError
from tools.coursebuilder.build import build
from tools.coursebuilder.imagery import CEILING, FLOOR, even_colours, pixels_for
from tools.coursebuilder.validate import validate_folder

QUIET = dict(log=lambda *_: None)
CREDIT = dict(imagery_credit="Ground from above: a test photo", imagery_licence="CC0-1.0")


def write_photo(path, crs, west, north, res, n, colour):
    """An n × n RGB GeoTIFF; colour(easting, northing) in UTM gives each pixel's [r, g, b] (0 for no data)."""
    cols, rows = np.meshgrid(np.arange(n) + 0.5, np.arange(n) + 0.5)
    x, y = west + cols * res, north - rows * res
    if crs != UTM:
        x, y = Transformer.from_crs(crs, UTM, always_xy=True).transform(x, y)
    rgb = np.clip(np.stack(colour(x, y)), 0, 255).astype("uint8")
    profile = dict(driver="GTiff", width=n, height=n, count=3, dtype="uint8", crs=crs, nodata=0)
    with rasterio.open(path, "w", transform=from_origin(west, north, res, res), **profile) as dst:
        dst.write(rgb)
    return str(path)


def gradient(x, y):
    """Redder to the east, greener to the north, blue flat."""
    return 60 + (x - E0) * 0.1, 60 + (y - N0) * 0.1, np.full_like(x, 90.0)


@pytest.fixture
def dtm(tmp_path):
    write_dtm(tmp_path / "dtm" / "plane.tif", UTM, E0 - 700, N0 + 700, 2, 700, 700)


def read_ground(folder):
    with warnings.catch_warnings():  # ground.jpg has no map position of its own: the course places it
        warnings.simplefilter("ignore", rasterio.errors.NotGeoreferencedWarning)
        with rasterio.open(folder / "ground.jpg") as src:
            return src.read().astype(float)


def test_size_is_a_power_of_two_near_four_metres():
    assert pixels_for(1000) == 256
    assert pixels_for(6200) == 2048  # Leckhampton: 3.0 m
    assert pixels_for(13400) == 4096  # Gatineau: 3.3 m
    assert pixels_for(40000) == 4096  # the most any chip is asked to load


def test_photo_in_another_coordinate_system_lands_north_up(options, tmp_path, dtm):
    # the photo is in the British National Grid, the course in UTM: it has to be turned to fit
    to_bng = Transformer.from_crs(UTM, "EPSG:27700", always_xy=True)
    bx, by = to_bng.transform(E0, N0)
    photo = write_photo(tmp_path / "photo.tif", "EPSG:27700", bx - 800, by + 800, 4, 400, gradient)
    out = build(options(imagery=[photo], **CREDIT), **QUIET)
    folder = tmp_path / "courses" / "test-loop"
    assert out["course"]["imagery"] == {"file": "ground.jpg", "size": 256}
    assert out["course"]["credits"][1] == {"text": "Ground from above: a test photo", "licence": "CC0-1.0"}
    g = read_ground(folder)
    assert g.shape == (3, 256, 256)
    assert g[0, :, 192:].mean() > g[0, :, :64].mean() + 40, "redder to the east (right)"
    assert g[1, :64, :].mean() > g[1, 192:, :].mean() + 40, "greener to the north (top)"
    assert validate_folder(folder) == []


def test_build_json_and_command_record_the_photos(options, tmp_path, dtm, monkeypatch):
    photo = write_photo(tmp_path / "photo.tif", UTM, E0 - 600, N0 + 600, 4, 300, gradient)
    with rasterio.open(photo, "r+") as dst:
        dst.update_tags(scenes="S2B_30UWC_20250701_0_L2A S2A_30UWC_20250712_0_L2A")
    monkeypatch.chdir(tmp_path)
    build(options(imagery=[photo], imagery_url="https://example.org/photos", **CREDIT), **QUIET)
    info = json.loads((tmp_path / "courses" / "test-loop" / "build.json").read_text())
    assert info["imagery"] == {
        "files": [{"file": "photo.tif", "scenes": ["S2B_30UWC_20250701_0_L2A", "S2A_30UWC_20250712_0_L2A"]}]
    }
    cmd = shlex.split(info["command"])
    assert cmd[cmd.index("--imagery") + 1] == "photo.tif"
    assert cmd[cmd.index("--imagery-licence") + 1] == "CC0-1.0"
    assert cmd[cmd.index("--imagery-url") + 1] == "https://example.org/photos"


def test_photos_need_a_credit(options, tmp_path, dtm):
    photo = write_photo(tmp_path / "photo.tif", UTM, E0 - 600, N0 + 600, 4, 300, gradient)
    with pytest.raises(BuildError, match="credit"):
        build(options(imagery=[photo]), **QUIET)


def test_rebuilding_without_a_photo_removes_it(options, tmp_path, dtm):
    photo = write_photo(tmp_path / "photo.tif", UTM, E0 - 600, N0 + 600, 4, 300, gradient)
    build(options(imagery=[photo], **CREDIT), **QUIET)
    out = build(options(), **QUIET)
    folder = tmp_path / "courses" / "test-loop"
    assert "imagery" not in out["course"]
    assert not (folder / "ground.jpg").exists()
    assert validate_folder(folder) == []


def test_a_gap_is_filled_with_the_average(options, tmp_path, dtm):
    # this photo stops at the middle of the square, going east
    photo = write_photo(
        tmp_path / "west.tif", UTM, E0 - 600, N0 + 600, 4, 150, lambda x, y: (x * 0 + 50, x * 0 + 150, x * 0 + 100)
    )
    logged = []
    build(options(imagery=[photo], **CREDIT), log=logged.append)
    assert any("isn't covered" in m for m in logged)
    g = read_ground(tmp_path / "courses" / "test-loop")
    east = g[:, :, 140:]
    assert east.std(axis=(1, 2)).max() < 3, "the uncovered part is one even colour"


def test_photo_somewhere_else_is_refused(options, tmp_path, dtm):
    photo = write_photo(tmp_path / "photo.tif", UTM, E0 + 50_000, N0, 4, 100, gradient)
    with pytest.raises(BuildError, match="don't cover"):
        build(options(imagery=[photo], **CREDIT), **QUIET)


def test_a_grey_photo_is_refused(options, tmp_path, dtm):
    path = tmp_path / "grey.tif"
    profile = dict(driver="GTiff", width=10, height=10, count=1, dtype="uint8", crs=UTM)
    with rasterio.open(path, "w", transform=from_origin(E0 - 600, N0 + 600, 120, 120), **profile) as dst:
        dst.write(np.full((1, 10, 10), 99, dtype="uint8"))
    with pytest.raises(BuildError, match="colour photo"):
        build(options(imagery=[str(path)], **CREDIT), **QUIET)


def test_brightness_is_stretched_and_colours_kept():
    rng = np.random.default_rng(1)
    # a dull, dark photo of forest: green above red and blue, everything in a narrow band
    rgb = np.stack([rng.uniform(30, 40, (64, 64)), rng.uniform(50, 60, (64, 64)), rng.uniform(25, 35, (64, 64))])
    empty = np.zeros((64, 64), dtype=bool)
    out = even_colours(rgb.astype("uint8"), empty).astype(float)
    assert out.min() <= FLOOR + 3 and out.max() >= CEILING - 3, "stretched to the range"
    r, g, b = out.mean(axis=(1, 2))
    assert g > r > b, "still green: the colours are stretched together"
    assert g - r > 40 and r - b > 10, "and further apart, as the brightness is (they were 20 and 5)"


def test_folder_reports_a_missing_photo(options, tmp_path, dtm):
    photo = write_photo(tmp_path / "photo.tif", UTM, E0 - 600, N0 + 600, 4, 300, gradient)
    build(options(imagery=[photo], **CREDIT), **QUIET)
    folder = tmp_path / "courses" / "test-loop"
    (folder / "ground.jpg").unlink()
    assert validate_folder(folder) == ["ground.jpg is missing"]
