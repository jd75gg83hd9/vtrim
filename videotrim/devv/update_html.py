import os
import shutil

from videotrim import settings

# for development only
# copies html from git src dir into into install dir
shutil.copyfile('template.html', settings.html_template())

release_dir = r'C:\vid-rls'
dst_dir = os.path.join(release_dir, 'internal', 'python', 'videotrim')
vt_dir = os.path.dirname(os.getcwd())
for f in os.listdir(vt_dir):
    if f.endswith('.py'):
        src = os.path.join(vt_dir, f)
        dst = os.path.join(dst_dir, f)
        print('copying %s to %s' % (src, dst_dir))
        shutil.copy(os.path.join(vt_dir, f), os.path.join(dst_dir, f))