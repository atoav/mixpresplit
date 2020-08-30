# mixpresplit

mixpresplit is a small but powerful commandline utility that allows you to split and sort polywavs (as produced by the Sounddevices MixPre recorder) into seperate audio files – one for each channel. Sounddevices offers there own graphical tool that does this called [Wave Agent](https://www.sounddevices.com/product/wave-agent-software/), which you should also check out. Wave Agent has the downside that it currently can't split 32bit files and that you cannot use it for automated or semi-automated workflows.

## About the project

mixpresplit is programmed in Python 3 and depends on the great [ffmpeg](https://ffmpeg.org/) project for all audio processing related stuff. That means you could - in principle – just use your own ffmpeg commands and get similar results. mixpresplit however is optimized for fast and reliable workflows to qickly get things done. 

### Basic usage

Just specify a input directory and a output pattern and press Enter:
```bash
mixpresplit G:/MixPre_SD-Card/MyProject D:/Recordings/Myfolder/{tracknumber}_{take}.wav
```
This will read all recordings from the SD-Card, split them and place them into the target folder. If you wonder about the meaning of `{tracknumber}` and `{take}` these are _keywords_ which make mixpresplit very productive and powerful:

### Keywords

Keywords are special predefined variables that you can use in the output path. A more advanced example:
```bash
mixpresplit G:/MixPre/MyProject "D:/Recordings/{date} {scene}/Take_{take}/{tracknumber}_{trackname}-Take{take}" --flac
```
This will take all recordings found on the SD-card at `G:/MixPre/MyProject` and create a folder in `D:/Recordings` for each day of recording, each containing folders for each take. The tracks of the recording will be converted to flac and sorted by tracknumber (they map to the track numbers found on the recorder, the mixdown channels for MixL and MixR always get the numbers 9 and 10). The result could look like this:
```
D:/Recordings/
   |-- 2020-08-12 Bandpractise/
   |          |--Take_1/
   |          |    |--1_Drums.L-Take1.flac
   |          |    |--2_Drums.R-Take1.flac
   |          |    |--3_Bass-Take1.flac
   |          |    |--4_Synth-Take1.flac
   |          |--Take_2/
   |               |--1_Drums.L-Take2.flac
   |               |--2_Drums.R-Take2.flac
   |               |--3_Bass-Take2.flac
   |               |--4_Synth-Take2.flac
   |-- 2020-08-13 Bandpractise/
              |--Take_1/
              |    |--1_Drums.L-Take1.flac
              |    |--2_Drums.R-Take1.flac
              |    |--3_Bass-Take1.flac
              |    |--4_Synth-Take1.flac
              |--Take_2/
                   |--1_Drums.L-Take2.flac
                   |--2_Drums.R-Take2.flac
                   |--3_Bass-Take2.flac
                   |--4_Synth-Take2.flac
```
As you can see the magic lies in statements like `{date}`, `{take}` and `{tracknumber}`: these are automatically filled in by mixpresplit with the values stored in the recordings themselves. So if you decided that instead of sorting by `Day/Scene > Take > Track` you'd rather sort by `Track > Month > Scene` you'd just had to rewrite that one path with different keywords.

You can find a list of all possible keywords when running `mixpresplit -h`:
```
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
```

### Filters
If you want to only export certain tracks you can use _filters_ to narrow down the exported material. 
Filters can be one of the following:
```
--only-circled          Use only circled takes
--tracks TEXT           include/Exclude certain tracks
--takes  TEXT           include/Exclude certain takes
```

#### Filter by Take

A simple usage is to export only circled takes:
```bash
mixpresplit G:/MixPre/MyProject "D:/Recordings/Drums/{trackname}.wav" --only-circled
```

If you only want to export a certain take you can use the `--takes` filter (only export take 4):
```bash
mixpresplit G:/MixPre/MyProject "D:/Recordings/Drums/{trackname}.wav" --takes 4
```

You can also export a range of takes (only export takes 1 to 4):
```bash
mixpresplit G:/MixPre/MyProject "D:/Recordings/Drums/{trackname}.wav" --takes 1-4
```

By adding ! in front you can invert the behaviour (you may have to wrap the option in single quotes).
So this export every take _except_ the takes 1 to 4:
```bash
mixpresplit G:/MixPre/MyProject "D:/Recordings/Drums/{trackname}.wav" --takes '!1-4'
```

You can use multiple of these filters by either seperating the statements with commas or by using multiple options.
So this skips takes 1 to 7 except take 5 and also includes take 23:
```bash
mixpresplit G:/MixPre/MyProject "D:/Recordings/Drums/{trackname}.wav" --takes '!1-7,5' --take 23
```

#### Filter by Track

All the filters you can use with takes can also be used with tracks.
Here we only export the tracks 1 to 7:
```bash
mixpresplit G:/MixPre/MyProject "D:/Recordings/Drums/{trackname}.wav" --tracks '1-7'
```

Additionally you can search the trackname to filter tracks.
For example if you only want to export tracks with "Drums" in their names use this:
```bash
mixpresplit G:/MixPre/MyProject "D:/Recordings/Drums/{trackname}.wav" --tracks 'Drums'
```

If you want to export anything except Drums just invert it with the ! sign:
```bash
mixpresplit G:/MixPre/MyProject "D:/Recordings/Drums/{trackname}.wav" --tracks '!Drums'
```

### Format Conversion

Per default mixpresplit will use the very same output format as present in the input. So if you split a 32 Bit wav file, the resulting files will be 32 Bit wav files as well.

If you want to convert the files you use these:
```
--flac        Use FLAC instead of WAV for output
--24          Output as 24 bit audio
--16          Output as 16 bit audio
```

More formats might follow in the future, given the ffmpeg base they should not be hard to implement, feel free to post a issue on github.

### Renaming things

It might happen that you named things wrongly on set or in the studio, for this you can use the options:
```
--replace TEXT     Replace this string in OUTPATH
--with    TEXT     With that string
```

If you for example want to replace the word "Drums" in your channels with "Bass" you can use this:
```bash
mixpresplit G:/MixPre/MyProject "D:/Recordings/{date}/{trackname}.wav" --rename Drums --with Bass
```

Careful however, because this replaces in the whole OUTPATH:
```
"D:/Recordings/Drums/{trackname}.wav" -> "D:/Recordings/Bass/{trackname}.wav"
```

You always have to use these options in pairs. If you don't match the numbers, mixpresplit will complain and remind you. This functionality is a little crude, and might be improved at some point.

## Installation

### From Source

mixpresplit uses Python 3 and depends on ffmpeg. For Python dependency managment [python poetry](https://python-poetry.org/) is used. If you want to use poetry you can use these steps:

1. Clone this repo using `git clone` in the terminal and enter it
2. Install Python3 using either an [installer](https://www.python.org/downloads/) or your package manager (`sudo apt install python3` or similar)
3. Install [ffmpeg] and make sure the executable is found in your systems PATH variable
4. Install [python poetry](https://python-poetry.org/docs/#installation)
5. Run `poetry install` to download the dependecies
6. Run with `poetry run mixpresplit`

### Using PIP

1. Install Python3 using either an [installer](https://www.python.org/downloads/) or your package manager (`sudo apt install python3` or similar)
2. Install python-pip if it hasn't been installed in step 1
3. Install [ffmpeg] and make sure the executable is found in your systems PATH variable
4. Install with `pip install mixpresplit` or `pip3 install mixpresplit`
5. Run with `mixpresplit`

## Run Tests

Make sure you have the `python-pytest` package installed. Then run `poetry run py.test`

### Binary Packages

Something like a packed executable for Windows or a debian package for Linux systems might follow at some point
