local M=LoadModule('Modules/WickermanCompare')
local json=require('dkjson')
refresh()
local original=build:SaveDB('source')
local catalog=build.itemsTab:GetWickermanCatalog()
local checks=0
local function check(ok,label) assert(ok,label);checks=checks+1 end
local function find(effect)
 for _,entry in ipairs(catalog) do
  local item=build.itemsTab:CreateWickermanItem(entry.name)
  if item.raw:lower():find(effect) then return item end
 end
 error(effect)
end
for _,case in ipairs({
 {'damage against undead','conditionVisceraEnemyUndead','AverageHit'},
 {'consume a corpse within.-of life','conditionVisceraConsumableCorpse','VisceraCorpseLifeAverage'},
}) do
 local item=find(case[1]);local s=M.newSession(build.itemsTab);s.items[item.type]=item
 s.conditions[case[2]]=false;local off=M.calculate(build.itemsTab,s)
 s.conditions[case[2]]=true;local on=M.calculate(build.itemsTab,s)
 check(on.after[case[3]]>off.after[case[3]],'Condition had no effect '..case[2])
 check(build:SaveDB('source')==original,'Condition modified original')
end
local flask=new('Item'):Item('Rarity: Normal\nBismuth Flask\nBismuth Flask')
build.itemsTab:AddItem(flask,true);build.itemsTab.slots['Flask 1']:SetSelItemId(flask.id)
build.itemsTab.slots['Flask 1'].active=true;refresh()
local equipped=build:SaveDB('flask-source');local s=M.newSession(build.itemsTab)
s.flasksOff=false;local active=M.calculate(build.itemsTab,s)
s.flasksOff=true;local inactive=M.calculate(build.itemsTab,s)
check(active.after.FireResist>inactive.after.FireResist,'Flask disable ineffective')
check(build:SaveDB('flask-source')==equipped,'Flask toggle modified original')
local file=assert(io.open(AUDIT_WORK..'/conditions.json','w'));file:write(json.encode({passed=checks,flask_on_fire_resist=active.after.FireResist,flask_off_fire_resist=inactive.after.FireResist,conditions=true,source_unchanged=true}));file:close()
print('CONDITIONS PASSED',checks)
