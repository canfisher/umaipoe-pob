    UmaipoeFarm::Catalog farmCatalog_;
    std::string farmSeason_, farmError_, farmSearch_, farmNotice_;
    bool farmReady_ = false;

    bool farmLoad() {
        if (farmSeason_ == viewTag) return farmReady_;
        farmSeason_ = viewTag; farmReady_ = false;
        try {
            std::string data;
            if (!PlannerReadFile(exeDir + L"Data\\umaipoe_atlas_farming.json", data))
                throw std::runtime_error(u8"파밍 분류 자료를 읽을 수 없습니다.");
            farmCatalog_.Load(UmaipoeFarm::Json::parse(data));
            if (farmCatalog_.version != viewTag || farmCatalog_.nodes.size() != tree.nodes.size())
                throw std::runtime_error(u8"현재 트리와 파밍 자료의 버전이 다릅니다. 자동 배치를 중지했습니다.");
            for (const auto& n : tree.nodes) {
                if (!farmCatalog_.nodes.count(n.id)) throw std::runtime_error(u8"파밍 자료에 없는 노드가 있습니다.");
                std::vector<int> adjacent;
                for (int i : n.adj) adjacent.push_back(tree.nodes.at(i).id);
                std::sort(adjacent.begin(), adjacent.end());
                if (adjacent != farmCatalog_.nodes.at(n.id).adjacent)
                    throw std::runtime_error(u8"트리 연결이 변경되어 자동 배치를 중지했습니다.");
            }
            farmReady_ = true; farmError_.clear();
        } catch (const std::exception& e) { farmError_ = e.what(); }
        return farmReady_;
    }

    void farmApply(UmaipoeFarm::State state) {
        state = UmaipoeFarm::Normalize(farmCatalog_, std::move(state));
        const auto result = UmaipoeFarm::Calculate(farmCatalog_, state);
        AtlasBuildFile candidate = buildFile;
        const bool newBuild = candidate.Active().farming.empty();
        if (newBuild) candidate.active = candidate.AddBuild(u8"파밍 자동 배치");
        auto& entry = candidate.Active();
        entry.farming = UmaipoeFarm::Encode(state).dump();
        entry.alloc = result.nodes; entry.targets = result.targets;
        entry.blocked.assign(state.excluded.begin(), state.excluded.end());
        for (auto it = entry.variants.begin(); it != entry.variants.end();)
            if (!std::binary_search(result.nodes.begin(), result.nodes.end(), it->first)) it = entry.variants.erase(it);
            else ++it;
        candidate.version = tree.Version();
        if (!candidate.Save(exeDir)) {
            farmNotice_ = u8"저장하지 못했습니다. 기존 전략은 그대로이며 다시 시도할 수 있습니다.";
            return;
        }
        buildFile = std::move(candidate);
        tree.ApplyAllocIds(result.nodes); tree.ApplyTargetIds(result.targets);
        tree.ApplyBlockedIds(buildFile.Active().blocked); tree.ApplyVariantIds(buildFile.Active().variants);
        undo.valid = false; panelDirty = true;
        farmNotice_ = newBuild ? u8"기존 전략을 보존하고 새 파밍 전략을 저장했습니다." : u8"선택과 노드를 저장했습니다.";
    }

    void renderFarmingPanel() {
        if (!ImGui::CollapsingHeader(u8"원하는 파밍으로 자동 배치", ImGuiTreeNodeFlags_DefaultOpen)) return;
        if (!farmLoad()) { ImGui::TextWrapped("%s", farmError_.c_str()); return; }
        if (planningMode || !onCanonicalSeason()) {
            ImGui::TextWrapped(u8"현재 시즌의 일반 편집에서 사용할 수 있습니다. 먼저 계획 모드를 마쳐 주세요."); return;
        }
        auto state = UmaipoeFarm::Decode(farmCatalog_, buildFile.Active().farming);
        bool changed = false;
        ImGui::TextWrapped(u8"파밍을 누르면 연결 경로까지 자동 배치됩니다. 먼저 고른 파밍부터 번갈아 배치합니다.");
        ImGui::SetNextItemWidth(-1);
        ImGui::InputTextWithHint("##farmsearch", u8"파밍 찾기: 탐험, 군단, 의식...", &farmSearch_);
        const float width = ImGui::GetContentRegionAvail().x;
        ImGui::BeginChild("##farmcategories", ImVec2(0, PobUi::D(172)), true);
        int shown = 0;
        for (const auto& c : farmCatalog_.categories) {
            if (!farmSearch_.empty() && c.name.find(farmSearch_) == std::string::npos && c.id.find(ToLowerAscii(farmSearch_)) == std::string::npos) continue;
            if (shown++ % 2) ImGui::SameLine();
            const bool selected = std::find(state.selected.begin(), state.selected.end(), c.id) != state.selected.end();
            if (PobUi::Button((c.name + "##farm_" + c.id).c_str(), selected ? PobUi::BtnKind::Primary : PobUi::BtnKind::Secondary,
                              PobUi::BtnSize::Sm, nullptr, (width - PobUi::D(36)) * 0.5f)) {
                if (selected) state.selected.erase(std::remove(state.selected.begin(), state.selected.end(), c.id), state.selected.end());
                else {
                    if (UmaipoeFarm::Influence(c.id)) {
                        state.selected.erase(std::remove_if(state.selected.begin(), state.selected.end(), UmaipoeFarm::Influence), state.selected.end());
                        farmNotice_ = u8"작열의 총주교·세계 포식자·메이븐은 하나만 선택합니다.";
                    }
                    state.selected.push_back(c.id);
                }
                changed = true;
            }
            if (ImGui::IsItemHovered()) ImGui::SetTooltip("%s", c.note.c_str());
        }
        ImGui::EndChild();
        ImGui::SetNextItemWidth(-1);
        changed |= ImGui::SliderInt(u8"포인트 예산##farmbudget", &state.budget, 0, farmCatalog_.maximum);
        for (int budget : {30, 60, 90, 120, 150}) {
            if (budget != 30) ImGui::SameLine();
            if (ImGui::SmallButton((std::to_string(budget) + "##farmbudget").c_str())) { state.budget = budget; changed = true; }
        }
        for (size_t i = 0; i < state.selected.size(); ++i) {
            const auto* c = farmCatalog_.Find(state.selected[i]); if (!c) continue;
            ImGui::PushID(static_cast<int>(i));
            ImGui::Text("%d. %s", static_cast<int>(i + 1), c->name.c_str()); ImGui::SameLine();
            if (ImGui::SmallButton(u8"빼기")) { state.selected.erase(state.selected.begin() + i); changed = true; ImGui::PopID(); break; }
            if (i) { ImGui::SameLine(); if (ImGui::SmallButton(u8"우선")) { std::swap(state.selected[i], state.selected[i - 1]); changed = true; } }
            ImGui::PopID();
        }
        if (ImGui::SmallButton(u8"선택 모두 해제")) { state.selected.clear(); changed = true; }
        ImGui::SameLine();
        if (ImGui::SmallButton(u8"지도 성장 조합")) { state.selected = {"maps", "shrine", "box"}; changed = true; }
        if (ImGui::CollapsingHeader(u8"노드 제외·위험 옵션 허용")) {
            ImGui::TextWrapped(u8"핵심노드·세부 선택 노드는 자동 배치하지 않습니다. 효과를 확인한 뒤 트리에서 직접 선택하세요.");
            std::set<int> seen;
            ImGui::BeginChild("##farmoptions", ImVec2(0, PobUi::D(160)), true);
            for (const auto& id : state.selected) for (int node : farmCatalog_.Find(id)->targets) {
                if (!seen.insert(node).second) continue;
                const auto& n = farmCatalog_.nodes.at(node); ImGui::PushID(node);
                bool excluded = state.excluded.count(node) != 0;
                if (ImGui::Checkbox((u8"제외: " + farmCatalog_.names.at(node)).c_str(), &excluded)) {
                    if (excluded) state.excluded.insert(node); else state.excluded.erase(node); changed = true;
                }
                if (n.caution && !n.special) {
                    bool allowed = state.allowed.count(node) != 0;
                    if (ImGui::Checkbox(u8"위험도 확인 · 자동 배치 허용", &allowed)) {
                        if (allowed) state.allowed.insert(node); else state.allowed.erase(node); changed = true;
                    }
                }
                ImGui::PopID();
            }
            ImGui::EndChild();
        }
        if (changed) farmApply(state);
        if (!farmNotice_.empty()) ImGui::TextWrapped("%s", farmNotice_.c_str());
        ImGui::TextWrapped(u8"세부 옵션은 트리에서 직접 선택하세요. 성역·탐광·강탈 지역 내부에는 아틀라스가 적용되지 않습니다.");
        ImGui::TextWrapped(u8"원하는 파밍을 연결하는 출발용 구성입니다. 최대 수익이나 모든 핵심노드를 보장하지 않습니다.");
        if (ImGui::CollapsingHeader(u8"배치하지 못한 노드와 이유")) {
            const auto result = UmaipoeFarm::Calculate(farmCatalog_, state);
            for (const auto& p : result.pending)
                ImGui::BulletText("%s: %s", farmCatalog_.names.at(p.first).c_str(), p.second.c_str());
            if (result.pending.empty()) ImGui::TextUnformatted(u8"대상 노드를 모두 배치했습니다.");
        }
        ImGui::Separator();
    }
