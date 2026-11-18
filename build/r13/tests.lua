local json = require('dkjson')
local M = LoadModule('Modules/WickermanCompare')
local checks, cases = 0, { }
local function check(ok, label) assert(ok, label); checks = checks + 1 end
local function same(a, b, label) check(math.abs(a-b) <= math.max(0.000001, math.abs(a)*1e-8), label) end
refresh()
local original = build:SaveDB('original')
local oldInput, oldPlaceholder = json.encode(build.configTab.input), json.encode(build.configTab.placeholder)
local s = M.newSession(build.itemsTab)
local cache = GlobalCache
local start = os.clock()
local equal = M.calculate(build.itemsTab, s)
same(equal.before.AverageHit,equal.after.AverageHit,'Identical setup differs')
same(equal.before.AverageHit,build.calcsTab.mainOutput.AverageHit,'Baseline differs from active build')
check(GlobalCache==cache,'Global cache replaced')
check(build:SaveDB('original')==original,'Source XML changed')
check(json.encode(build.configTab.input)==oldInput,'Source inputs changed')
check(json.encode(build.configTab.placeholder)==oldPlaceholder,'Source placeholders changed')
cases.identical={before=equal.before.AverageHit,after=equal.after.AverageHit,seconds=os.clock()-start}
local body=build.itemsTab:CreateWickermanItem('Corrupted Carapace')
body.implicitModLines[1].range=0.1;body:BuildAndParseRaw()
s.items['Wickerman Torso']=body
local add=M.calculate(build.itemsTab,s)
check(add.after.AverageHit>add.before.AverageHit,'Life cost damage not applied')
cases.carapace={before=add.before.AverageHit,after=add.after.AverageHit,line=body.raw}
for _,boss in ipairs({'None','Boss','Pinnacle','Uber'}) do
 s.boss=boss;s.conditions.conditionVisceraEnemyRare=false
 local r=M.calculate(build.itemsTab,s)
 check(r.before.AverageHit>0 and r.after.AverageHit>r.before.AverageHit,'Boss comparison failed '..boss)
 check(build:SaveDB('original')==original,'Boss scenario mutated source '..boss)
 cases[boss]={before=r.before.AverageHit,after=r.after.AverageHit}
end
s.boss='Boss';s.conditions.conditionVisceraEnemyRare=true
check(not pcall(M.calculate,build.itemsTab,s),'Contradictory monster class accepted')
s.conditions.conditionVisceraEnemyRare=false
s.items['Wickerman Torso']=build.itemsTab:CreateWickermanItem('Chimeral Eye')
check(not pcall(M.calculate,build.itemsTab,s),'Wrong slot accepted')
check(GlobalCache==cache,'Failure leaked global cache')
check(build:SaveDB('original')==original,'Failure changed source')
s.items['Wickerman Torso']=body;s.flasksOff=true
local off=M.calculate(build.itemsTab,s)
check(off.after.AverageHit>0,'Flasks off failed')
check(build:SaveDB('original')==original,'Flasks changed original')
local incomplete
for _,entry in ipairs(build.itemsTab:GetWickermanCatalog()) do
 local item=build.itemsTab:CreateWickermanItem(entry.name)
 if #M.unsupported({[item.type]=item})>0 then incomplete=item;break end
end
check(incomplete~=nil,'No unsupported fixture')
s.items[incomplete.type]=incomplete
s.result=M.calculate(build.itemsTab,s)
check(#s.result.afterMissing>0,'Unsupported line not shown')
check(M.report(s):find('미계산',1,true)~=nil,'Report missing support warning')
check(M.report(s):find('그 외 레벨',1,true)~=nil,'Report missing assumptions')
local uiSession,controls=M.open(build.itemsTab)
check(controls.calculate~=nil and controls.copy~=nil,'Missing comparison controls')
check(controls.copy.enabled()==false,'Stale report copy enabled')
main:ClosePopup()
check(build:SaveDB('original')==original,'Opening popup changed source')
local path=AUDIT_WORK..'/비교 후 저장.xml'
build.dbFileName=path;build:SaveDBFile()
local file=assert(io.open(path,'rb'));local saved=file:read('*a');file:close()
loadBuildFromXML(saved,'reopened');refresh()
same(build.calcsTab.mainOutput.AverageHit,equal.before.AverageHit,'Save/reload changed damage')
local out=assert(io.open(AUDIT_WORK..'/tests.json','w'));out:write(json.encode({passed=checks,cases=cases,source_unchanged=true,save_reload=true},{indent=true}));out:close()
print('COMPARISON TESTS PASSED',checks)
