using System;
using System.IO;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;

public static class Tests {
    static int passed;
    static void Check(bool ok, string name) { if (!ok) throw new Exception(name); Console.WriteLine("PASS " + name); passed++; }
    static void Reject(Action action, string name) { bool rejected = false; try { action(); } catch { rejected = true; } Check(rejected, name); }
    static string MakeZip(string root, string version, string entry, bool failure = false) {
        string zip = Path.Combine(root, version + ".zip");
        using (var archive = ZipFile.Open(zip, ZipArchiveMode.Create)) {
            archive.CreateEntryFromFile(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Fixture.exe"), "pob-zh.exe");
            using (var w = new StreamWriter(archive.CreateEntry("PoE1-3.30/Launch.lua").Open())) w.Write("test fixture");
            if (entry != null) using (var w = new StreamWriter(archive.CreateEntry(entry).Open())) w.Write("data");
            if (failure) using (var w = new StreamWriter(archive.CreateEntry("fail-start").Open())) w.Write("1");
        }
        return zip;
    }
    static Release ReleaseFor(string zip, string version, int sequence) {
        return new Release { schema = 1, sequence = sequence, minLauncher = 1, version = version, url = Updater.ReleasePrefix + version + "/app.zip", sha256 = Updater.Hash(zip), bytes = new FileInfo(zip).Length };
    }
    static string Sign(Release release, RSACryptoServiceProvider key) {
        var json = new JavaScriptSerializer(); byte[] payload = Encoding.UTF8.GetBytes(json.Serialize(release));
        return json.Serialize(new Envelope { payload = Convert.ToBase64String(payload), signature = Convert.ToBase64String(key.SignData(payload, CryptoConfig.MapNameToOID("SHA256"))) });
    }
    public static int Main(string[] args) {
        string root = Path.GetFullPath(args[0]); Directory.CreateDirectory(root);
        using (var rsa = new RSACryptoServiceProvider(2048)) {
            rsa.PersistKeyInCsp = false;
            var updater = new Updater(Path.Combine(root, "Auto"), rsa.ToXmlString(false));
            var old = ReleaseFor(MakeZip(root, "r8", null), "r8", 8);
            Check(updater.Verify(Sign(old, rsa)).sha256 == old.sha256, "signed manifest accepted");
            using (var other = new RSACryptoServiceProvider(2048)) { other.PersistKeyInCsp = false; Reject(() => updater.Verify(Sign(old, other)), "wrong signer rejected"); }
            string good = Path.Combine(root, "r8.zip");
            File.AppendAllText(good, "tamper"); Reject(() => updater.Install(old, good), "corrupted archive rejected");
            File.Delete(good); MakeZip(root, "r8", null); old = ReleaseFor(good, "r8", 8);
            foreach (string path in new[] { "../escaped", "/absolute", "folder\\escape", "AUX.txt", "trailing. ", "a:stream", "a/../b" })
                Reject(() => Updater.SafeEntry(root, path), "unsafe path rejected " + path);
            string bad = MakeZip(root, "r9-bad", "../escaped"); Reject(() => updater.Install(ReleaseFor(bad,"r9-bad",9),bad), "ZIP traversal rejected");
            string privateZip = MakeZip(root, "r9-private", "PoE1-3.30/Builds/private.xml"); Reject(() => updater.Install(ReleaseFor(privateZip,"r9-private",9),privateZip), "private build in release rejected");
            updater.Install(old, good); Check(updater.Installed(old), "verified install");
            string legacy = Path.Combine(root, "legacy", "PoE1-3.30"); Directory.CreateDirectory(Path.Combine(legacy, "Builds"));
            File.WriteAllText(Path.Combine(legacy,"Launch.lua"), "legacy");
            File.WriteAllText(Path.Combine(legacy,"Builds","한글.xml"), "original build");
            File.WriteAllText(Path.Combine(legacy,"Settings.xml"), "<PathOfBuilding><Misc buildPath=\"Builds/\" custom=\"keep\"/></PathOfBuilding>");
            string originalHash = Updater.Hash(Path.Combine(legacy,"Settings.xml"));
            updater.Import(legacy);
            string savedBuild = Path.Combine(updater.DataPath,"Builds","한글.xml");
            Check(File.ReadAllText(savedBuild)=="original build", "Korean build imported");
            Check(Updater.Hash(Path.Combine(legacy,"Settings.xml"))==originalHash, "legacy settings unchanged");
            string settings = Path.Combine(updater.DataPath,"Settings.xml");
            Check(File.ReadAllText(settings).Contains("custom=\"keep\"") && File.ReadAllText(settings).Contains("UserData/Builds/"), "settings migrated and relative path redirected");
            File.WriteAllText(Path.Combine(legacy,"Builds","한글.xml"), "different build"); updater.Import(legacy);
            Check(File.ReadAllText(savedBuild)=="original build" && Directory.GetFiles(Path.Combine(updater.DataPath,"Builds")).Length==2, "conflicting builds preserved");
            updater.Begin(old); using (var p=updater.Start(old,true)) { p.Kill(); p.WaitForExit(); }
            Check(updater.State.current.sha256==old.sha256 && updater.State.pending==null, "healthy start commits release");
            string secondZip=MakeZip(root,"r9",null); var second=ReleaseFor(secondZip,"r9",9); updater.Install(second,secondZip);
            string before=File.ReadAllText(settings); updater.Begin(second); File.WriteAllText(settings,"failed settings");
            File.WriteAllText(savedBuild,"truncated by failed candidate");
            updater=new Updater(updater.Root,rsa.ToXmlString(false)); updater.Recover();
            Check(File.ReadAllText(settings)==before && File.ReadAllText(savedBuild)=="original build", "interrupted update restores settings and keeps builds");
            Check(updater.State.current.sha256==old.sha256 && updater.State.rejected.Contains(second.sha256), "failed candidate quarantined");
            updater.State.rejected.Clear(); updater.Begin(second); using(var p=updater.Start(second,true)){p.Kill();p.WaitForExit();}
            Check(updater.State.current.sha256==second.sha256 && updater.State.previous.sha256==old.sha256,"success retains rollback version");
            updater.Rollback(); Check(updater.State.current.sha256==old.sha256,"manual rollback preserves pointer");
            string failZip=MakeZip(root,"r10",null,true); var fail=ReleaseFor(failZip,"r10",10); updater.Install(fail,failZip); updater.Begin(fail);
            Reject(()=>updater.Start(fail,true),"real failing process rejected"); updater.Recover();
            Check(updater.State.current.sha256==old.sha256 && File.ReadAllText(savedBuild)=="original build","failed startup retained old version and build");
            Check(!File.Exists(Path.Combine(root,"escaped")),"no escaped files written");
            string missingHealthZip=MakeZip(root,"r11-missinghealth",null);var missingHealth=ReleaseFor(missingHealthZip,"r11-missinghealth",11);missingHealth.healthRequired=true;
            updater.Install(missingHealth,missingHealthZip);updater.Begin(missingHealth);
            Reject(()=>updater.Start(missingHealth,true),"build-list readiness alone cannot commit a health-required release");updater.Recover();
            Check(File.ReadAllText(savedBuild)=="original build","health failure preserves original build");
            string selfDir=Path.Combine(root,"self");Directory.CreateDirectory(selfDir);
            string self=Path.Combine(selfDir,"Umaipoe-PoB.exe"),manifest=Path.Combine(selfDir,"launcher.json");
            File.Copy(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"Fixture.exe"),self);
            var launcher=ReleaseFor(self,"r12-launcher",100004);launcher.kind="launcher";launcher.launcherVersion=Updater.LauncherVersion;
            File.WriteAllText(manifest,Sign(launcher,rsa));
            string stable=Path.Combine(updater.Root,"Umaipoe-PoB.exe");File.WriteAllText(stable,"old launcher");
            SelfUpdate.Replace(updater.Root,self,rsa.ToXmlString(false),p=>Updater.Hash(p)==launcher.sha256);
            Check(Updater.Hash(stable)==launcher.sha256 && File.ReadAllText(stable+".previous")=="old launcher","verified launcher replacement preserves old executable");
            File.WriteAllText(stable,"old launcher again");
            Reject(()=>SelfUpdate.Replace(updater.Root,self,rsa.ToXmlString(false),p=>false),"launcher health failure rejected");
            Check(File.ReadAllText(stable)=="old launcher again","launcher health failure rolls back original executable");
            File.AppendAllText(self,"tampered");
            Reject(()=>SelfUpdate.Replace(updater.Root,self,rsa.ToXmlString(false),p=>true),"tampered launcher never replaces original");
            Check(File.ReadAllText(stable)=="old launcher again","original launcher survived signature/hash rejection");
            updater.BootstrapEnabled=false;
            updater.State.imported=true; updater.State.staged=null; updater.State.pending=null;
            bool checkedBeforeStart=false;
            updater.StartupCheck=()=>{checkedBeforeStart=true;throw new IOException("offline");};
            using(var p=updater.Launch()){Check(checkedBeforeStart && !p.HasExited,"offline check falls back to installed build");p.Kill();p.WaitForExit();}
            updater.State.rejected.Clear();
            updater.StartupCheck=()=>{updater.State.staged=second;updater.Save();};
            using(var p=updater.Launch()){Check(updater.State.current.sha256==second.sha256,"startup update activates before returning launched process");p.Kill();p.WaitForExit();}
            string toolSource=Path.Combine(root,"source-tools"),toolTarget=Path.Combine(root,"target-tools");
            Directory.CreateDirectory(Path.Combine(toolSource,"PobTools"));
            File.WriteAllText(Path.Combine(toolSource,"PobTools","atlas.json"),"{\"name\":\"한글 파밍\"}");
            Updater.CopyToolSettings(toolSource,toolTarget);
            Check(File.ReadAllText(Path.Combine(toolTarget,"PobTools","atlas.json")).Contains("한글 파밍"),"tool projects survive version migration");
            File.WriteAllText(Path.Combine(toolTarget,"PobTools","atlas.json"),"changed");Updater.CopyToolSettings(toolSource,toolTarget);
            Check(File.ReadAllText(Path.Combine(toolTarget,"PobTools","atlas.json"))=="changed","existing tool projects are not overwritten");
            Reject(()=>Updater.ValidateToolData(toolTarget),"missing timeless/data package rejected");
            Check(File.ReadAllText(savedBuild)=="original build","startup checks preserve user build");
            File.WriteAllText(Path.Combine(root,"result.json"),"{\"passed\":"+passed+",\"failures\":0}");
        }
        return 0;
    }
}
