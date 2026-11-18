"""Run a GUI smoke test on a private desktop without changing the active desktop."""
import ctypes as c
from ctypes import wintypes as w
import os
import subprocess
import sys
import uuid

class Startup(c.Structure):
    _fields_=[("cb",w.DWORD),("reserved",w.LPWSTR),("desktop",w.LPWSTR),("title",w.LPWSTR),
              *[(n,w.DWORD) for n in ("x","y","width","height","cols","rows","fill","flags")],
              ("show",w.WORD),("cbReserved",w.WORD),("reserved2",c.c_void_p),
              *[(n,w.HANDLE) for n in ("stdin","stdout","stderr")]]

class Process(c.Structure):
    _fields_=[("process",w.HANDLE),("thread",w.HANDLE),("pid",w.DWORD),("tid",w.DWORD)]

u=c.WinDLL("user32",use_last_error=True); k=c.WinDLL("kernel32",use_last_error=True)
u.CreateDesktopW.argtypes=[w.LPCWSTR,w.LPCWSTR,c.c_void_p,w.DWORD,w.DWORD,c.c_void_p]
u.CreateDesktopW.restype=w.HANDLE
u.CloseDesktop.argtypes=[w.HANDLE]
k.CreateProcessW.argtypes=[w.LPCWSTR,w.LPWSTR,c.c_void_p,c.c_void_p,w.BOOL,w.DWORD,c.c_void_p,w.LPCWSTR,c.POINTER(Startup),c.POINTER(Process)]
k.CloseHandle.argtypes=[w.HANDLE]
k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD]
k.GetExitCodeProcess.argtypes=[w.HANDLE,c.POINTER(w.DWORD)]
name="UmaipoeTest"+uuid.uuid4().hex
desk=u.CreateDesktopW(name,None,None,0,0x000F01FF,None)
if not desk:raise c.WinError(c.get_last_error())
si=Startup();si.cb=c.sizeof(si);si.desktop=name;info=Process()
try:
    cmd=c.create_unicode_buffer(subprocess.list2cmdline(sys.argv[1:]))
    if not k.CreateProcessW(None,cmd,None,None,False,0x08000000,None,os.getcwd(),c.byref(si),c.byref(info)):
        raise c.WinError(c.get_last_error())
    try:
        k.WaitForSingleObject(info.process,0xffffffff)
        code=w.DWORD()
        if not k.GetExitCodeProcess(info.process,c.byref(code)):raise c.WinError(c.get_last_error())
        sys.exit(code.value)
    finally:
        k.CloseHandle(info.thread);k.CloseHandle(info.process)
finally:
    u.CloseDesktop(desk)
