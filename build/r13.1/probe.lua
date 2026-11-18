local base = os.getenv("GEM_TEST_DIR")
local function write(name, data)
    local file = assert(io.open(base.."/"..name, "wb"))
    file:write(data)
    file:close()
end
local function open(name)
    local f = assert(io.open(base.."/"..name, "rb"))
    local xml = f:read("*a"); f:close()
    main:SetMode("BUILD", false, "Gem names", xml)
end
local expected = {["Arcanist Brand"]="신비학자 낙인",Frostbite="동상",["Elemental Weakness"]="원소 약화",["Assassin's Mark"]="암살자의 징표"}
local stage = 0
local function run()
    if stage == 0 then stage=1; open("gems.xml"); return end
    local b = main.modes.BUILD
    if main.mode ~= "BUILD" or not b.skillsTab or not b.skillsTab.socketGroupList[1] or main.newMode then return end
    local tab = b.skillsTab
    tab:SetDisplayGroup(tab.socketGroupList[1])
    local draws, widths = {}, {}
    local draw,width = DrawString,DrawStringWidth
    local function rendered(s)
        return PobToolsGetTranslate() and (PobToolsTranslateDisplay(s) or s) or s
    end
    DrawString = function(x,y,a,h,f,s,...)
        if expected[s] then draws[s]=rendered(s) end
        return draw(x,y,a,h,f,s,...)
    end
    DrawStringWidth = function(h,f,s,...)
        if expected[s] then widths[s]=rendered(s) end
        return width(h,f,s,...)
    end
    local original = PobToolsGetTranslate()
    local ok,err=pcall(function()
        for _,enabled in ipairs({true,false}) do
            PobToolsSetTranslate(enabled)
            for i,gem in ipairs(tab.displayGroup.gemList) do
                local control=tab.gemSlots[i].nameSpec
                draws[gem.nameSpec]=nil; widths[gem.nameSpec]=nil
                control:Draw({x=0,y=0,width=1280,height=720},true)
                local want=assert(expected[gem.nameSpec])
                assert(draws[gem.nameSpec]==(enabled and want or gem.nameSpec), tostring(draws[gem.nameSpec]).." drawing "..gem.nameSpec)
                assert(widths[gem.nameSpec]==draws[gem.nameSpec],"width "..gem.nameSpec)
                assert(control.buf==gem.nameSpec)
            end
            assert(#tab.displayGroup.gemList==4)
        end
    end)
    DrawString,DrawStringWidth=draw,width
    PobToolsSetTranslate(original)
    assert(ok,err)
    if stage==1 then
        write("reopened.xml",assert(b:SaveDB("fixture"))); stage=2; open("reopened.xml")
    else
        write("native-gem-check.json",require("dkjson").encode({names=expected,drawWidthMatches=true,englishMode=true,roundTrip=true}))
        stage=3
    end
end
return function()
    if stage>=3 then return end
    local ok,err=pcall(run)
    if not ok then stage=3; write("probe-error.txt",tostring(err)) end
end
