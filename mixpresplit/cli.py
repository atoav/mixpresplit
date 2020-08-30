#!/usr/bin/env python 
#-*- coding: utf-8 -*-

import sys
import os, re, struct
import datetime
import platform
import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections import OrderedDict
from wavinfo import WavInfoReader
import click


# Allow also -h to get help
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

# Filter patterns
filter_take_pattern       = re.compile(r'(!?\d-\d|!?\d|!?[A-z0-9-_]+)')
filter_take_pattern_digit = re.compile(r'^(!?\d)$')
filter_take_pattern_range = re.compile(r'^(!?\d-\d)$')
filter_take_pattern_word  = re.compile(r'^(!?[A-z0-9-_]+)$')
filter_track_pattern       = re.compile(r'(!?\d-\d|!?\d|!?[A-z0-9-_]+)')
filter_track_pattern_digit = re.compile(r'^(!?\d)$')
filter_track_pattern_range = re.compile(r'^(!?\d-\d)$')
filter_track_pattern_word  = re.compile(r'^(!?[A-z0-9-_]+)$')




class Metadata():
    def __init__(self)  -> "Metadata":
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

    def set_filepath(self, filepath: str):
        self.filepath = filepath
        return self

    @property
    def filename(self) -> str:
        if self.filepath is None:
            return ""
        else:
            return os.path.basename(self.filepath)

    @property
    def directory(self) -> str:
        if self.filepath is None:
            return ""
        else:
            return os.path.dirname(self.filepath)

    @property
    def total_seconds(self) -> float:
        if self.samplecount is None:
            return False
        else:
            return self.samplecount / self.samplerate

    @property
    def duration(self) -> datetime.timedelta:
        return datetime.timedelta(seconds=self.total_seconds)

    def set_datestring(self, datestring: str) -> str:
        self.datestring = datestring
        return self

    def set_timestring(self, timestring: str) -> str:
        self.timestring = timestring
        return self

    def set_codec(self, bitrate: int) -> "Metadata":
        if bitrate == 32:
            self.codec = "pcm_f32le"
        elif bitrate == 24:
            self.codec = "pcm_s24le"
        elif bitrate == 16:
            # V Didn't check this, just a wild guess..
            self.codec = "pcm_s16le"
        return self

    def set_samplerate(self, samplerate: int) -> "Metadata":
        self.samplerate = int(samplerate)
        return self

    def set_channels(self, channels: int) -> "Metadata":
        self.channels = int(channels)
        return self

    def set_scene(self, scene: str) -> "Metadata":
        self.scene = scene
        return self

    def set_take(self, take: int) -> "Metadata":
        self.take = int(take)
        return self

    def set_tape(self, tape: str) -> "Metadata":
        self.tape = tape
        return self

    def set_circled(self, circled: bool) -> "Metadata":
        self.circled = bool(circled)
        return self

    def set_speed(self, speed: str) -> "Metadata":
        self.speed = speed
        return self

    def set_samplecount(self, samplecount: int) -> "Metadata":
        self.samplecount = int(samplecount)
        return self

    def add_track(self, tracknumber: int, trackname: str) -> "Metadata":
        if not tracknumber in self.tracks:
            self.tracks[tracknumber] = trackname
        return self

    def __str__(self) -> str:
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



def read_metadata(path: str) -> "Metadata":
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

    # Always subtract 2 from regular (non-mixdown) channelnumbers to match the device channels
    index_offset = 2
    used_indices = []

    # Process the regular Channels first (excluding downmixes)
    for track in metadata.ixml.track_list:
        if not track.name in ["MixL", "MixR"]:
            index = int(track.channel_index) - index_offset
            meta.add_track(index, track.name)
            used_indices.append(index)

    # Add Mix Tracks last (to avoid messing with the channel numbers)
    for track in metadata.ixml.track_list:
        if track.name in ["MixL", "MixR"]:
            if track.name == "MixL":
                index = 9
            else:
                index = 10
            meta.add_track(index, track.name)
            used_indices.append(index)

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


def process_files(meta: "Metadata", outpath: str, options: dict) -> [str]:
    # Expand the output
    outpath = expand_outpath(outpath, meta)

    # Construct channel mapping and filenames for output
    outfiles = [(i, trackname) for i, trackname in meta.tracks.items()]

    # If no Stereo Master is recorded first channel would be at index 3
    # correct this offset by subtracting this
    smallest = min(meta.tracks.keys())

    # List of paths written to
    written_to = []
    
    # Add -map [FL] /my/path/SceneName-001.1-Trackname.WAV:
    for i, trackname  in outfiles:

        # Get the input codec as a default
        output_codec = meta.codec
        file_extension = ".wav"

        # Override input codec if options are present
        if options["flac"]:
            output_codec = "flac"
            file_extension = ".flac"

        # Construct basic command
        cmd = [
            "ffmpeg",
            "-i", meta.filepath,
            "-c:a", meta.codec, # <-- input codec, output codec below!
        ]

        # Which channel shall be used
        channel = i-smallest
        cmd.append("-af")
        cmd.append("pan=1|c0=c{}".format(channel))

        # Which Codec shall be used
        cmd.append("-c:a")
        cmd.append(output_codec) # <-- output codec

        # Convert to 24 or 16 bit if demanded
        if options["24"]:
            cmd.append("-sample_fmt")
            cmd.append("s24")
        elif options["16"]:
            cmd.append("-sample_fmt")
            cmd.append("s16")

        # Skip loop to end if track is filtered
        if not filter_tracks(i, trackname, options):
            continue
        
        # expand the Outpath per Track
        patched_outpath = expand_outpath(outpath, meta, i)

        # For each --replace foo use the according --with bar
        for i, r in enumerate(options["replace"]):
            patched_outpath = patched_outpath.replace(r, options["with"][i])

        # Add extension if there is none
        if not patched_outpath.lower().endswith(file_extension):
            patched_outpath = "{}{}".format(patched_outpath, file_extension)
        
        # Create Outpath if it doesn't exist
        if not os.path.isdir(patched_outpath) and not options["dry-run"]:
            os.makedirs(os.path.dirname(patched_outpath), exist_ok=True)
        cmd.append(patched_outpath)
        

        # Set overwrite option in ffmpeg if flag is found
        if options["overwrite"]:
            cmd.append("-y") 

        # Hide ffmpeg output
        cmd.append("-hide_banner") 
        cmd.append("-loglevel")
        cmd.append("error")

        if not options["dry-run"]:
            subprocess.check_output(cmd)
            print("    [{}] -> {}".format(channel, patched_outpath))
            written_to.append(patched_outpath)
        else:
            print("    [{}] -> {} (Dry Run)".format(channel, patched_outpath))

    return written_to


def filter_tracks(tracknumber: int, trackname: str, options: dict) -> bool:
    """
    Filter out tracks 
    """

    # Parse all filters for include tracks
    if options["tracks"] is not None:
        matches = re.findall(filter_track_pattern, options["tracks"])
    else:
        # If there is no filter, just use it
        return True

    included = False
    # First exclude
    for match in matches:
        # True if match starts with ! and replace it if it exists
        invert = match.startswith("!")
        match = match[:1].replace('!', '') + match[1:]
        # Match for ranges like 1-3
        if re.match(filter_track_pattern_range, match):
            start, end = [int(i) for i in match.split("-")]
            if tracknumber in range(start, end+1):
                included = included or True
        # Match for single digit
        elif re.match(filter_track_pattern_digit, match):
            if tracknumber == int(match):
                included = included or True
        # Match for strings
        elif re.match(filter_track_pattern_word, match):
            if match.lower() == "all":
                included = included or True
            elif match.lower() == "mixdown":
                if "Mix.L" in trackname or "Mix.R" in trackname:
                    included = included or True
            elif match in trackname:
                included = included or True

        # XOR the two bools "included" and "inverted":
        # Included
        # |  Invert
        # |   |     XOR
        # 0   0   =  0         
        # 0   1   =  1         
        # 1   0   =  1         
        # 1   1   =  0     
        included = included != invert
    
    return included


def filter_takes(metas: ["Metadata"], options: dict) -> ["Metadata"]:
    """
    Filter out takes 
    """

    # Parse all filters for include takes
    if options["takes"] is not None:
        # Extract patterns from the user input
        matches = re.findall(filter_take_pattern, options["takes"])
    else:
        # No filter has been defined, return all
        return metas

    # Iterate all incoming takes and keep the ones we selected
    filtered_metas = []
    for meta in metas:
        included = False
        # Go through each match of the user input
        for match in matches:
            # True if match starts with ! and replace it if it exists
            invert = match.startswith("!")
            match = match[:1].replace('!', '') + match[1:]
            # Match for ranges like 1-3
            if re.match(filter_take_pattern_range, match):
                start, end = [int(i) for i in match.split("-")]
                if meta.take in range(start, end+1):
                    included = included or True
            # Match for single digit
            if re.match(filter_take_pattern_digit, match):
                if meta.take == int(match):
                    included = included or True
            # Match for strings
            if re.match(filter_take_pattern_word, match):
                if match.lower() == "all":
                    included = included or True

            # XOR the two bools "included" and "inverted" and append it to the list
            # Included
            # |  Invert
            # |   |     XOR
            # 0   0   =  0         
            # 0   1   =  1         
            # 1   0   =  1         
            # 1   1   =  0     
            included = included != invert

        # Use this take if anything matched
        if included:
            filtered_metas.append(meta)

    # Print out the ignored takes
    for meta in set(metas).difference(set(filtered_metas)):
        print("Ignoring Take {} ({})".format(meta.take, meta.duration))

    return filtered_metas


def find_common_dir(filepaths: [str], depth: int =5) -> str:
    """
    Find a common path in a bunch of paths, bound by depth
    Return first path if the number of iterations is exceeded
    """
    common_paths = [None, None]
    iterations = 0
    while len(common_paths) > 1:
        common_paths = set()
        for p in filepaths:
            common_paths.add(os.path.dirname(p))
        filepaths = list(common_paths)
        iterations += 1
        # If a common path is not found after a number of iterations return first
        if iterations >= depth:
            return list(common_paths)[0]
    return list(common_paths)[0]



def open_filebrowser(written_to: [str]) -> None:
    """
    Opens a system specific filebrowser at a folder that makes sense
    """
    # Find the biggest common path
    directory = find_common_dir(written_to)
    # Open system specific browser
    if platform.system() == "Windows":
        os.startfile(directory)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", directory])
    else:
        subprocess.Popen(["xdg-open", directory])



@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('inpaths', nargs=-1)
@click.argument('outpath', nargs=1)
@click.option('--overwrite/-y', is_flag=True, help="Overwrite existing files without asking")
@click.option('--only-circled', is_flag=True, help="Use only circled takes")
@click.option('--replace', multiple=True, help="Replace this string in OUTPATH")
@click.option('--with', 'with_', multiple=True, help="With that string")
@click.option('--dry-run', is_flag=True, help="Don't write, just print")
@click.option('--tracks', help="Only use these tracks (see section \"Filters\")")
@click.option('--takes', help="Only use these takes (see section \"Filters\")")
@click.option('--open', 'open_', is_flag=True, help="Open destination folder afterwards")
@click.option('--flac', is_flag=True, help="Use FLAC instead of WAV for output")
@click.option('--24', "bit24", is_flag=True, help="Output as 24 bit audio")
@click.option('--16', "bit16", is_flag=True, help="Output as 16 bit audio")
def main(inpaths, outpath, overwrite, only_circled, replace, with_, dry_run, open_, flac, bit24, bit16, tracks, takes):
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
        You can use Filters to exclude/include:
        'all'  . . . . . . all files
        'mixdown'  . . . . the mixdown tracks
        '4'  . . . . . . . a single track/take
        '4,6'  . . . . . . a list of tracks/take
        '4-8'  . . . . . . a range of tracks/take
        'foo'  . . . . . . anything with "foo" in the track name
        '!foo' . . . . . . anything not containing "foo"
    """

    options = {
        "overwrite" : overwrite,
        "only-circled" : only_circled,
        "replace" : replace,
        "with" : with_,
        "dry-run" : dry_run,
        "tracks" : tracks,
        "takes" : takes,
        "open" : open_,
        "flac" : flac,
        "24" : bit24,
        "16" : bit16
    }


    # Check if there is a equal number of replace and with options, warn and exit if not
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

    # Filter by takes
    metas = filter_takes(metas, options)

    # Display the number of total takes and length
    total_takes = len(metas)
    total_duration = datetime.timedelta(seconds=sum([d.total_seconds for d in metas]))
    print("Processing {} take(s) with a total duration of {}".format(total_takes, total_duration))

    # Export only circled takes
    if options["only-circled"]:
        metas = [m for m in metas if m.circled]

    # Stores the paths that are beeing written to
    written_to = []
    
    # Split the polywavs
    for meta in metas:
        print("\n{} (Take [{}/{}] from {}): Splitting {} ({} channels, Duration: {}) ...".format(meta.scene, meta.take, total_takes, meta.datestring, meta.filename, len(meta.tracks.keys()), meta.duration))
        written_to_for_meta = process_files(meta, outpath, options)
        for p in written_to_for_meta:
            written_to.append(p)

    if options["open"]:
        if not options["dry-run"]:
            open_filebrowser(written_to)
        else:
            print("Note: Didn't open filebrowser because no files have been written (dry-run)")




if __name__ == "__main__":
    main()