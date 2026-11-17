from pathlib import Path
import ctypes,os,json
root=Path(__file__).resolve().parents[2]
app=root/'outputs/pob330-r12/Umaipoe-PoB-r12'
base=app/'PoE1-3.30';os.chdir(base)
with os.add_dll_directory(str(base)):lua=ctypes.CDLL(str(base/'lua51.dll'))
lua.luaL_newstate.restype=ctypes.c_void_p
for name,args in [('luaL_openlibs',[ctypes.c_void_p]),('luaL_loadstring',[ctypes.c_void_p,ctypes.c_char_p]),('lua_pcall',[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int]),('lua_tolstring',[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p]),('lua_close',[ctypes.c_void_p])]:getattr(lua,name).argtypes=args
lua.lua_tolstring.restype=ctypes.c_char_p
output=root/'work/pob330-r12/native-legion.json'
script=('package.path="lua/?.lua;"..package.path; local data=dofile("Data/TimelessJewelData/LegionPassives.lua"); local f=assert(io.open('+json.dumps(output.as_posix())+',"w")); f:write(require("dkjson").encode(data)); f:close()').encode()
s=lua.luaL_newstate();lua.luaL_openlibs(s)
try:
 if lua.luaL_loadstring(s,script) or lua.lua_pcall(s,0,0,0):raise RuntimeError(lua.lua_tolstring(s,-1,None).decode())
finally:lua.lua_close(s)
d=json.loads((app/'Data/timeless_jewels.json').read_text(encoding='utf-8'));native=json.loads(output.read_text(encoding='utf-8'));changes=[]
baseline=json.loads((app.parent/'backups/before-jewel-display/timeless_jewels.json').read_text(encoding='utf-8'))
print('native keys',list(native))
for key in ['additions','nodes']:
 assert len(d[key])==len(native[key]),key
 for old,new,original in zip(d[key],native[key],baseline[key]):
  assert old['id']==new['id'],(old['id'],new['id'])
  for field in ['dn','sd','sortedStats','stats','ks']:
   if field not in new:continue
   value=new[field]
   if field=='sd' and len(original['sd'])!=len(value):value=original['sd']
   if field=='sd':value=[before if before.casefold()==after.casefold() else after for before,after in zip(original['sd'],value)]
   if field=='stats':value={k:{a:b for a,b in v.items() if a in ['fmt','index','min','max']}for k,v in value.items()} if isinstance(value,dict) else {}
   if old.get(field)!=value:changes.append([old['id'],field,old.get(field),value]);old[field]=value
d['meta']['sourceVersion']='Umaipoe r12 native 3.30; original node/LUT order preserved'
(app/'Data/timeless_jewels.json').write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
(app.parent/'native-jewel-sync.json').write_text(json.dumps({'changes':changes,'arrayOrderPreserved':True},ensure_ascii=False,indent=2),encoding='utf-8')
print('synchronized changed fields',len(changes))
