#!/usr/bin/env python 
#-*- coding: utf-8 -*-

import sys
import os, re, struct
import datetime
import shlex
import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections import OrderedDict
from wavinfo import WavInfoReader
import click

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

scene_pattern    = re.compile(r"sSCENE=(.*?)\s")
take_pattern     = re.compile(r"sTAKE=(.*?)\s")
tape_pattern     = re.compile(r"sTAPE=(.*?)\s")
circled_pattern  = re.compile(r"sCIRCLED=(.*?)\s")
speed_pattern    = re.compile(r"sSPEED=(.*?)\s")

# Filter patterns
filter_take_pattern       = re.compile(r'(\d-\d|\d|.+)')
filter_take_pattern_digit = re.compile(r'^(\d)$')
filter_take_pattern_range = re.compile(r'^(\d-\d)$')
filter_take_pattern_word  = re.compile(r'^(.+)$')


FMT = [
    "",
    "PCM",
    ""
    "float",
    "",
    "",
    "aLaw",
    "muLaw"
]


class Metadata():
    def __init__(self):
        self.filepath = None
        self.datestring = None
        self.timestring = None
        self.codec = None
        self.samplerate = None
        self.channels = None
        self.scene = None
        self.take = None
        self.tape = None
        self.circled = None
        self.speed = None
        self.samplecount = None
        self.tracks = OrderedDict()

    def set_filepath(self, filepath):
        self.filepath = filepath
        return self

    @property
    def filename(self):
        if self.filepath is None:
            return ""
        else:
            return os.path.basename(self.filepath)

    @property
    def directory(self):
        if self.filepath is None:
            return ""
        else:
            return os.path.dirname(self.filepath)

    @property
    def total_seconds(self):
        if self.samplecount is None:
            return False
        else:
            return self.samplecount / self.samplerate

    @property
    def duration(self):
        return datetime.timedelta(seconds=self.total_seconds)

    def set_datestring(self, datestring):
        self.datestring = datestring
        return self

    def set_timestring(self, timestring):
        self.timestring = timestring
        return self

    def set_codec(self, bitrate):
        if bitrate == 32:
            self.codec = "pcm_f32le"
        elif bitrate == 24:
            self.codec = "pcm_s24le"
        elif bitrate == 16:
            # V Didn't check this, just a wild guess..
            self.codec = "pcm_s16le"
        return self

    def set_samplerate(self, samplerate):
        self.samplerate = int(samplerate)
        return self

    def set_channels(self, channels):
        self.channels = int(channels)
        return self

    def set_scene(self, scene):
        self.scene = scene
        return self

    def set_take(self, take):
        self.take = int(take)
        return self

    def set_tape(self, tape):
        self.tape = tape
        return self

    def set_circled(self, circled):
        self.circled = circled == "TRUE"
        return self

    def set_speed(self, speed):
        self.speed = speed
        return self

    def set_samplecount(self, samplecount):
        self.samplecount = int(samplecount)
        return self

    def add_track(self, tracknumber: int, trackname: str):
        if not tracknumber in self.tracks:
            self.tracks[tracknumber] = trackname
            info = WavInfoReader(self.filepath.replace("\\", "/"))
            info.ixml.track_list
        return self

    def __str__(self):
        lines = []
        lines.append("Metadata():")
        lines.append("   filepath:   {}".format(self.filepath))
        lines.append("   filename:   {}".format(self.filename))
        lines.append("   samplerate: {}".format(self.samplerate))
        lines.append("   codec:      {}".format(self.codec))
        lines.append("   channels:   {}".format(self.channels))
        lines.append(" datestring:   {}".format(self.datestring))
        lines.append(" timestring:   {}".format(self.timestring))
        lines.append("   scene:      {}".format(self.scene))
        lines.append("   take:       {}".format(self.take))
        lines.append("   tape:       {}".format(self.tape))
        lines.append("   circled:    {}".format(self.circled))
        lines.append("   speed:      {}".format(self.speed))
        lines.append("   totalseconds:      {}".format(self.total_seconds))
        lines.append("       duration:      {}".format(self.duration))
        lines.append("   Tracks:")

        for i, track in self.tracks.items():
            print("Track:         [{}] {}".format(i, track))
            lines.append("        [{}] {}".format(i, track))

        return "\n".join(lines)



def read_metadata(path: str):
    metadata = WavInfoReader(path)

    meta = Metadata()
    meta.set_filepath(path)
    meta.set_timestring(metadata.bext.originator_time)
    meta.set_datestring(metadata.bext.originator_date)
    meta.set_codec(metadata.fmt.bits_per_sample)
    meta.set_samplerate(metadata.fmt.sample_rate)
    meta.set_channels(metadata.fmt.channel_count)
    meta.set_scene(metadata.ixml.scene)
    meta.set_take(metadata.ixml.take)
    meta.set_tape(metadata.ixml.tape)
    meta.set_speed([l.split("=")[1] for l in metadata.bext.description.split("\r\n") if l.startswith("sSPEED")][0])
    meta.set_circled([l.split("=")[1]=="TRUE" for l in metadata.bext.description.split("\r\n") if l.startswith("sCIRCLED")][0])
    meta.set_samplecount(metadata.data.frame_count)

    for track in metadata.ixml.track_list:
        meta.add_track(int(track.interleave_index), track.name)

    return meta



def get_wavs_files(inpath: str) -> [str]:
    return [os.path.join(inpath, f) for f in os.listdir(inpath) if f.lower().endswith(".wav")]


def expand_outpath(outpath: str , meta: dict, channel: int=0) -> str:
    outpath = outpath.replace("{date}", meta.datestring)
    outpath = outpath.replace("{hour}", meta.timestring.split(":")[0])
    outpath = outpath.replace("{h}", meta.timestring.split(":")[0])
    outpath = outpath.replace("{min}", meta.timestring.split(":")[1])
    outpath = outpath.replace("{m}", meta.timestring.split(":")[1])
    outpath = outpath.replace("{sec}", meta.timestring.split(":")[2])
    outpath = outpath.replace("{s}", meta.timestring.split(":")[2])
    outpath = outpath.replace("{scene}", meta.scene)
    outpath = outpath.replace("{take}", str(meta.take))
    outpath = outpath.replace("{tape}", meta.tape)
    if channel != 0:
        outpath = outpath.replace("{tracknumber}", str(channel))
        outpath = outpath.replace("{n}", str(channel))
        outpath = outpath.replace("{trackname}", meta.tracks[channel])
    if meta.circled:
        outpath = outpath.replace("{circled}", "CIRCLED")
    return outpath


def split(meta, outpath, options):
    # Expand the output
    outpath = expand_outpath(outpath, meta)

    # Construct channel mapping and filenames for output
    outfiles = [(i, trackname) for i, trackname in meta.tracks.items()]

    # If no Stereo Master is recorded first channel would be at index 3
    # correct this offset by subtracting this
    smallest = min(meta.tracks.keys())
    
    # Add -map [FL] /my/path/SceneName-001.1-Trackname.WAV:
    for i, trackname  in outfiles:

        # Construct basic command
        cmd = [
            "ffmpeg",
            "-i", meta.filepath,
            "-c:a", meta.codec,
        ]

        # Which channel shall be used
        channel = i-smallest
        cmd.append("-af")
        cmd.append("pan=1|c0=c{}".format(channel))

        # Which Codec shall be used
        cmd.append("-c:a")
        cmd.append(meta.codec)

        included = False

        # Functionality to include tracks
        if options["include-tracks"] is not None:
            include_track_matches = re.findall(filter_take_pattern, options["include-tracks"])
            
            include_track_numbers = []
            if len(include_track_matches) > 0:
                for match in include_track_matches:
                    if re.match(filter_take_pattern_range, match):
                        start, end = [int(i) for i in match.split("-")]
                        for t in range(start, end+1):
                            include_track_numbers.append(t)
                    if re.match(filter_take_pattern_word, match):
                        if match in trackname:
                            include_track_numbers.append(i)
                    if re.match(filter_take_pattern_digit, match):
                        include_track_numbers.append(int(match))
            if i in include_track_numbers:
                included = True

        if not included and options["ignore-tracks"] is not None:
            # Functionality to ignore tracks
            ignore_track_matches = re.findall(filter_take_pattern, options["ignore-tracks"])

            ignore_track_numbers = []
            if len(ignore_track_matches) > 0:
                for match in ignore_track_matches:
                    if re.match(filter_take_pattern_range, match):
                        start, end = [int(i) for i in match.split("-")]
                        for t in range(start, end+1):
                            ignore_track_numbers.append(t)
                    if re.match(filter_take_pattern_word, match):
                        if match in trackname:
                            ignore_track_numbers.append(i)
                    if re.match(filter_take_pattern_digit, match):
                        ignore_track_numbers.append(int(match))
            if i in ignore_track_numbers:
                continue
        
        # expand the Outpath per Track
        patched_outpath = expand_outpath(outpath, meta, i)

        # For each --replace foo use the according --with bar
        for i, r in enumerate(options["replace"]):
            patched_outpath = patched_outpath.replace(r, options["with"][i])

        # Add extension if there is none
        if not patched_outpath.lower().endswith(".wav"):
            patched_outpath = "{}.wav".format(patched_outpath)
        
        # Create Outpath if it doesn't exist
        if not os.path.isdir(patched_outpath) and not options["dry-run"]:
            os.makedirs(os.path.dirname(patched_outpath), exist_ok=True)
        cmd.append(patched_outpath)
        

        # Set overwrite option in ffmpeg if flag is found
        if options["overwrite"]:
            cmd.append("-y") 

        cmd.append("-hide_banner") 
        cmd.append("-loglevel")
        cmd.append("error")

        if not options["dry-run"]:
            subprocess.check_output(cmd)
            print("    [{}] -> {}".format(channel, patched_outpath))
        else:
            print("    [{}] -> {} (Dry Run)".format(channel, patched_outpath))


# Not implemented yet
FLAGS = [
    "--ignore-mixdown",
    "--only-circled",
    "--flac",
    "--32",
    "--24",
    "--16",
    "-d/--dry-run",
    "-open-destination"
]

# Not implemented yet
OPTIONS = [
    "-f/--filename",
    "-t/--takes",    # Include takes from till
    "-x/--ignore",   # Ignore takes from till
    "-s/--scene"     # Override Scenename
    "-c/--channel"   # Override Channel Name
]


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('inpaths', nargs=-1)
@click.argument('outpath', nargs=1)
@click.option('--overwrite/-y', is_flag=True, help="Overwrite existing files without asking")
@click.option('--only-circled', is_flag=True, help="Use only circled takes")
@click.option('--replace', multiple=True, help="Replace this string in OUTPATH")
@click.option('--with', 'with_', multiple=True, help="With that string")
@click.option('--dry-run/-d', is_flag=True, help="Don't write, just print")
@click.option('--ignore-tracks', help="Ignore certain tracks (see section \"Filters\"")
@click.option('--include-tracks', help="Include certain tracks (see section \"Filters\"")
def main(inpaths, outpath, overwrite, only_circled, replace, with_, dry_run, ignore_tracks, include_tracks):
    """
        ============================ MIXPRESPLIT ================================
        This is a CLI-Utility that helps splitting polyWav files that are made by a Sounddevices MixPre Recorder.
       
        This is (for now) more useful than the existing solution by Sounddevices because it can handle 32 Bit recordings properly and can create output directories based on the metadata. Make sure you have ffmpeg installed : )
        
        \b
        You can insert the following variables in the path OUTPATH:
        {date} . . . . . Date of the recording (e.g. 2020-06-01)
        {hour} . . . . . Hour of the recording (e.g. 19)
        {min}  . . . . . Minute of the recording (e.g. 20)
        {sec}  . . . . . Second of the recording (e.g. 24)
        {scene}  . . . . Scene name (e.g. MixPre)
        {take} . . . . . Take Number (e.g. 001)
        {tape} . . . . . Identifier for the Tape/SD-Card
        {circled}  . . . Circled Files (e.g. CIRCLED)
        {tracknumber}. . Number of the track (e.g. 001)
        {trackname}. . . Name of the track as chosen on the recorder

        \b
        You can use Filters to ignore/include:
        all  . . . . . . all files
        mixdown  . . . . the mixdown tracks
        4  . . . . . . . a single track
        4,6  . . . . . . a list of tracks
        4-8  . . . . . . a range of tracks
        "foo"  . . . . . anything with "foo" in the track name
    """

    options = {
        "overwrite" : overwrite,
        "only-circled" : only_circled,
        "replace" : replace,
        "with" : with_,
        "dry-run" : dry_run,
        "ignore-tracks" : ignore_tracks,
        "include-tracks" : include_tracks
    }

    if len(options["replace"]) != len(options["with"]):
        print("Error:    You wrote {} \"--replace\" and {} \"--with\" options!".format(len(options["replace"]), len(options["with"])))
        print("Solution: Use a \"--with\" option for each \"--replace\" option (same count)")
        exit()
    
    # Get a flat list of wavfiles from all inpaths
    infiles = []
    for inpath in inpaths:
        wavs = get_wavs_files(inpath)
        for wav in wavs:
            infiles.append(wav)

    # Read the track metadata
    metas = [read_metadata(i) for i in infiles]
    total_takes = len(metas)
    total_duration = datetime.timedelta(seconds=sum([d.total_seconds for d in metas]))
    print("Processing {} take(s) with a total duration of {}".format(total_takes, total_duration))

    # Export only circled takes
    if options["only-circled"]:
        metas = [m for m in metas if m.circled]
    
    # Split the polywavs
    for meta in metas:
        print("\n{} (Take [{}/{}] from {}): Splitting {} ({} channels, Duration: {}) ...".format(meta.scene, meta.take, total_takes, meta.datestring, meta.filename, len(meta.tracks.keys()), meta.duration))
        split(meta, outpath, options)




if __name__ == "__main__":
    main()