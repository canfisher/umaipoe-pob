local M = { }
local calcs = require("Modules.Calcs")
M.slots = { "Wickerman Head", "Wickerman Torso", "Wickerman Upper Limb", "Wickerman Lower Limb" }
M.parts = { "머리", "몸통", "팔", "다리" }
M.conditions = {
    { "conditionVisceraEnemyNearBanner", "내 깃발 범위" },
    { "conditionVisceraEnemyUndead", "언데드 대상" },
    { "conditionVisceraEnemyBeast", "야수 대상" },
    { "conditionVisceraEnemyAnimal", "동물에게 피격" },
    { "conditionVisceraEnemyRare", "희귀 대상" },
    { "conditionVisceraConsumableCorpse", "시체 공급 있음" },
    { "conditionVisceraRecoupingLife", "생명력 회생 중" },
    { "conditionEnemyCursed", "저주된 대상" },
}
M.bosses = {
    { label = "일반 몬스터", val = "None" }, { label = "지도 보스", val = "Boss" },
    { label = "일반 엔드보스", val = "Pinnacle" }, { label = "우버 보스", val = "Uber" },
}
M.groups = {
    { label = "피해·자원", rows = {
        { "FullDPS", "전체 DPS · 포함 스킬만" }, { "CombinedDPS", "선택 스킬 합산 DPS" },
        { "AverageHit", "선택 스킬 평균 적중" }, { "Life", "최대 생명력" },
        { "EnergyShield", "에너지 보호막" }, { "ManaUnreserved", "비점유 마나" },
        { "LifeCost", "1회 생명력 소모" }, { "ManaCost", "1회 마나 소모" },
    } },
    { label = "생존·회복", rows = {
        { "PhysicalMaximumHitTaken", "물리 최대 피격" }, { "FireMaximumHitTaken", "화염 최대 피격" },
        { "ColdMaximumHitTaken", "냉기 최대 피격" }, { "LightningMaximumHitTaken", "번개 최대 피격" },
        { "ChaosMaximumHitTaken", "카오스 최대 피격" }, { "LifeRegenRecovery", "생명력 재생 / 초" },
        { "ManaRegenRecovery", "마나 재생 / 초" }, { "LifeLeechGainRate", "생명력 흡수 / 초" },
    } },
    { label = "살덩이 참고값", rows = {
        { "VisceraCorpseLifePerTrigger", "시체 1회 생명력 회복" }, { "VisceraCorpseManaPerTrigger", "시체 1회 마나 회복" },
        { "VisceraCorpseLifeAverage", "시체 공급 시 평균 회복 / 초" }, { "VisceraAvoidCorruptedBlood", "타락한 피 회피 (%)" },
        { "VisceraPowerChargeOnHit", "적중 시 권능 충전 확률 (%)" }, { "VisceraPetrificationDurationMultiplier", "석화 시간 배율 · 살덩이" },
        { "VisceraWitheredDurationMultiplier", "위축 시간 배율 · 살덩이" }, { "CullPercent", "마무리 타격 기준 (%)" },
    } },
}
local names = LoadModule("Data/VisceraKorean")
local function translated(text)
    return type(PobToolsTranslate) == "function" and PobToolsTranslate(text) or text
end
local function shallow(value)
    return setmetatable(copyTable(value, true), getmetatable(value))
end
local function deep(value, seen)
    if type(value) ~= "table" then return value end
    seen = seen or {}
    if seen[value] then return seen[value] end
    local result = {}; seen[value] = result
    for key, entry in pairs(value) do rawset(result, key, deep(entry, seen)) end
    return setmetatable(result, getmetatable(value))
end
local function cloneItem(item)
    if not item then return false end
    local clone = new("Item"):Item(item:BuildRaw())
    clone.id = item.id
    clone:BuildModList()
    return clone
end
local function itemName(item)
    return item and (names[item.baseName] or item.baseName) or "장착 안 함"
end
local function number(value)
    if type(value) ~= "number" or value ~= value then return "—" end
    if value == math.huge then return "∞" end
    if value == -math.huge then return "-∞" end
    if math.abs(value) >= 1000000 then return string.format("%.3fM", value / 1000000) end
    if math.abs(value) >= 1000 then return string.format("%.1f", value) end
    return string.format("%.3f", value):gsub("0+$", ""):gsub("%.$", "")
end
local function difference(a, b)
    if number(a) == "—" or number(b) == "—" then return "미계산" end
    if math.abs(a) == math.huge or math.abs(b) == math.huge then return a == b and "변화 없음" or number(a) .. " → " .. number(b) end
    local delta = b - a
    local sign = delta > 0 and "+" or ""
    return sign .. number(delta) .. (a ~= 0 and string.format(" (%+.1f%%)", delta / math.abs(a) * 100) or " (기준 0)")
end

function M.newSession(tab)
    local session = { items = { }, original = { }, choices = { }, edited = { }, conditions = { }, group = 1 }
    for _, slot in ipairs(M.slots) do
        local item = tab.items[tab.slots[slot].selItemId]
        session.original[slot], session.items[slot], session.choices[slot] = cloneItem(item), cloneItem(item), "keep"
    end
    for _, condition in ipairs(M.conditions) do session.conditions[condition[1]] = tab.build.configTab.input[condition[1]] == true end
    session.boss = tab.build.configTab.input.enemyIsBoss or "None"
    session.flasksOff = false
    return session
end

function M.proxy(source, items, conditions, boss, flasksOff)
    local proxy = shallow(source)
    proxy.calcsTab = shallow(source.calcsTab)
    proxy.calcsTab.input = copyTable(source.calcsTab.input)
    proxy.calcsTab.build = proxy
    proxy.configTab = shallow(source.configTab)
    local config = proxy.configTab
    config.build, config.input, config.placeholder = proxy, copyTable(source.configTab.input), copyTable(source.configTab.placeholder)
    config.configSets = shallow(source.configTab.configSets)
    local active = shallow(source.configTab.configSets[config.activeConfigSetId])
    active.input, active.placeholder = config.input, config.placeholder
    active.customModsList = copyTable(active.customModsList or {})
    config.configSets[config.activeConfigSetId] = active
    config.varControls = { }
    for key, control in pairs(source.configTab.varControls) do
        local var = key
        local clone = shallow(control)
        clone.SetPlaceholder = function(self, text, notify)
            self.placeholder = tostring(text)
            if notify then config.placeholder[var] = tonumber(text) end
        end
        config.varControls[var] = clone
    end
    for key, value in pairs(conditions or {}) do config.input[key] = value end
    if boss then
        config.input.enemyIsBoss = boss
        if boss ~= source.configTab.input.enemyIsBoss then config.input.presetBossSkills = "None" end
        local control = config.varControls.enemyIsBoss
        for index, entry in ipairs(control.list) do if entry.val == boss then control.selIndex = index end end
    end
    config:BuildModList()
    proxy.itemsTab = shallow(source.itemsTab)
    proxy.itemsTab.build = proxy
    proxy.itemsTab.items = { }
    for id, item in pairs(source.itemsTab.items) do proxy.itemsTab.items[id] = cloneItem(item) end
    proxy.itemsTab.itemSets = deep(source.itemsTab.itemSets)
    proxy.itemsTab.itemOrderList = copyTable(source.itemsTab.itemOrderList)
    proxy.itemsTab.activeItemSet = proxy.itemsTab.itemSets[source.itemsTab.activeItemSetId]
    proxy.itemsTab.slots, proxy.itemsTab.orderedSlots = { }, { }
    for _, slot in ipairs(source.itemsTab.orderedSlots) do
        local clone = shallow(slot)
        if flasksOff and slot.slotName:match("^Flask") then clone.active = false end
        if not slot.nodeId then
            proxy.itemsTab.activeItemSet[slot.slotName].selItemId = clone.selItemId
            proxy.itemsTab.activeItemSet[slot.slotName].active = clone.active
        end
        proxy.itemsTab.slots[slot.slotName] = clone
        table.insert(proxy.itemsTab.orderedSlots, clone)
    end
    for index, slot in ipairs(M.slots) do
        local item = items and items[slot]
        if item ~= nil then
            assert(not item or item.type == slot, "살덩이 부위가 일치하지 않습니다.")
            local clone = cloneItem(item)
            local id = 0
            if clone then
                id = 1
                while proxy.itemsTab.items[id] do id = id + 1 end
                clone.id = id; proxy.itemsTab.items[id] = clone
                table.insert(proxy.itemsTab.itemOrderList, id)
            end
            proxy.itemsTab.slots[slot].selItemId = id
            proxy.itemsTab.activeItemSet[slot].selItemId = id
        end
    end
    -- Calculators write caches into socket groups; isolate those from the open build.
    proxy.skillsTab = shallow(source.skillsTab)
    proxy.skillsTab.build = proxy
    proxy.skillsTab.socketGroupList = deep(source.skillsTab.socketGroupList)
    return proxy
end

function M.exportXML(tab, session)
    assert(session.result, "먼저 비교 계산을 실행하세요.")
    local proxy = M.proxy(tab.build, session.items, session.conditions, session.boss, session.flasksOff)
    local xml = assert(common.xml.ParseXML(tab.build:SaveDB("comparison")))
    local root = xml[1]
    for _, node in ipairs(root) do
        if node.elem == "Items" or node.elem == "Config" then
            local replacement = {elem = node.elem}
            local saver = node.elem == "Items" and proxy.itemsTab or proxy.configTab
            saver:Save(replacement)
            for key in pairs(node) do node[key] = nil end
            for key, value in pairs(replacement) do node[key] = value end
        elseif node.elem == "Build" then
            for index = #node, 1, -1 do
                if type(node[index]) == "table" and (node[index].elem == "PlayerStat" or node[index].elem == "MinionStat") then table.remove(node, index) end
            end
        end
    end
    return assert(common.xml.ComposeXML(root))
end

function M.exportCode(tab, session)
    return common.base64.encode(Deflate(M.exportXML(tab, session))):gsub("+", "-"):gsub("/", "_")
end

function M.unsupported(items)
    local lines = { }
    for index, slot in ipairs(M.slots) do
        local item = items[slot]
        if item then
            if item.base.visceraMissing then table.insert(lines, M.parts[index] .. " · " .. itemName(item) .. ": 효과 자료 미확인") end
            for _, mod in ipairs(item.implicitModLines) do
                if mod.extra or not mod.modList or #mod.modList == 0 then
                    table.insert(lines, M.parts[index] .. " · " .. itemName(item) .. ": " .. translated(itemLib.applyRange(mod.line, mod.range or 0.5)))
                end
            end
        end
    end
    return lines
end

function M.calculate(tab, session)
    assert(tab.build.spec.treeVersion:find("3_30"), "3.30 패시브 트리에서 사용하세요.")
    assert(not (session.boss ~= "None" and session.conditions.conditionVisceraEnemyRare), "보스와 희귀 몬스터 조건은 함께 사용할 수 없습니다.")
    local oldCache = GlobalCache
    local isolatedCache = { cachedData = { MAIN = {}, CALCS = {}, CALCULATOR = {} } }
    GlobalCache = isolatedCache
    local ok, result = xpcall(function()
        local outputs = { }
        for index, items in ipairs({ session.original, session.items }) do
            local proxy = M.proxy(tab.build, items, session.conditions, session.boss, session.flasksOff)
            GlobalCache.cachedData.CALCULATOR = { }
            local _, output = calcs.getMiscCalculator(proxy)
            outputs[index] = deep(output)
        end
        return { before = outputs[1], after = outputs[2], beforeMissing = M.unsupported(session.original), afterMissing = M.unsupported(session.items) }
    end, debug.traceback)
    GlobalCache = oldCache
    if not ok then error(result, 0) end
    return result
end

function M.report(session)
    local result = assert(session.result, "먼저 비교 계산을 실행하세요.")
    local bossLabel = session.boss
    for _, entry in ipairs(M.bosses) do if entry.val == session.boss then bossLabel = entry.label end end
    local lines = { "우마이 한글 PoB r13 · 제웅·살덩이 조합 비교", "같은 빌드·조건에서 네 부위를 교체한 계산입니다. 실전 측정·최적 조합 보장은 아닙니다.",
        "적 설정: " .. bossLabel .. " / 플라스크: " .. (session.flasksOff and "모두 끔" or "원본 활성 상태 유지") }
    for _, entry in ipairs(M.conditions) do table.insert(lines, entry[2] .. ": " .. (session.conditions[entry[1]] and "켬" or "끔")) end
    table.insert(lines, "그 외 레벨·충전·적 처치·적 피해 설정 등은 원본을 유지합니다. 리그 강화 수치는 별도로 넣지 않습니다.")
    for i, slot in ipairs(M.slots) do
        table.insert(lines, M.parts[i] .. ": " .. itemName(session.original[slot]) .. " → " .. itemName(session.items[slot]))
        if session.items[slot] then
            for _, mod in ipairs(session.items[slot].implicitModLines) do table.insert(lines, "  " .. translated(itemLib.applyRange(mod.line, mod.range or 0.5))) end
        end
    end
    for _, group in ipairs(M.groups) do
        table.insert(lines, "\n[" .. group.label .. "] 현재 → 비교 조합 / 차이")
        for _, row in ipairs(group.rows) do
            table.insert(lines, row[2] .. ": " .. number(result.before[row[1]]) .. " → " .. number(result.after[row[1]]) .. " / " .. difference(result.before[row[1]], result.after[row[1]]))
        end
    end
    for _, side in ipairs({ { "현재 조합 미계산", result.beforeMissing }, { "비교 조합 미계산", result.afterMissing } }) do
        table.insert(lines, "\n[" .. side[1] .. "] " .. #side[2] .. "줄")
        for _, line in ipairs(side[2]) do table.insert(lines, line) end
    end
    table.insert(lines, "표에 없는 효과도 있습니다. 차이 0은 효과 없음의 증명이 아닙니다. 미계산 효과는 점수에 더하지 않습니다. 주기 회복·충전 확률은 상시 유지나 EHP 증가를 보장하지 않습니다.")
    return table.concat(lines, "\n")
end

function M.open(tab, session)
    session = session or M.newSession(tab)
    local controls = { }
    local function label(id, x, y, text, size)
        controls[id] = new("LabelControl"):LabelControl({"TOPLEFT", nil, "TOPLEFT"}, { x, y, 0, size or 14 }, (type(text) == "function" and function() return "^7" .. text() end or "^7" .. text))
    end
    local function dirty() session.result, session.error = nil, nil end
    label("note", 24, 24, "현재 빌드의 네 부위를 같은 조건으로 비교합니다. 원본 장비·설정은 변경하지 않습니다.")
    local catalog = tab:GetWickermanCatalog()
    for index, slotName in ipairs(M.slots) do
        local slot, y = slotName, 58 + (index - 1) * 37
        local list = { {label="현재 유지 · " .. itemName(session.original[slot]), kind="keep"}, {label="장착 안 함", kind="none"} }
        if session.edited[slot] then table.insert(list, { label="수치 조정 · " .. itemName(session.edited[slot]), kind="edited" }) end
        for _, item in ipairs(catalog) do
            if item.base.type == slot then table.insert(list, { label=item.label, kind=item.name, searchFilter=item.searchFilter }) end
        end
        label("part" .. index, 24, y + 5, M.parts[index])
        local select = new("DropDownControl"):DropDownControl(nil, {-45, y, 620, 25}, list, function(_, entry)
            session.choices[slot] = entry.kind
            if entry.kind == "keep" then session.items[slot] = cloneItem(session.original[slot])
            elseif entry.kind == "none" then session.items[slot] = false
            elseif entry.kind == "edited" then session.items[slot] = cloneItem(session.edited[slot])
            else session.items[slot] = tab:CreateWickermanItem(entry.kind) end
            dirty()
        end)
        for n, entry in ipairs(list) do if entry.kind == session.choices[slot] then select.selIndex = n end end
        select.maxDroppedWidth = 720
        select.tooltipText = "목록에서 한글 이름을 입력해 찾을 수 있습니다. 새 항목은 기본 중간 수치이므로 ‘수치·효과’에서 실제 값으로 바꾸세요."
        controls["partSelect" .. index] = select
        controls["edit" .. index] = new("ButtonControl"):ButtonControl(nil, {337, y, 124, 25}, "수치·효과", function()
            if not session.items[slot] then return end
            main:ClosePopup()
            tab:OpenWickermanPopup(cloneItem(session.items[slot]), {
                onSave = function(item)
                    session.items[slot], session.edited[slot], session.choices[slot] = cloneItem(item), cloneItem(item), "edited"
                    dirty(); M.open(tab, session)
                end,
                onCancel = function() M.open(tab, session) end,
            })
        end)
        controls["edit" .. index].enabled = function() return session.items[slot] ~= false end
    end
    label("conditionsLabel", 24, 211, "비교 조건 · 양쪽에 똑같이 적용 (그 외 충전·처치 등은 원본 설정 유지)")
    controls.boss = new("DropDownControl"):DropDownControl(nil, {-225, 239, 330, 24}, M.bosses, function(_, entry)
        session.boss = entry.val
        if session.boss ~= "None" then
            session.conditions.conditionVisceraEnemyRare = false
            controls.condition5.state = false
        end
        dirty()
    end)
    for n, entry in ipairs(M.bosses) do if entry.val == session.boss then controls.boss.selIndex = n end end
    controls.flasks = new("DropDownControl"):DropDownControl(nil, {187, 239, 330, 24}, {"플라스크: 원본 활성 상태", "플라스크: 모두 끔"}, function(n) session.flasksOff = n == 2; dirty() end)
    controls.flasks.selIndex = session.flasksOff and 2 or 1
    for index, entry in ipairs(M.conditions) do
        local key = entry[1]
        local control = new("CheckBoxControl"):CheckBoxControl({"TOPLEFT", nil, "TOPLEFT"}, {30 + (index - 1) % 4 * 215, 280 + math.floor((index - 1) / 4) * 30, 18}, entry[2], function(value) session.conditions[key] = value; dirty() end, nil, session.conditions[key])
        control.labelRight = true
        if key == "conditionVisceraEnemyRare" then control.enabled = function() return session.boss == "None" end end
        controls["condition" .. index] = control
    end
    controls.calculate = new("ButtonControl"):ButtonControl(nil, {-310, 333, 180, 27}, "비교 계산", function()
        session.result, session.error = nil, nil
        local ok, result = pcall(M.calculate, tab, session)
        if ok then session.result = result else session.error = "계산 실패 · 원본은 유지됩니다. 조건과 빌드를 확인하세요."; session.detailError = tostring(result) end
    end)
    controls.group = new("DropDownControl"):DropDownControl(nil, {150, 333, 330, 27}, M.groups, function(n) session.group = n end)
    controls.group.selIndex = session.group
    label("status", 24, 370, function()
        if session.error then return "^xFFB34D" .. session.error end
        if not session.result then return "수정 후 ‘비교 계산’을 누르세요. 원본의 주력 스킬·스킬 개수와 설정을 먼저 확인하세요." end
        return "미계산 문구: 현재 " .. #session.result.beforeMissing .. "줄 / 비교 " .. #session.result.afterMissing .. "줄 · 자세한 원문은 결과 복사에서 확인"
    end)
    label("col1", 24, 399, "항목")
    label("col2", 345, 399, "현재 조합")
    label("col3", 515, 399, "비교 조합")
    label("col4", 685, 399, "차이")
    for index = 1, 8 do
        local n, y = index, 426 + (index - 1) * 23
        label("rowName" .. n, 24, y, function() return M.groups[session.group].rows[n][2] end)
        for col, side in ipairs({"before", "after"}) do
            local resultSide = side
            label("row" .. n .. side, 175 + col * 170, y, function()
                local row = M.groups[session.group].rows[n]
                return session.result and number(session.result[resultSide][row[1]]) or "—"
            end)
        end
        label("delta" .. n, 685, y, function()
            local row = M.groups[session.group].rows[n]
            return session.result and difference(session.result.before[row[1]], session.result.after[row[1]]) or "—"
        end)
    end
    label("limits", 24, 618, "미계산·표에 없는 효과는 0으로 평가하지 않습니다. 주기 회복·충전 확률은 상시 유지가 아닙니다.", 13)
    controls.copy = new("ButtonControl"):ButtonControl(nil, {-315, 646, 185, 27}, "결과 복사", function() Copy(M.report(session)) end)
    controls.copy.enabled = function() return session.result ~= nil end
    controls.export = new("ButtonControl"):ButtonControl(nil, {-105, 646, 185, 27}, "조합 코드 복사", function()
        local ok, code = pcall(M.exportCode, tab, session)
        if ok then Copy(code) else session.error = "코드 생성 실패 · 원본은 유지됩니다."; session.detailError = tostring(code) end
    end)
    controls.export.enabled = controls.copy.enabled
    controls.export.tooltipText = "현재 빌드를 바꾸지 않고 비교 조합과 조건을 새 코드로 내보냅니다. 새 빌드로 가져온 뒤 다른 이름으로 저장하세요."
    controls.reset = new("ButtonControl"):ButtonControl(nil, {105, 646, 185, 27}, "원본으로 초기화", function() main:ClosePopup(); M.open(tab) end)
    controls.cancel = new("ButtonControl"):ButtonControl(nil, {315, 646, 185, 27}, "닫기", function() main:ClosePopup() end)
    main:OpenPopup(930, 700, "제웅·살덩이 조합 비교 · 3.30", controls, nil, nil, "cancel")
    return session, controls
end

return M
