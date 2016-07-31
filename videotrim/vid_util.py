import asyncio
import json
import logging
import os
import subprocess

import time

from videotrim import settings
from videotrim import util
logger = logging.getLogger('videotrim')
ffprobe_params = '-v quiet -print_format json -show_streams -show_format'.split(' ')

def ffprobe(file):
    return json.loads(subprocess.check_output([settings.ffprobe(), '-i', file] + ffprobe_params).decode('utf-8'))

def stream0(ffprobe_data):
    for stream in ffprobe_data['streams']:
        if stream['index'] == 0:
            return stream
    raise AssertionError('no stream 0 found')

def is_mpeg2ts(file):
    data = ffprobe(file)
    fformat = data['format']['format_name']
    fcodec = stream0(data)['codec_name']
    logger.debug('ffprobe of %s: found format %s and codec %s' % (file, fformat, fcodec))
    return fformat == 'mpegts' and fcodec == 'mpeg2video'

def vs_script(src_line):
    return r'''import vapoursynth as vs
core = vs.get_core()
# core.std.LoadPlugin(path=r".........")
@@source line@@

# video = core.std.SeparateFields(video)
# video = core.std.DoubleWeave(video)

# QTGMC
# import havsfunc as haf
# video = haf.QTGMC(video, Preset='medium', TFF=True)
# video = haf.QTGMC(video, Preset='placebo', TFF=True)
# video = haf.QTGMC(video, Preset='draft', TFF=True)

# debilienar
# core.avs.LoadPlugin(path=r'@@internal dir@@\debilinear.dll')
# video = core.avs.debilinear(video, 40,80)

# import finesharp
# sharpened = finesharp.sharpen(video, sstr=2)
# video = core.std.StackHorizontal([video, sharpened])

# @@frame count@@ frames
video.set_output()'''.replace('@@source line@@', src_line)\
        .replace('@@frame count@@', str(framecount(src_line)))\
        .replace('@@internal dir@@', settings.internal_dir())

src_prefix = 'video = '

ffms2_src = lambda x: src_prefix + "core.ffms2.Source(source=r'" + x + "')"
lsmash_src = lambda x: src_prefix + "core.lsmas.LWLibavSource(source=r'" + x + "')"

async def d2v_src(mpeg2ts_location):
    # creates d2v, returns src line that loads the d2v
    d2v_filename = os.path.join(settings.tmp_dir(), util.kinda_unique_str())
    params = ['-i', mpeg2ts_location, '-o', d2v_filename, '-hide', '-exit']
    logger.debug('%s calling dgindex with params %s' % (time.time(), params))
    a = await asyncio.create_subprocess_exec(settings.dgindex(), *params)
    await a.wait()
    return src_prefix + "core.d2v.Source(input=r'" + d2v_filename + ".d2v')"


def framecount(src_line):
    import vapoursynth as vs
    core = vs.get_core()
    num_frames = eval(src_line.replace(src_prefix, '')).num_frames
    return num_frames

