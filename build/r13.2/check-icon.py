from pathlib import Path
from ctypes import wintypes as w
import ctypes as c
import hashlib
import json
import struct
import sys

k=c.WinDLL("kernel32",use_last_error=True)
def fn(name,restype,*arguments):
    f=getattr(k,name);f.restype=restype;f.argtypes=arguments;return f
load=fn("LoadLibraryExW",w.HMODULE,w.LPCWSTR,w.HANDLE,w.DWORD)
unload=fn("FreeLibrary",w.BOOL,w.HMODULE)
find=fn("FindResourceW",w.HRSRC,w.HMODULE,c.c_void_p,c.c_void_p)
loadres=fn("LoadResource",w.HGLOBAL,w.HMODULE,w.HRSRC)
lock=fn("LockResource",c.c_void_p,w.HGLOBAL)
size=fn("SizeofResource",w.DWORD,w.HMODULE,w.HRSRC)
callback=c.WINFUNCTYPE(w.BOOL,w.HMODULE,c.c_void_p,c.c_void_p,c.c_ssize_t)
enum=fn("EnumResourceNamesW",w.BOOL,w.HMODULE,c.c_void_p,callback,c.c_ssize_t)
def icons(path, numeric):
    h=load(str(path.resolve()),None,2)
    if not h:raise c.WinError(c.get_last_error())
    try:
        ids=[]
        def each(module,typ,name,param):
            ids.append(name if name<=65535 else c.wstring_at(name))
            return True
        assert enum(h,14,callback(each),0) and ids==([101] if numeric else ["GLFW_ICON"]),ids
        def read(which,kind):
            name=c.cast(c.c_wchar_p(which),c.c_void_p) if isinstance(which,str) else which
            r=find(h,name,kind);assert r
            n=size(h,r);p=lock(loadres(h,r));assert p and n
            return c.string_at(p,n)
        group=read(ids[0],14)
        reserved,typ,count=struct.unpack_from("<HHH",group)
        assert (reserved,typ)==(0,1) and count>0 and len(group)>=6+14*count
        images=[]
        for i in range(count):
            *_,length,idx=struct.unpack_from("<BBBBHHIH",group,6+14*i)
            data=read(idx,3);assert len(data)==length
            images.append(hashlib.sha256(data).hexdigest())
        return images
    finally:unload(h)

work=Path(__file__).resolve().parent
old=icons(work/"profile-test/shared-program/pob-zh.exe",False)
new=icons(work/"host-build/pob-zh.exe",True)
assert old==new
print(json.dumps(dict(resource_id=101,icon_images_preserved=len(new))))
