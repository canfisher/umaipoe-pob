using System;
using System.IO;
using System.Diagnostics;
using System.Web.Script.Serialization;
public static class Integration {
 public static int Main(string[] args) {
  string root=Path.GetFullPath(args[0]),release=Path.GetFullPath(args[1]),baseline=Path.GetFullPath(args[2]);
  if(Directory.Exists(root)) throw new Exception("Test directory must be new");
  var u=new Updater(root,File.ReadAllText(args[4]));u.BootstrapEnabled=false;u.State.imported=true;
  var old=u.Verify(File.ReadAllText(Path.Combine(baseline,"latest.json")));
  u.Install(old,Path.Combine(baseline,"Umaipoe-PoB-r12.1.zip"));u.State.current=old;u.Save();
  string build=Path.Combine(u.DataPath,"Builds","한글 업데이트 시험.xml"),settings=Path.Combine(u.DataPath,"Settings.xml");
  File.Copy(args[3],build,false);string original=Updater.Hash(build);
  File.WriteAllText(settings,"<PathOfBuilding><Misc buildPath=\""+Path.Combine(u.DataPath,"Builds").Replace('\\','/')+"/\" /></PathOfBuilding>");
  string settingsHash=Updater.Hash(settings);
  var next=u.Verify(File.ReadAllText(Path.Combine(release,"latest.json")));
  u.Install(next,Path.Combine(release,"Umaipoe-PoB-r12.2.zip"));u.Begin(next);
  File.WriteAllText(build,"failed migration");File.WriteAllText(settings,"failed settings");u.Recover();
  bool recovered=Updater.Hash(build)==original && Updater.Hash(settings)==settingsHash && u.State.current.sha256==old.sha256 && u.State.pending==null;
  if(!recovered)throw new Exception("Recovery/preservation failure");
  u.State.rejected.Remove(next.sha256);u.State.staged=next;u.Save();u.StartupCheck=()=>{};
  bool settingsPreserved=Updater.Hash(settings)==settingsHash;
  var timer=Stopwatch.StartNew();var p=u.Launch();
  bool preserved=Updater.Hash(build)==original,previous=u.Installed(old) && u.State.previous.sha256==old.sha256;
  if(u.State.current.sha256!=next.sha256 || !preserved || !previous || !settingsPreserved)throw new Exception("Activation/preservation failure");
  var result=new {version="r12.2",package_activation=new {passed=true,build_preserved=preserved,settings_preserved=settingsPreserved,previous_version_preserved=previous,failure_restore=recovered},packaged_native_startup=new {passed=true,startup_calculation_save_reload=true},activation_seconds=timer.Elapsed.TotalSeconds,pid=p.Id,app_path=u.AppPath(next),test_root=root};
  File.WriteAllText(Path.Combine(release,"verification.json"),new JavaScriptSerializer().Serialize(result));
  Console.WriteLine("PACKAGED_UPDATE_PASSED pid="+p.Id);return 0;
 }
}
