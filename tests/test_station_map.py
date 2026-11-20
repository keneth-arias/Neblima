import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]


class StationLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.locations: list[tuple[str, float, float]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        fields = dict(attrs)
        station = fields.get("data-station")
        if tag == "a" and station:
            url = urlsplit(fields["href"] or "")
            assert url.hostname == "www.openstreetmap.org"
            query = parse_qs(url.query)
            self.locations.append((station, float(query["mlat"][0]), float(query["mlon"][0])))


def test_map_uses_all_seven_source_locations() -> None:
    config = yaml.safe_load((ROOT / "configs/weather-alignment.yaml").read_text())
    expected = [(row["name"], row["latitude"], row["longitude"]) for row in config["stations"]]
    links = StationLinks()
    links.feed((ROOT / "web/estaciones.html").read_text())
    assert len(links.locations) == 7
    assert sorted(links.locations) == sorted(expected)


def test_readme_map_matches_station_locations() -> None:
    readme = (ROOT / "README.md").read_text()
    block = re.search(r"^```geojson\n(.*?)\n```$", readme, re.MULTILINE | re.DOTALL)
    assert block is not None
    data = json.loads(block[1])
    assert data["type"] == "FeatureCollection"
    links = StationLinks()
    links.feed((ROOT / "web/estaciones.html").read_text())
    locations = []
    for feature in data["features"]:
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "Point"
        assert feature["properties"]["Estación"]
        longitude, latitude = feature["geometry"]["coordinates"]
        locations.append((feature["id"], latitude, longitude))
    assert sorted(locations) == sorted(links.locations)
