from pathlib import Path
import urllib.request
import zipfile
import subprocess
import re
import sys

root = Path(sys.argv[1])
vendor = root / 'vendor'
headers = {
    'GLFW/glfw3.h': 'https://raw.githubusercontent.com/glfw/glfw/3.4/include/GLFW/glfw3.h',
    'GLFW/glfw3native.h': 'https://raw.githubusercontent.com/glfw/glfw/3.4/include/GLFW/glfw3native.h',
    'GLES2/gl2.h': 'https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/main/api/GLES2/gl2.h',
    'GLES2/gl2platform.h': 'https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/main/api/GLES2/gl2platform.h',
    'GLES2/gl2ext.h': 'https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/main/api/GLES2/gl2ext.h',
    'KHR/khrplatform.h': 'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/api/KHR/khrplatform.h',
    'webp/decode.h': 'https://raw.githubusercontent.com/webmproject/libwebp/v1.5.0/src/webp/decode.h',
    'webp/types.h': 'https://raw.githubusercontent.com/webmproject/libwebp/v1.5.0/src/webp/types.h',
}
for path, url in headers.items():
    target = vendor / 'include' / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(urllib.request.urlopen(url, timeout=60).read())
nuget = vendor / 'webview2.zip'
nuget.write_bytes(urllib.request.urlopen('https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/1.0.3800.47/microsoft.web.webview2.1.0.3800.47.nupkg', timeout=60).read())
with zipfile.ZipFile(nuget) as archive:
    (vendor / 'include/WebView2.h').write_bytes(archive.read('build/native/include/WebView2.h'))
package = vendor / 'baseline.zip'
package.write_bytes(urllib.request.urlopen('https://github.com/canfisher/umaipoe-pob/releases/download/r10.1/Umaipoe-PoB-r10.1.zip', timeout=120).read())
(vendor / 'lib').mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(package) as archive:
    for name in ('glfw3', 'libGLESv2', 'WebView2Loader', 'libwebpdecoder'):
        entry = next(p for p in archive.namelist() if p.endswith('engine/' + name + '.dll'))
        dll = vendor / (name + '.dll')
        dll.write_bytes(archive.read(entry))
        listing = subprocess.check_output(['dumpbin', '/exports', str(dll)], text=True)
        exports = re.findall(r'^\s+\d+\s+[0-9A-F]+\s+[0-9A-F]{8}\s+(\S+)', listing, re.M)
        assert exports, name
        definition = vendor / (name + '.def')
        definition.write_text('LIBRARY ' + name + '.dll\nEXPORTS\n' + '\n'.join(exports), encoding='ascii')
        subprocess.run(['lib', '/nologo', '/machine:x64', '/def:' + str(definition), '/out:' + str(vendor / 'lib' / (name + '.lib'))], check=True)
