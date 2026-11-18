from pathlib import Path
import zipfile

root=Path(__file__).resolve().parents[2]
work=Path(__file__).resolve().parent
app=root/'outputs/pob330-r13/Umaipoe-PoB-r13'
engine=app/'PoE1-3.30'
with zipfile.ZipFile(root/'outputs/pob330-r12.2/Umaipoe-PoB-r12.2.zip') as z:
    source=z.read('PoE1-3.30/Classes/ItemsTab.lua').decode('utf-8-sig').replace('\r\n','\n')
    launch=z.read('PoE1-3.30/Launch.lua').decode('utf-8-sig')
old='\t-- Passive tree dropdown controls'
new='''\tself.controls.wickermanCompare = new("ButtonControl"):ButtonControl({"TOPLEFT",prevSlot,"BOTTOMLEFT"}, {0, 6, 216, 22}, "살덩이 조합 비교", function()
        LoadModule("Modules/WickermanCompare").open(self)
    end)
    self.controls.wickermanCompare.shown = self.controls.wickermanHeader.shown
    self.controls.wickermanCompare.tooltipText = "코드·XML로 불러온 현재 빌드에서 네 부위와 조건을 비교합니다. 원본은 바뀌지 않습니다."
    prevSlot = self.controls.wickermanCompare

'''+old
assert source.count(old)==1
source=source.replace(old,new)
source=source.replace('function ItemsTabClass:OpenWickermanPopup(source)','function ItemsTabClass:OpenWickermanPopup(source, compareOptions)')
old='''        self:AddItem(preview, true)
        if not source then self.slots[preview.type]:SetSelItemId(preview.id) end'''
new='''        if compareOptions then
            main:ClosePopup()
            compareOptions.onSave(preview)
            return
        end
'''+old
assert source.count(old)==1
source=source.replace(old,new)
source=source.replace('function() return item and item.id and "수정 저장" or source and "아이템 추가" or "추가하고 장착" end','function() return compareOptions and "비교 조합에 사용" or item and item.id and "수정 저장" or source and "아이템 추가" or "추가하고 장착" end')
source=source.replace('controls.raw.enabled = function() return preview ~= nil end','controls.raw.enabled = function() return preview ~= nil and not compareOptions end')
source=source.replace('controls.cancel = new("ButtonControl"):ButtonControl(nil, {165, 492, 100, 25}, "취소", function() main:ClosePopup() end)', 'controls.cancel = new("ButtonControl"):ButtonControl(nil, {165, 492, 100, 25}, "취소", function() main:ClosePopup(); if compareOptions then compareOptions.onCancel() end end)')
(engine/'Classes/ItemsTab.lua').write_text(source,encoding='utf-8')
(engine/'Modules/WickermanCompare.lua').write_bytes((work/'WickermanCompare.lua').read_bytes())
(engine/'Launch.lua').write_text(launch.replace('r12.2','r13'),encoding='utf-8')
print('Patched isolated r13; r12.2 preserved')
