import ctypes
import json
import os
import sys
import zlib
from pathlib import Path

base = Path(__file__).resolve().parents[2] / 'outputs/pob330-r7/Umaipoe-PoB-3.30-KR-r7/PoE1-3.30'
base = Path(os.environ.get('POB_R7_TEST_ENGINE', str(base))).resolve()
workspace = Path(__file__).resolve().parent
wrapper_path = base / 'HeadlessWrapper.lua'
build_path, audit_path = [Path(arg).resolve() for arg in sys.argv[1:]]
build_data, audit = build_path.read_bytes(), audit_path.read_bytes()
os.chdir(base)
os.environ['CI'] = '1'
with os.add_dll_directory(str(base)):
    lua = ctypes.CDLL(str(base / 'lua51.dll'))
lua.luaL_newstate.restype = ctypes.c_void_p
lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lua.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
lua.lua_tolstring.restype = ctypes.c_void_p
lua.lua_pushlstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
lua.lua_pushcclosure.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
lua.lua_setfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
lua.lua_close.argtypes = [ctypes.c_void_p]
state = lua.luaL_newstate()
lua.luaL_openlibs(state)


def codec(transform):
    @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)
    def callback(state):
        size = ctypes.c_size_t()
        pointer = lua.lua_tolstring(state, 1, ctypes.byref(size))
        data = transform(ctypes.string_at(pointer, size.value))
        lua.lua_pushlstring(state, data, len(data))
        return 1
    return callback


inflate, deflate = codec(zlib.decompress), codec(zlib.compress)
for name, callback in [(b'_NativeInflate', inflate), (b'_NativeDeflate', deflate)]:
    lua.lua_pushcclosure(state, callback, 0)
    lua.lua_setfield(state, -10002, name)


def run(script):
    status = lua.luaL_loadstring(state, script) or lua.lua_pcall(state, 0, 0, 0)
    if status:
        raise RuntimeError(ctypes.string_at(lua.lua_tolstring(state, -1, None)).decode('utf-8', 'replace'))


base_lua, work_lua = json.dumps(base.as_posix()), json.dumps(workspace.as_posix())
overrides = f'''
AUDIT_WORK = {work_lua}
Inflate = _NativeInflate
Deflate = _NativeDeflate
function GetScriptPath() return {base_lua} end
function GetRuntimePath() return {base_lua} end
function GetWorkDir() return {base_lua} end
function GetUserPath() return {work_lua} end
local originalOpen = io.open
function io.open(path, mode)
    mode = mode or 'r'
    if path == 'Data/ModCache.lua' and mode == 'w' then path = AUDIT_WORK .. '/ModCache.generated.lua' end
    if tostring(path):lower():match('settings%.xml$') then
        if mode == 'r' or mode == 'rb' then return nil end
        path = AUDIT_WORK .. '/test-Settings.xml'
    end
    if mode ~= 'r' and mode ~= 'rb' then
        if not tostring(path):gsub('\\\\', '/'):find(AUDIT_WORK .. '/', 1, true) then
            return nil, 'Test output outside workspace'
        end
    end
    return originalOpen(path, mode)
end
'''
prefix = 'arg={}; package.path="./lua/?.lua;./lua/?/init.lua;./?.lua;"..package.path; package.cpath="./?.dll;"..package.cpath\n'
wrapper = wrapper_path.read_text(encoding='utf-8-sig').split('\n', 1)[1]
wrapper = wrapper.replace('dofile("Launch.lua")', overrides + '\ndofile("Launch.lua")').replace('io.read("*l")', 'error(mainObject.promptMsg)')
try:
    import time
    started = time.perf_counter()
    run((prefix + wrapper).encode())
    print('STARTUP_WALL_SECONDS', time.perf_counter()-started)
    if os.environ.get('TEST_VARIANT') == 'fast':
        run(b'assert(main.mode == "LIST"); assert(next(main.tree) == nil); assert(main.uniqueDB.loading); assert(next(main.uniqueDB.list) == nil)')
    if not os.environ.get('BENCHMARK_ONLY'):
        run(b'loadBuildFromXML([====[' + build_data + b']====], "Progression")\nfunction refresh() build.buildFlag=true; runCallback("OnFrame") end\n' + audit)
finally:
    lua.lua_close(state)


