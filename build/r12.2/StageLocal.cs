using System;
using System.IO;
using System.Linq;
using System.Web.Script.Serialization;
public static class StageLocal {
 public static int Main(string[] args) {
  var u=new Updater(args[0],File.ReadAllText(args[2]));
  if(u.State.pending!=null)throw new Exception("An update is pending");
  var before=Directory.GetFiles(u.DataPath,"*",SearchOption.AllDirectories).ToDictionary(p=>p,p=>Updater.Hash(p));
  string folder=Path.GetFullPath(args[1]);Directory.CreateDirectory(Path.Combine(folder,"backups"));
  File.Copy(Path.Combine(u.Root,"state.json"),Path.Combine(folder,"backups","local-state-before.json"),false);
  var release=u.Verify(File.ReadAllText(Path.Combine(folder,"latest.json")));
  u.Install(release,Path.Combine(folder,"Umaipoe-PoB-r12.2.zip"));u.State.staged=release;u.Save();
  bool kept=before.All(p=>Updater.Hash(p.Key)==p.Value);if(!kept)throw new Exception("User data changed");
  var report=new{version=release.version,staged=true,appliesOnNextLaunch=true,userFilesPreserved=before.Count,previous=u.State.current.version};
  File.WriteAllText(Path.Combine(folder,"local-stage-verification.json"),new JavaScriptSerializer().Serialize(report));
  Console.WriteLine("LOCAL_STAGED user files preserved="+before.Count);return 0;
 }
}
