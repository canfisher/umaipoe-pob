local json = require('dkjson')
local M = LoadModule('Modules/WickermanCompare')
local checks, results = 0, {}
local function check(ok, label) assert(ok, label); checks = checks + 1 end
local function same(a,b,label)
 if a==nil and b==nil then return end
 check(type(a)==type(b),label..' type '..tostring(a)..' '..tostring(b))
 if type(a)=='number' then check(a==b or math.abs(a-b)<=math.max(0.00001,math.abs(a)*1e-7),label..' value '..tostring(a)..' '..tostring(b)) end
end
refresh()
local original=build:SaveDB('source')
local catalog=build.itemsTab:GetWickermanCatalog()
local function find(effect)
 for _,entry in ipairs(catalog) do
  local item=build.itemsTab:CreateWickermanItem(entry.name)
  if item.raw:lower():find(effect,1,true) then return item end
 end
 error('Missing effect '..effect)
end
local bases={find('damage against undead'),find('consume a corpse within'),find('petrification'),find('chance to avoid corrupted blood')}
for index,scenario in ipairs({
 {boss='None',off=false,enabled=false},
 {boss='Boss',off=true,enabled=true},
 {boss='Pinnacle',off=false,enabled=true},
 {boss='Uber',off=true,enabled=false},
}) do
 loadBuildFromXML(original,'source');refresh()
 local s=M.newSession(build.itemsTab)
 s.boss=scenario.boss;s.flasksOff=scenario.off
 s.conditions.conditionVisceraEnemyUndead=scenario.enabled
 s.conditions.conditionVisceraConsumableCorpse=scenario.enabled
 s.conditions.conditionVisceraEnemyRare=false
 for _,item in ipairs(bases) do s.items[item.type]=item end
 local body=build.itemsTab:CreateWickermanItem('Corrupted Carapace')
 body.implicitModLines[1].range=0.1;body:BuildAndParseRaw();s.items[body.type]=body
 local before=build:SaveDB('before')
 local beforeCache=GlobalCache
 s.result=M.calculate(build.itemsTab,s)
 local code=M.exportCode(build.itemsTab,s)
 local xml=Inflate(common.base64.decode(code:gsub('-','+'):gsub('_','/')))
 check(build:SaveDB('before')==before,'Export modified source')
 check(GlobalCache==beforeCache,'Cache changed')
 loadBuildFromXML(xml,'comparison');refresh()
 local equipped=build.calcsTab.mainOutput
 for _,group in ipairs(M.groups) do
  for _,row in ipairs(group.rows) do
   local expected=s.result.after[row[1]]
   if row[1]=='FullDPS' and expected==nil then check(equipped.FullDPS==0,'Unexpected full DPS')
   else same(expected,equipped[row[1]],scenario.boss..' '..row[1]) end
  end
 end
 for _,slot in ipairs(M.slots) do
  local expected=s.items[slot]
  local actual=build.itemsTab.items[build.itemsTab.slots[slot].selItemId]
  check(not expected and not actual or expected and actual and expected:BuildRaw()==actual:BuildRaw(),'Equipped item mismatch '..slot)
 end
 if scenario.off then
  for n=1,5 do check(not build.itemsTab.slots['Flask '..n].active,'Active flask persisted') end
 end
 local path=AUDIT_WORK..'/crosscheck-reopened.xml'
 build.dbFileName=path;build:SaveDBFile()
 local file=assert(io.open(path,'rb'));local saved=file:read('*a');file:close()
 local avg=equipped.AverageHit
 loadBuildFromXML(saved,'saved-again');refresh()
 same(avg,build.calcsTab.mainOutput.AverageHit,'Save/reopen')
 results[index]={boss=scenario.boss,flasks_off=scenario.off,conditions=scenario.enabled,average_hit=avg}
end
loadBuildFromXML(original,'source');refresh()
local reopened=build:SaveDB('source')
for name,value in pairs({['original.xml']=original,['original-reopened.xml']=reopened}) do local f=assert(io.open(AUDIT_WORK..'/'..name,'w'));f:write(value);f:close() end
local file=assert(io.open(AUDIT_WORK..'/crosscheck.json','w'))
file:write(json.encode({passed=checks,cases=results,export_equipment_and_settings=true,save_reload=true,source_unchanged=true},{indent=true}));file:close()
print('CROSSCHECK PASSED',checks)
