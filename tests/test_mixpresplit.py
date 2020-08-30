import traceback
import pytest
import click
from click.testing import CliRunner
import re
import mixpresplit
from mixpresplit.cli import *

TRACK_PATTERN = re.compile(r"\[(?P<number>\d)\] -> \.\./(?P<scene>[A-z0-9 _-]+)-(?P<take>\d+?)\.(?P<tracknumber>\d+?)_(?P<trackname>[A-z0-9_ -]+?)\.wav")

MASTERLENGTHS = {
    "L&R" : 2,
    "L" : 1,
    "R" : 1,
    "L&R Linked" : 2,
    "Off" : 0,
    "Off & Linked": 0
}



@pytest.fixture(scope="module")
def runner():
    return CliRunner()


def test_version():
    assert mixpresplit.__version__ == '0.1.1'


def load_samples():
    with open("./testsamples/readme.md", "r") as f:
        x = [[p.strip() for p in x.split("|")[1:-1]] for x in f.readlines()[2:]]
        x = [
          {
            "name": p[0].rsplit("/")[-1].strip(),
            "path": "{}.wav".format(p[0]),
            "tracks": [int(i) for i in p[1].split(",") if i != ""],
            "master": p[2],
            "sample_rate": p[3],
            "bitrate" : int(p[4])
          }
          for p in x if len(p) != 0
        ]
    return x


def test_basic(runner):
    """
    Test if mixpresplit -h returns without error
    """
    result = runner.invoke(main, ["-h"])
    print(result.output)
    if result.exception:
        traceback.print_exception(*result.exc_info)
    assert result.exit_code == 0


def test_channels(runner):
    """
    Test if all files map correctly to the corresponding channels
    """
    sample_descriptions = load_samples()
    sample_descriptions = [s for s in sample_descriptions if s["path"].startswith("channeltests")]
    input_directory = "./testsamples/channeltests"
    result = runner.invoke(main, ["--dry-run", input_directory, "../{scene}-{take}.{tracknumber}_{trackname}"])
    samples = [l.strip() for l in result.output.split("\nTestsample ") if l != ""][2:]
    samples = [
        {   
            "name":  l.split("\n")[0].split("Splitting")[1].split(" (")[0].split(".WAV")[0].strip(),
            "tracks": [
                re.match(TRACK_PATTERN, t.strip()).groupdict() for t in l.split("\n")[1:]
                ]
        } for l in samples
    ]
    
    for s in samples:
        # Find fitting sample_description
        matching_description = [d for d in sample_descriptions if d["name"].lower() == s["name"].lower()][0]
        expected_tracks = [t for t in matching_description["tracks"]]
        for t in range(0, MASTERLENGTHS[matching_description["master"]]):
            if matching_description["master"] == "R":
                expected_tracks.append(10)
            else:
                expected_tracks.append(9+t)
        existing_tracks = [int(t["tracknumber"]) for t in s["tracks"]]
        expected_tracks.sort()
        # If there would be an error print this first
        if not set(existing_tracks) == set(expected_tracks):
            print("Track: {} ({})".format(s["name"], matching_description["master"]))
            print("  Existing: {}".format(existing_tracks))
            print("            {}".format(", ".join([t["trackname"] for t in s["tracks"]])))
            print("  Expected: {}".format(expected_tracks))
            print()
        assert set(existing_tracks) == set(expected_tracks)

    if result.exception:
        traceback.print_exception(*result.exc_info)
    assert result.exit_code == 0
