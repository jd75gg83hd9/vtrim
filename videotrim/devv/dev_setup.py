import subprocess
import tempfile
import urllib.request
import os
import tarfile
import shutil
import zipfile
from urllib.parse import urlparse
from videotrim.devv import lib_dir, download_dir


def download_archive(url):
    filename = urlparse(url).path.split('/')[-1]
    file_path = os.path.join(download_dir, filename)
    partial_file_path = file_path + '.part'

    if os.path.isfile(file_path):
        print('%s already exists, skipping download' % filename)
    else:
        if os.path.isfile(partial_file_path):
            os.remove(partial_file_path)
        print('downloading %s to %s' % (filename, download_dir))
        with urllib.request.urlopen(url) as data:
            with open(partial_file_path, 'wb') as f:
                f.write(data.read())
        os.rename(partial_file_path, file_path)

    return file_path


def get_7zip():
    tar = tarfile.open(download_archive(r'http://7-zip.org/a/lzma920.tar.bz2'))
    tar.extract('7zr.exe', lib_dir)
    tar.close()


def clean_lib_dir():
    if os.path.isdir(lib_dir):
        shutil.rmtree(lib_dir)
    os.mkdir(lib_dir)
    os.mkdir(download_dir)

def zip_e(zip, dst_dir, extract_files, exclude_folder_pattern):
    """like 7zip e mode, extract specific files, ignoring zip folder structure"""
    copied_files = set()
    with tempfile.TemporaryDirectory() as tmp_dir:
        zipfile.ZipFile(zip).extractall(tmp_dir)
        for root, dirs, files in os.walk(tmp_dir):
            for name in files:
                if exclude_folder_pattern not in root:
                    srcfile = os.path.join(root, name)
                    dstfile = os.path.join(dst_dir, name)
                    if name in extract_files:
                        if os.path.isfile(dstfile):
                            raise AssertionError('wanted to extract %s from %s, but the file already exists' % (name, zip))
                        if name in copied_files:
                            raise AssertionError('wanted to extract %s from %s, but it was already extracted' % (name, zip))
                        print('extracting %s to %s' %(srcfile, dstfile))
                        shutil.copy(srcfile, dstfile)
                        copied_files.add(name)
    for ef in extract_files:
        if not ef in copied_files:
            raise AssertionError('could not extract %s from %s' % (ef, zip))

def unzip_without_top_directory(zip, dst_dir, file_ending_whitelist=None):
    """unzip but ignore the top level directory in the zip"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        zipfile.ZipFile(zip).extractall(tmp_dir)
        top_directory = os.path.join(tmp_dir, os.listdir(tmp_dir)[0])
        for f in os.listdir(top_directory):
            dst_path = os.path.join(dst_dir, f)
            if not os.path.isfile(dst_path) and not os.path.isdir(dst_path):
                if file_ending_whitelist is not None:
                    for ending in file_ending_whitelist:
                        if dst_path.endswith(ending):
                            shutil.move(os.path.join(top_directory, f), dst_path)
                else:
                    shutil.move(os.path.join(top_directory, f), dst_path)

get_7zip()
sevenzip = os.path.join(lib_dir, '7zr.exe')

release_dir = r'C:\vid-rls'
internal_dir = os.path.join(release_dir, 'internal')
python_dir = os.path.join(internal_dir, 'python')

# deleting & creating folders through python while some of them are open in explorer
# or otherwise somehow in use is unreliable (random access denied errors), so using cmd
if os.path.isdir(release_dir):
    print('deleting ' + release_dir)
    subprocess.call(['cmd.exe', '/c', 'rmdir', release_dir, '/q', '/s'])
print('creating ' + release_dir)
subprocess.call(['cmd.exe', '/c', 'mkdir', release_dir])
print('creating subdirectories')
subprocess.call(['cmd.exe', '/c', 'mkdir', internal_dir])
subprocess.call(['cmd.exe', '/c', 'mkdir', python_dir])
subprocess.call(['cmd.exe', '/c', 'mkdir', os.path.join(internal_dir, 'logs')])
subprocess.call(['cmd.exe', '/c', 'mkdir', os.path.join(internal_dir, 'temp')])
print('finished creating subdirectories')

python_embedded_archive = download_archive(r'https://www.python.org/ftp/python/3.5.1/python-3.5.1-embed-win32.zip')
ffmpeg_archive = download_archive(r'https://ffmpeg.zeranoe.com/builds/win64/static/ffmpeg-latest-win64-static.7z')
vsynth_archive = download_archive(r'https://github.com/vapoursynth/vapoursynth/releases/download/R32/VapourSynth32-Portable-R32.7z')

# http://autobahn.ws/python/installation.html#windows-installation
get_pip = download_archive(r'https://bootstrap.pypa.io/get-pip.py')

# TODO dangerous filenames with these two (could conflict):
havsfunc_archive = download_archive(r'https://github.com/HomeOfVapourSynthEvolution/havsfunc/archive/r23.zip')
mvsfunc_archive = download_archive(r'https://github.com/HomeOfVapourSynthEvolution/mvsfunc/archive/r7.zip')

vsedit_archive = download_archive(r'https://bitbucket.org/mystery_keeper/vapoursynth-editor/downloads/VapourSynthEditor-r8-32bit.7z')
ffms2_archive = download_archive(r'https://github.com/FFMS/ffms2/releases/download/2.22/ffms2-2.22-msvc.7z')
fmtcnv_archive = download_archive(r'https://github.com/EleonoreMizo/fmtconv/releases/download/r20/fmtconv-r20.zip')
# L-SMASH   http://forum.doom9.org/showthread.php?t=167435
lsmash_archive = download_archive(r'https://www.dropbox.com/sh/3i81ttxf028m1eh/AAD5uZ7GGyJVd0zxrvx3sK4pa/Old/L-SMASH-Works-r879-20160627-32bit.7z?dl=1')
debilinear_archive = download_archive(r'http://web.archive.org/web/20140214021604/http://rgb.chromashift.org/debilinear%20r6.zip')
debicubic_archive = download_archive(r'http://web.archive.org/web/20140420184606/http://rgb.chromashift.org/debicubic%20r2.zip')
finesharp_script = download_archive(r'https://gist.github.com/4re/8676fd350d4b5b223ab9/raw/8314a9a4c9ca8f2e1842ff301fe36d0eee54182a/finesharp.py')

# QTGMC
adjust_script = download_archive('https://raw.githubusercontent.com/dubhater/vapoursynth-adjust/master/adjust.py')
mvtools_archive = download_archive(r'https://github.com/dubhater/vapoursynth-mvtools/releases/download/v13/vapoursynth-mvtools-v13-win32.7z')
nnedi3_archive = download_archive(r'https://github.com/dubhater/vapoursynth-nnedi3/releases/download/v8/vapoursynth-nnedi3-v8-win32.7z')
nnedi3_weights = download_archive(r'https://github.com/dubhater/vapoursynth-nnedi3/raw/v6/src/nnedi3_weights.bin')

# only necessary for QTGMC placebo & very slow
fft3dfilter_archive = download_archive(r'http://vfrmaniac.fushizen.eu/works/vsfft3dfilter_r22-b023e21.7z')
fftw_archive = download_archive(r'ftp://ftp.fftw.org/pub/fftw/fftw-3.3.4-dll32.zip')

# mpeg2 TS handling
d2vsource_archive = download_archive(r'https://github.com/dwbuiten/d2vsource/releases/download/v1.0/d2vsource-1.0-windows.zip')
# DGIndex.exe http://avisynth.nl/index.php/DGDecode
dgdecode_archive = download_archive(r'http://hank315.nl/files/DGdecode/dgmpgdec158_SSE.zip')

scd_archive = os.path.join(download_dir, 'scenechange-0.2.0-2.7z')
if not os.path.isfile(scd_archive):
    raise ValueError('auto download of mediafire links not possible - download SCD manually http://forum.doom9.org/showthread.php?t=166769 and put in lib\download')


# vsedit - top level dir in 7z needs to be removed?
# "You can also use the VapourSynth Editor by decompressing it into the same directory."
# http://www.vapoursynth.com/doc/installation.html#windows-portable-instructions
with tempfile.TemporaryDirectory() as tmp_dir:
    subprocess.call([sevenzip, 'x', vsedit_archive, '-y', '-o' + tmp_dir])
    vsedit_root = os.path.join(tmp_dir, os.listdir(tmp_dir)[0])
    for f in os.listdir(vsedit_root):
        dest = os.path.join(python_dir, f)
        if not os.path.isfile(dest) and not os.path.isdir(dest):
            shutil.move(os.path.join(vsedit_root, f), dest)

subprocess.call([sevenzip, 'x', vsynth_archive, '-y', '-o' + python_dir])
zipfile.ZipFile(python_embedded_archive).extractall(python_dir)

subprocess.call([sevenzip, 'e', ffmpeg_archive, '-y', '-o' + internal_dir, 'ffmpeg.exe', 'ffprobe.exe', 'ffplay.exe', '-r'])

shutil.copy('template.html', os.path.join(internal_dir, 'template.html'))
shutil.copy(os.path.join(internal_dir, 'template.html'), os.path.join(internal_dir, 'index.html'))
shutil.copy('start_server.py', os.path.join(internal_dir, 'start_server.py'))
shutil.copy('start_server.bat', os.path.join(release_dir, 'start_server.bat'))

# videotrim module
# shutil.copytree(os.path.dirname(os.getcwd()), os.path.join(python_dir, 'videotrim'), ignore=shutil.ignore_patterns('*.pyc))
dst_dir = os.path.join(python_dir, 'videotrim')
os.mkdir(dst_dir)
vt_dir = os.path.dirname(os.getcwd())
for f in os.listdir(vt_dir):
    if f.endswith('.py'):
        shutil.copy(os.path.join(vt_dir, f), os.path.join(dst_dir, f))

unzip_without_top_directory(havsfunc_archive, python_dir, file_ending_whitelist=['havsfunc.py'])
unzip_without_top_directory(mvsfunc_archive, python_dir, file_ending_whitelist=['mvsfunc.py'])
shutil.copy(adjust_script, os.path.join(python_dir, 'adjust.py'))

def sevenzip_e(archive, dst_dir, files, flags=[]):
    for file in files:
        if os.path.isfile(os.path.join(dst_dir, file)):
            raise AssertionError('wanted to extract %s from %s, but it already exists in the destination '
                                 'location %s' % (file, archive, dst_dir))
    subprocess.call([sevenzip, 'e', archive, '-y', '-o' + dst_dir] + files + ['-r'] + flags)
    for file in files:
        if not os.path.isfile(os.path.join(dst_dir, file)):
            raise AssertionError('Could not extract %s from %s' % (file, archive))

vsynth_plugins = os.path.join(python_dir, 'vapoursynth32', 'plugins')
sevenzip_e(lsmash_archive, vsynth_plugins, ['vslsmashsource.dll'])
sevenzip_e(scd_archive, vsynth_plugins, ['scenechange.dll', 'temporalsoften2.dll'])
sevenzip_e(scd_archive, python_dir, ['temporalsoften2.py'])
sevenzip_e(mvtools_archive, vsynth_plugins, ['libmvtools.dll'])
sevenzip_e(nnedi3_archive, vsynth_plugins, ['libnnedi3.dll'])
sevenzip_e(ffms2_archive, vsynth_plugins, ['ffms2.dll', 'ffms2.lib', 'ffmsindex.exe'], ['-xr!*x64*'])
sevenzip_e(fft3dfilter_archive, vsynth_plugins, ['vsfft3dfilter.dll'], ['-xr!*x64*'])
shutil.copy(nnedi3_weights, os.path.join(vsynth_plugins, os.path.split(nnedi3_weights)[1]))
shutil.copy(finesharp_script, os.path.join(python_dir, os.path.split(finesharp_script)[1]))
shutil.copy(get_pip, os.path.join(internal_dir, os.path.split(get_pip)[1]))
zip_e(fmtcnv_archive, vsynth_plugins, ['fmtconv.dll'], '64')
zip_e(d2vsource_archive, vsynth_plugins, ['d2vsource.dll'], '64')
zip_e(fftw_archive, vsynth_plugins, ['libfftw3f-3.dll'], 'sadsadasd')
zip_e(debilinear_archive, internal_dir, ['debilinear.dll'], 'sadsadasd')
zip_e(debicubic_archive, internal_dir, ['debicubic.dll'], 'sadsadasd')
zip_e(dgdecode_archive, internal_dir, ['DGIndex.exe'], 'sadsadasd')
