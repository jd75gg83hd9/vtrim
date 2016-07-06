import importlib
import logging
import os
import subprocess
import urllib.request

try:
    import autobahn
except ImportError:
    print('#########################################')
    print('## autobahn not found - installing...  ##')
    print('#########################################')
    subprocess.call(['internal\python\python.exe', 'internal\get-pip.py'])
    subprocess.call(['internal\python\python.exe', '-m', 'pip', 'install', 'autobahn'])

    # http://stackoverflow.com/questions/25384922/how-to-refresh-sys-path
    import site
    importlib.reload(site)

    importlib.invalidate_caches()

    print('#########################################')
    print('######### installation complete #########')
    print('#########################################')

from videotrim import server_autobahn, settings
settings.set_install_dir(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
settings.setup_logging(logging.INFO)
server_autobahn.start()
