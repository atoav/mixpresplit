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



# Not implemented yet
FLAGS = [
    "-n/--no-overwrite",
    "-y/--overwrite",
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


scene_pattern    = re.compile(r"sSCENE=(.*?)\s")
take_pattern     = re.compile(r"sTAKE=(.*?)\s")
tape_pattern     = re.compile(r"sTAPE=(.*?)\s")
circled_pattern  = re.compile(r"sCIRCLED=(.*?)\s")
speed_pattern    = re.compile(r"sSPEED=(.*?)\s")


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


def split(meta, outpath):
    # Expand the output
    outpath = expand_outpath(outpath, meta)



    # Construct channel mapping and filenames for output
    outfiles = [(i, "{}-{:03d}.{}-{}.WAV".format(meta.scene, meta.take, i, t.replace(" ", "_"))) for i, t in meta.tracks.items()]

    # If no Stereo Master is recorded first channel would be at index 3
    # correct this offset by subtracting this
    smallest = min(meta.tracks.keys())
    
    # Add -map [FL] /my/path/SceneName-001.1-Trackname.WAV:
    for i, outfile  in outfiles:

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
        
        # expand the Outpath per Track
        patched_outpath = expand_outpath(outpath, meta, i)

        # Add extension if there is none
        if not patched_outpath.lower().endswith(".wav"):
            patched_outpath = "{}.wav".format(patched_outpath)
        
        # Create Outpath if it doesn't exist
        if not os.path.isdir(patched_outpath):
            os.makedirs(os.path.dirname(patched_outpath), exist_ok=True)
        cmd.append(patched_outpath)
        print("    [{}] -> {}".format(channel, patched_outpath))

        cmd.append("-hide_banner") 
        cmd.append("-loglevel")
        cmd.append("error")

        subprocess.check_output(cmd)

def main():
    if len(sys.argv) <= 2:
        print("============================ MIXPRESPLIT ================================")
        print("This is a CLI-Utility that helps splitting polyWav files that are made")
        print("by a Sounddevices MixPre Recorder.")
        print()
        print("This is (for now) more useful than the existing solution by Sounddevices")
        print("because it can handle 32 Bit recordings properly and can create output")
        print("directories based on the metadata.")
        print()
        print("Usage:")
        print("    mixpre [INPUTDIRECTORY ...] [OUTPATH]")
        print()
        print("You can insert the following variables in the path OUTPATH:")
        print("          {date} . . . . Date of the recording (e.g. 2020-06-01)")
        print("          {hour} . . . . Hour of the recording (e.g. 19)")
        print("           {min} . . . . Minute of the recording (e.g. 20)")
        print("           {sec} . . . . Second of the recording (e.g. 24)")
        print("         {scene} . . . . Scene name (e.g. MixPre)")
        print("          {take} . . . . Take Number (e.g. 001)")
        print("          {tape} . . . . Identifier for the Tape/SD-Card")
        print("       {circled} . . . . Circled Files (e.g. CIRCLED)")
        print("   {tracknumber} . . . . Number of the track (e.g. 001)")
        print("     {trackname} . . . . Name of the track as chosen on the recorder")
        print()

    else:
        # The first sys.argv is the name of the script itself, so ignore it
        args    = sys.argv[1:]
        front  = " ".join(list(set(args[:-1])))
        outpath  = args[-1]

        args = shlex.split(front)
        options = {k: True if v.startswith('-') else v
           for k,v in zip(args, args[1:]+["--"]) if k.startswith('-')}

        print("Options: {}".format(options))
        print("outpath: {}".format(outpath))
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
        
        # Split the polywavs
        for meta in metas:
            print("\n{} (Take [{}/{}] from {}): Splitting {} ({} channels, Duration: {}) ...".format(meta.scene, meta.take, total_takes, meta.datestring, meta.filename, len(meta.tracks.keys()), meta.duration))
            split(meta, outpath)


if __name__ == "__main__":
    main()