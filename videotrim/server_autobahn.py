from collections import OrderedDict
from datetime import datetime
import os

import logging
import logging.config
import subprocess

import tempfile
import json
import time

from videotrim import settings

import socket

try:
    import asyncio
except ImportError:
    # Trollius >= 0.3 was renamed
    import trollius as asyncio

from autobahn.asyncio.websocket import WebSocketServerProtocol, \
    WebSocketServerFactory

video_dir = r'C:\video\sample'

trim_dir = tempfile.TemporaryDirectory()

# TODO move logging config to a different file

ffmpeg_report_logger = logging.getLogger('ffmpeg-report')
ffmpeg_logger = logging.getLogger('ffmpeg')
ws_logger = logging.getLogger('websocket')
logger = logging.getLogger('videotrim')

default_port = 5743

new_tab_data = list()


vs_script = r'''import vapoursynth as vs
core = vs.get_core()
# core.std.LoadPlugin(path=r".........")
video = core.ffms2.Source(source=r"@@mkv@@")

# QTGMC
# import havsfunc as haf
# video = haf.QTGMC(video, Preset='medium', TFF=True)
# video = haf.QTGMC(video, Preset='placebo', TFF=True)
# video = haf.QTGMC(video, Preset='draft', TFF=True)

# debilienar
# core.avs.LoadPlugin(path=r'@@internal dir@@\debilinear.dll')
# video = core.avs.debilinear(video, 40,80)

# @@framecount@@ frames
video.set_output()'''
# vs_script = r'''import vapoursynth as vs
# core = vs.get_core()
# video = core.lsmas.LWLibavSource(source=r"@@mkv@@")
# # @@framecount@@ frames
# video.set_output()'''

counter = 1


def kinda_unique_str():
    global counter
    counter += 1  # race condition?
    return str(time.time()) + str(counter)

ffplay_windows = dict()


class MyError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def order_websocket_dict(json_str):
    # make logs easier to read by always printing command or event entries first
    ddict = json.loads(json_str)
    ordered = OrderedDict()
    if 'command' in ddict:
        ordered['command'] = ddict['command']
    if 'event' in ddict:
        ordered['event'] = ddict['event']
    for item in ddict.items():
        ordered[item[0]] = item[1]
    return json.dumps(ordered)


def file_dragged_handler(data):
    filename = data['filename']
    logger.debug('locating ' + filename)
    for file in os.listdir(video_dir):
        if file == filename:
            video_file = os.path.join(video_dir, file)
            logger.info('located: ' + video_file)
            return {'command': 'set_video_path', 'video_path': video_file}
    logger.info('could not locate file: ' + filename)
    return {'command': 'alert', 'message': 'video file not found'}


def to_timestamp(int_timestamp):
    try:
        return datetime.strptime(str(int_timestamp).zfill(6), '%H%M%S').time().strftime('%H:%M:%S')
    except ValueError:
        raise ValueError('Invalid timestamp: %s. Timestamp must be of form: '
                         'S or SS or MSS or MMSS or HMMSS or HHMMSS.' % int_timestamp)


class MyServerProtocol(WebSocketServerProtocol):
    server_log = list()

    def onConnect(self, request):
        ws_logger.debug("Client connecting: {0}".format(request.peer))

    def onOpen(self):
        ws_logger.debug("WebSocket connection open.")
        self.session = self

    def update_server_log(self, new_line):
        self.server_log.append(time.strftime('%H:%M:%S') + ' ' + new_line)
        last_3_lines = self.server_log[-3:]
        last_3_lines.reverse()
        self.VtSendMessage({'command': 'set_server_log',
                            'contents': '<br>'.join(last_3_lines)})

    async def quick_preview(self, lossless_trim):
        # show a preview of the source lossless trim without going through vapoursynth
        preview_pre_params = ['-i', lossless_trim, '-vf', 'scale=640:-1']
        preview = os.path.join(trim_dir.name, 'vid%s.%s' % (time.time(), settings.preview_filetype()))
        await self.ffmpeg(preview_pre_params + settings.preview_ffmpeg_args() + ['-an', '-y'] + [preview] + ['-report'])
        self.VtSendMessage({'command': 'display_video',
                            'source_tag': '<video id="video" autoplay loop muted>'
                                          '<source src="file:///%s" type="video/%s">'
                                          '</video>' % (preview.replace('\\', '/'), settings.preview_filetype())})

    # def display_preview_of_script(self, script):
    #     script_filename = os.path.join(trim_dir.name, '%s.vpy' % time.time())
    #     with open(script_filename, 'w', encoding='utf-8') as script_file:
    #         script_file.write(script)
    #     if settings.webm_preview:
    #         preview = os.path.join(trim_dir.name, 'vid%s.webm' % time.time())
    #         params = ['-vf', 'scale=640:-1', '-c:v', 'libvpx'] + settings.webm_preview_params
    #         vidtype = 'video/webm'
    #     else:
    #         preview = os.path.join(trim_dir.name, 'vid%s.mp4' % time.time())
    #         params = ['-vf', 'scale=640:-1', '-c:v', 'libx264'] + settings.mp4_preview_params
    #         vidtype = 'video/mp4'
    #     start_time = time.time()
    #     commandd = ['cmd.exe', '/c', settings.vspipe_location, '--y4m', script_filename, '-', '|',
    #                 settings.ffmpeg_location, '-i', 'pipe:'] + params + [preview]
    #     subprocess.call(commandd)
    #     elapsed_time = time.time() - start_time
    #     logger.info('vspipe call finished in: %ss' % str(round(elapsed_time, 3)))
    #     self.VtSendMessage({'command': 'display_video',
    #                                  'source_tag': '<video id="video" autoplay loop muted>'
    #                                                '<source src="file:///%s" type="%s">'
    #                                                '</video>' % (preview.replace('\\', '/'), vidtype)})

    def kill_ffplay(self, window_key):
        """ close an ffplay window, or the ffmpeg process encoding its video, should it still be in progress """
        if window_key in ffplay_windows:
            ffmpeg_process = ffplay_windows['ffmpeg']
            ffplay_process = ffplay_windows['ffplay']
            ffmpeg_process.kill()
            ffplay_process.kill()
            del ffplay_windows[window_key]

    async def display_in_ffplay(self, script, lossless=True):
        ffplay_window_key = str(time.time())
        if lossless:
            ffplay_windows['ffmpeg'] = await self.ffmpeg()

    async def create_lossless_trim(self, data):
        timestamp = to_timestamp(data['timestamp'].strip())
        output_extension = data['video_path'][data['video_path'].rfind('.'):]
        if int(data['x264lossless']) == 1:
            output_extension = '.mkv'
            preview_pre_params = ['-ss', str(timestamp), '-i', data['video_path'], '-t', '00:00:05', '-c:v', 'libx264',
                                  '-qp', '0', '-preset', 'ultrafast']
        else:
            preview_pre_params = ['-ss', str(timestamp), '-i', data['video_path'], '-t', '00:00:05', '-c:v', 'copy']
        lossless_trim = os.path.join(trim_dir.name, 'vid%s%s' % (time.time(), output_extension))
        preview_post_params = ['-an', '-y']
        await self.ffmpeg(preview_pre_params + preview_post_params + [lossless_trim] + ['-report'])
        import vapoursynth as vs
        core = vs.get_core()
        video = core.lsmas.LWLibavSource(source=lossless_trim)
        framecount = video.num_frames
        script = vs_script.replace('@@framecount@@', str(framecount))\
            .replace('@@mkv@@', lossless_trim).replace('@@internal dir@@', settings.internal_dir())
        self.VtSendMessage({'command': 'set_vapoursynth_script',
                            'script_contents': script.replace('\n', '<br>')})
        # since lossless_trim will be displayed in its entirety, there's no need to go through vapoursynth
        await self.quick_preview(lossless_trim)
        # self.display_preview_of_script(script)

    async def start_ffmpeg(self, params):
        report_dir = os.path.join(settings.tmp_dir(), kinda_unique_str())
        os.mkdir(report_dir)
        ffmpeg_logger.info('ffmpeg call: ' + ' '.join(params))
        return {'process': await asyncio.create_subprocess_exec(settings.ffmpeg(), *params, cwd=report_dir,
                                                                stderr=subprocess.DEVNULL),
                'start_time': time.time(),
                'report_dir': report_dir}

    async def await_ffmpeg(self, start_ffmpeg_object):
        return_code = await start_ffmpeg_object['process'].wait()
        elapsed_time = time.time() - start_ffmpeg_object['start_time']
        for logfile in os.listdir(start_ffmpeg_object['report_dir']):
            if logfile.endswith('.log'):
                with open(os.path.join(start_ffmpeg_object['report_dir'], logfile), 'r', encoding='utf-8') as lf:
                    for line in lf.readlines():
                        ffmpeg_report_logger.debug(line.rstrip())
            else:
                pass
        ffmpeg_logger.debug('ffmpeg call finished in: %ss' % str(round(elapsed_time, 2)))
        if return_code != 0:
            raise MyError('ffmpeg call failed with error code ' + str(return_code))
        else:
            self.update_server_log('ffmpeg call successful')

    # def timestamp_entered_handler(self, data):
    #     timestamp = to_timestamp(data['timestamp'].strip())
    #     print('got timestamp')
    #     preview_pre_params = ['-ss', str(timestamp), '-i', data['video_path'], '-t', '00:00:05', '-vf', 'scale=640:-1']
    #     trimmed = os.path.join(trim_dir.name, 'vid%s.%s' % (time.time(), settings.preview_filetype()))
    #     self.ffmpeg(preview_pre_params + settings.preview_ffmpeg_args() + ['-an', '-y'] + [trimmed] + ['-report'])
    #     return json.dumps({'command': 'display_video',
    #                        'source_tag': '<video id="video" autoplay loop muted>'
    #                                      '<source src="file:///' + trimmed.replace('\\',
    #                                                                                '/') + '" type="video/' + settings.preview_filetype() + '">'
    #                                                                                                                                        '</video>'})

    async def ffmpeg(self, ffmpeg_params):
        started = await self.start_ffmpeg(ffmpeg_params)
        await self.await_ffmpeg(started)
        # tempdir = tempfile.TemporaryDirectory()
        # self.update_server_log('calling ffmpeg')
        # ffmpeg_logger.info('ffmpeg call: ' + ' '.join(ffmpeg_params))
        # start_time = time.time()
        # # return_code = subprocess.call([settings.ffmpeg_location, *ffmpeg_params], cwd=tempdir.name, stderr=subprocess.DEVNULL)
        # process = await asyncio.create_subprocess_exec(settings.ffmpeg(), *ffmpeg_params, cwd=tempdir.name,
        #                                                stderr=subprocess.DEVNULL)
        # return_code = await process.wait()
        # elapsed_time = time.time() - start_time
        # for logfile in os.listdir(tempdir.name):
        #     if logfile.endswith('.log'):
        #         with open(os.path.join(tempdir.name, logfile), 'r', encoding='utf-8') as lf:
        #             for line in lf.readlines():
        #                 ffmpeg_report_logger.debug(line.rstrip())
        #     else:
        #         pass
        # ffmpeg_logger.debug('ffmpeg call finished in: %ss' % str(round(elapsed_time, 2)))
        # if return_code != 0:
        #     raise MyError('ffmpeg call failed with error code ' + str(return_code))
        # else:
        #     self.update_server_log('ffmpeg call successful')

    def VtSendMessage(self, payload):
        dumped = json.dumps(payload)
        ws_logger.debug(">>>> " + order_websocket_dict(dumped))
        self.sendMessage(dumped.encode('utf-8'))

    async def onMessage(self, payload, isBinary):
        if isBinary:
            ws_logger.error('received binary message')
            raise ValueError
        else:
            ws_logger.debug("<--- " + order_websocket_dict(payload.decode('utf8')))

        data = json.loads(payload.decode('utf8'))

        if 'event' in data.keys():
            event = data['event']
            if event == 'file_dragged':
                self.VtSendMessage(file_dragged_handler(data))
            elif event == 'timestamp_entered':
                try:
                    # msg = self.timestamp_entered_handler(data)
                    await self.create_lossless_trim(data)
                except MyError as e:
                    print(e.value)
                    self.VtSendMessage({'command': 'alert', 'message': e.value})
            elif event == 'open_in_vsedit':
                script_filename = os.path.join(trim_dir.name, '%s.vpy' % time.time())
                with open(script_filename, 'w', encoding='utf-8') as script_file:
                    script_file.write(data['script'].replace('<br>', '\n'))
                logger.info('opening %s in vsedit' % script_filename)
                await asyncio.create_subprocess_exec(settings.vsedit(), script_filename)
            elif event == 'data_entered_for_new_tab':
                tab_id = len(new_tab_data)
                new_tab_data.append({'video_path': data['video_path'],
                                     'x264lossless': data['x264lossless'],
                                     'timestamp': data['timestamp']})
                self.VtSendMessage({'command': 'open_new_tab',
                                    'tab_id': tab_id})
            elif event == 'new_tab_opened':
                tab_data = new_tab_data[int(data['tab_id'])]
                self.VtSendMessage({'command': 'set_video_path',
                                    'video_path': tab_data['video_path']})
                self.VtSendMessage({'command': 'set_timestamp',
                                    'timestamp': tab_data['timestamp']})
                # TODO below is a 1:1 copy of elif event == 'timestamp_entered':
                try:
                    # msg = self.timestamp_entered_handler(data)
                    await self.create_lossless_trim(tab_data)
                except MyError as e:
                    print(e.value)
                    self.VtSendMessage({'command': 'alert', 'message': e.value})
            elif event == 'raise_exception':
                # test: start_server.bat should not close
                # https://docs.python.org/3.5/library/exceptions.html#exception-hierarchy
                raise NameError
            else:
                logger.error('undefined event in client WS message: ' + event)
        else:
            logger.error('client WS message did not contain "event" entry')

    def onClose(self, wasClean, code, reason):
        ws_logger.debug("WebSocket connection closed: {0}".format(reason))


def get_free_port():
    start_port = 5743
    port = start_port

    def port_is_free(potential_port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('127.0.0.1', potential_port))
            s.close()
            return True
        except OSError:
            return False

    while not port_is_free(port) and port < start_port + 30:
        port += 1

    return port


def prepare_html(port):
    with open(settings.html_template(), 'r', encoding='utf-8') as rawfile:
        with open(settings.replaced_html(), 'w', encoding='utf-8') as replacedfile:
            replacedfile.write(rawfile.read().replace('@@port@@', str(port)))


def start():
    port = get_free_port()
    prepare_html(port)

    factory = WebSocketServerFactory(u'ws://127.0.0.1:' + str(port))
    factory.protocol = MyServerProtocol

    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    coro = loop.create_server(factory, '127.0.0.1', port)
    logger.info('starting server')
    server = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        loop.close()


if __name__ == '__main__':
    settings.setup_logging(logging.DEBUG)
    start()
