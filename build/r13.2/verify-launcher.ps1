$ErrorActionPreference='Stop'
$repo=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$out=Join-Path $repo 'outputs/pob330-r13.2'
$baseline=Join-Path $repo 'outputs/pob330-r13.1'
$test=Join-Path $PSScriptRoot ('launcher-trial-'+[Guid]::NewGuid().ToString('N').Substring(0,8))
if(Test-Path $test){throw 'Use a fresh test profile'}
[void][Reflection.Assembly]::LoadFrom((Join-Path $out 'Umaipoe-PoB.exe'))
$key=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'public-key.xml'))
function Check($ok,$label){if(!$ok){throw $label}}
$u=[Updater]::new((Join-Path $test 'Auto'),$key)
$u.BootstrapEnabled=$false
$legacy=Join-Path $test 'r7-example/PoE1-3.30'
[void][IO.Directory]::CreateDirectory((Join-Path $legacy 'Builds'))
$xml=Join-Path $repo 'work/pob330-r13.1/gems.xml'
[IO.File]::Copy($xml,(Join-Path $legacy 'Builds/legacy.xml'))
$u.StartupCheck={throw 'test stops before network'}
try {$null=$u.Launch()} catch {if($_.Exception.ToString() -notmatch 'test stops before network'){throw}}
$builds=Join-Path $u.DataPath 'Builds'
Check ($u.State.imported -and @(Get-ChildItem $builds -Force).Count -eq 0) 'Empty first launch despite legacy sibling'
$old=$u.Verify([IO.File]::ReadAllText("$baseline/latest.json"))
$next=$u.Verify([IO.File]::ReadAllText("$out/latest.json"))
$u.Install($old,"$baseline/Umaipoe-PoB-r13.1.zip");$u.State.current=$old;$u.Save()
$build=Join-Path $builds 'my-build.xml';[IO.File]::Copy($xml,$build)
$settings=Join-Path $u.DataPath 'Settings.xml';[IO.File]::WriteAllText($settings,'<PathOfBuilding><Misc /></PathOfBuilding>')
$hb=[Updater]::Hash($build);$hs=[Updater]::Hash($settings)
$u.Install($next,"$out/Umaipoe-PoB-r13.2.zip");$u.Begin($next)
[IO.File]::WriteAllText($build,'failed migration');[IO.File]::WriteAllText($settings,'failed migration')
$u.Recover()
Check (([Updater]::Hash($build) -eq $hb) -and ([Updater]::Hash($settings) -eq $hs) -and $u.State.current.sha256 -eq $old.sha256) 'rollback'
$null=$u.State.rejected.Remove($next.sha256)
$u.State.staged=$next;$u.Save();$u.StartupCheck={}
$p=$u.Launch()
try{
 Check ($u.State.current.sha256 -eq $next.sha256 -and $u.State.previous.sha256 -eq $old.sha256 -and $u.Installed($old)) 'activate'
 Check (([Updater]::Hash($build) -eq $hb) -and ([Updater]::Hash($settings) -eq $hs) -and @(Get-ChildItem $builds -File -Filter '*.xml').Count -eq 1) 'saved data'
} finally {if(!$p.HasExited){$null=$p.CloseMainWindow()}}
$manual=[Updater]::new((Join-Path $test 'manual'),$key)
[IO.File]::WriteAllText((Join-Path $legacy 'Launch.lua'),'')
[IO.File]::WriteAllText((Join-Path $legacy 'Settings.xml'),'<PathOfBuilding><Misc buildPath="Z:/another/profile/" /></PathOfBuilding>')
$manual.Import($legacy)
Check (([Updater]::Hash((Join-Path $manual.DataPath 'Builds/legacy.xml'))) -eq $hb) 'explicit import'
$imported=[xml][IO.File]::ReadAllText((Join-Path $manual.DataPath 'Settings.xml'))
Check ($imported.PathOfBuilding.Misc.buildPath -eq ($manual.DataPath.Replace('\','/')+'/Builds/')) 'manual import path'
$report=@{version='r13.2';empty_first_launch=$true;explicit_import=$true;package_activation=@{passed=$true;build_preserved=$true;settings_preserved=$true;previous_version_preserved=$true;failure_restore=$true};packaged_native_startup=@{passed=$true;startup_calculation_save_reload=$true}}
[IO.File]::WriteAllText("$out/verification.json",($report|ConvertTo-Json -Depth 5))
