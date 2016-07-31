import configparser
import logging
import os
from logging.handlers import RotatingFileHandler

settings_folder = os.path.join(os.getenv('APPDATA'), 'VideoTrim')
settings_file = os.path.join(settings_folder, 'config.ini')
config = configparser.ConfigParser()

# TODO there's probabaly a better way to do this.....
install_dir = lambda: config.get('vt', 'install_dir')
internal_dir = lambda: os.path.join(install_dir(), 'internal')
tmp_dir = lambda: os.path.join(internal_dir(), 'temp')
python_dir = lambda: os.path.join(internal_dir(), 'python')
log_dir = lambda: os.path.join(internal_dir(), 'logs')
ffmpeg = lambda: os.path.join(internal_dir(), 'ffmpeg.exe')
ffprobe = lambda: os.path.join(internal_dir(), 'ffprobe.exe')
html_template = lambda: os.path.join(internal_dir(), 'template.html')
replaced_html = lambda: os.path.join(internal_dir(), 'index.html')
vsedit = lambda: os.path.join(python_dir(), 'vsedit-32bit.exe')
dgindex = lambda: os.path.join(internal_dir(), 'DGIndex.exe')
preview_filetype = lambda: 'mp4'
preview_ffmpeg_args = lambda: '-c:v libx264 -preset ultrafast -crf 18'.split(' ')


# initialization
if not os.path.isdir(settings_folder):
    os.mkdir(settings_folder)

if os.path.isfile(settings_file):
    config.read(settings_file)
else:
    config.add_section('vt')
    with open(settings_file, 'w') as configfile:
        config.write(configfile)


def save():
    temp_file = settings_file + '.tmp'
    with open(temp_file, 'w') as configfile:
        config.write(configfile)
    os.replace(temp_file, settings_file)


def set_install_dir(install_dir):
    config.set('vt', 'install_dir', install_dir)
    save()


def register_bat_execution(bat_dir):
    print('install dir: ' + bat_dir)
    set_install_dir(bat_dir)


def setup_logging(console_log_level):
    logFormatter = logging.Formatter("%(asctime)s %(name)-9s %(levelname)-5.5s %(message)s")

    # loggers
    ffmpeg_report_logger = logging.getLogger('ffmpeg-report')
    ffmpeg_report_logger.setLevel(logging.DEBUG)

    ffmpeg_logger = logging.getLogger('ffmpeg')
    ffmpeg_logger.setLevel(logging.DEBUG)

    ws_logger = logging.getLogger('websocket')
    ws_logger.setLevel(logging.DEBUG)

    logger = logging.getLogger('videotrim')
    logger.setLevel(logging.DEBUG)

    # handlers
    ten_megabytes = 10**7

    defaultFileHandler = RotatingFileHandler(os.path.join(log_dir(), 'log.log'), encoding='utf-8', maxBytes=ten_megabytes, backupCount=2)
    defaultFileHandler.setFormatter(logFormatter)

    ffmpegFileHandler = RotatingFileHandler(os.path.join(log_dir(), 'ffmpeg.log'), encoding='utf-8', maxBytes=ten_megabytes, backupCount=2)
    ffmpegFileHandler.setFormatter(logFormatter)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    consoleHandler.setLevel(console_log_level)

    # add handlers to loggers
    ffmpeg_report_logger.addHandler(ffmpegFileHandler)

    ffmpeg_logger.addHandler(ffmpegFileHandler)
    ffmpeg_logger.addHandler(defaultFileHandler)
    ffmpeg_logger.addHandler(consoleHandler)

    ws_logger.addHandler(defaultFileHandler)
    ws_logger.addHandler(consoleHandler)

    logger.addHandler(defaultFileHandler)
    logger.addHandler(consoleHandler)
