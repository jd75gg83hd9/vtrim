__author__ = 'LivingRoom'
import os
lib_dir = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())), 'lib')
download_dir = os.path.join(lib_dir, 'download')
if not os.path.isdir(lib_dir):
    os.mkdir(lib_dir)
if not os.path.isdir(download_dir):
    os.mkdir(download_dir)
