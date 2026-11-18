from pathlib import Path
import json
import os
import shutil
import subprocess
import time
import zipfile

work = Path(__file__).resolve().parent
out = work.parents[1]/"outputs/pob330-r13.2"
test = work/"profile-test-fixed"
app = test/"shared-program"
test.mkdir(exist_ok=False)
with zipfile.ZipFile(out/"Umaipoe-PoB-r13.2.zip") as src:
    src.extractall(app)
engine = app/"PoE1-3.30"
fixture = work.parent/"pob330-r13.1/gems.xml"
launch = engine/"Launch.lua"
body = launch.read_text("utf-8")
anchor = "if self.updateReadyFrames >= 3 then"
assert body.count(anchor)==1
launch.write_text(body.replace(anchor, anchor+"""
                    if not self.profileObserved and main.mode == "LIST" and main.modes.LIST.initialised then
                        local mode = main.modes.LIST
                        local rows = {}
                        for _, row in ipairs(mode.list) do rows[#rows+1]=row.fileName or row.folderName end
                        local path = os.getenv("PROFILE_OBSERVATION")
                        local f = assert(io.open(path..".tmp","w"))
                        f:write(require("dkjson").encode({path=main.buildPath,rows=rows,count=#rows}))
                        f:close(); assert(os.rename(path..".tmp",path)); self.profileObserved=true
                    end
"""),encoding="utf-8")
(engine/"Builds").mkdir(exist_ok=True)
shutil.copyfile(fixture,engine/"Builds/shared-decoy.xml")

def observe(account, expected, launcher):
    home=test/account
    home.mkdir(exist_ok=True)
    profile=home/"UmaipoePoB/Auto/UserData"
    result=test/(account+"-"+str(len(reports))+".json")
    env=dict(os.environ, LOCALAPPDATA=str(home),PROFILE_OBSERVATION=result.as_posix())
    for name in ("UMAIPOE_USER_DATA","UMAIPOE_LAUNCHER","UMAIPOE_READY_FILE","UMAIPOE_READY_TOKEN"):
        env.pop(name,None)
    if launcher:
        profile.mkdir(parents=True,exist_ok=True)
        env["UMAIPOE_USER_DATA"]=profile.as_posix()
    si=subprocess.STARTUPINFO()
    si.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow=subprocess.SW_HIDE
    proc=subprocess.Popen([app/"pob-zh.exe","--engine","PoE1-3.30"],cwd=app,env=env,startupinfo=si)
    try:
        for _ in range(180):
            if result.exists() or proc.poll() is not None:break
            time.sleep(.5)
        record=json.loads(result.read_text("utf-8"))
        assert Path(record["path"])==profile/"Builds",record
        assert record["count"]==len(expected) and sorted(record["rows"])==sorted(expected),record
        reports.append(dict(profile=account,launcher=launcher,rows=expected))
    finally:
        if proc.poll() is None:proc.terminate()
        proc.wait(15)
    return profile/"Builds"

reports=[]
a=observe("A",[],False)
shutil.copyfile(fixture,a/"A.xml")
observe("A",["A.xml"],True)
b=observe("B",[],True)
shutil.copyfile(fixture,b/"B.xml")
observe("B",["B.xml"],False)
observe("A",["A.xml"],False)
assert not list((app/"PobTools/logs").glob("crash-*-engine.txt")), "Native startup crash"
(out/"profile-verification.json").write_text(json.dumps(reports,indent=2),encoding="utf-8")
print("Verified native lists in 5 launches")
