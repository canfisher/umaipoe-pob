using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Threading;

public static class SelfUpdate {
    static string Q(string s) { if(s.Contains("\"")) throw new InvalidDataException("Invalid path");return "\""+s+"\""; }
    public static Release Verify(string executable,string manifest,string root,string key) {
        var update=new Updater(root,key);var release=update.Verify(File.ReadAllText(manifest));
        if(release.kind!="launcher" || release.launcherVersion<2 || release.launcherVersion!=Updater.LauncherVersion
            || new FileInfo(executable).Length!=release.bytes || Updater.Hash(executable)!=release.sha256)
            throw new InvalidDataException("실행기 서명 또는 해시 검증 실패");
        return release;
    }
    public static void Queue(string root,string source,string key) {
        string manifest=Path.Combine(Path.GetDirectoryName(source),"launcher.json");
        if(!File.Exists(manifest)) return;
        var release=Verify(source,manifest,root,key);
        string stable=Path.Combine(root,"Umaipoe-PoB.exe");
        if(File.Exists(stable) && Updater.Hash(stable)==release.sha256) return;
        string installed=Path.Combine(root,"launcher-installed.json");
        if(File.Exists(installed)) {
            var previous=new Updater(root,key).Verify(File.ReadAllText(installed));
            if(previous.sequence>=release.sequence && previous.sha256!=release.sha256) return;
        }
        string folder=Path.Combine(root,"Bootstrap",release.sha256);Directory.CreateDirectory(folder);
        string helper=Path.Combine(folder,"Umaipoe-PoB.exe"),signed=Path.Combine(folder,"launcher.json");
        if(!File.Exists(helper)) File.Copy(source,helper);
        File.Copy(manifest,signed,true);Verify(helper,signed,root,key);
        Process.Start(new ProcessStartInfo(helper,"--replace-launcher") {UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden,WorkingDirectory=folder});
    }
    public static void Replace(string root,string source,string key,Func<string,bool> health) {
        string manifest=Path.Combine(Path.GetDirectoryName(source),"launcher.json");var release=Verify(source,manifest,root,key);
        string installed=Path.Combine(root,"launcher-installed.json");
        if(File.Exists(installed)) {
            var previous=new Updater(root,key).Verify(File.ReadAllText(installed));
            if(previous.sequence>=release.sequence && previous.sha256!=release.sha256) return;
        }
        string stable=Path.Combine(root,"Umaipoe-PoB.exe"),backup=stable+".previous",temp=stable+".next";
        if(File.Exists(stable) && Updater.Hash(stable)==release.sha256) return;
        File.Copy(source,temp,true);
        if(Updater.Hash(temp)!=release.sha256) throw new InvalidDataException("실행기 복사 검증 실패");
        bool existed=File.Exists(stable);
        if(existed) File.Replace(temp,stable,backup);else File.Move(temp,stable);
        try {
            if(!health(stable)) throw new IOException("새 실행기 시작 검사 실패");
            Updater.Atomic(Path.Combine(root,"launcher-installed.json"),File.ReadAllText(manifest));
        } catch {
            if(existed && File.Exists(backup)) File.Replace(backup,stable,stable+".failed");
            else if(File.Exists(stable)) File.Move(stable,stable+".failed-"+Guid.NewGuid().ToString("N"));
            throw;
        }
    }
    public static int WaitAndReplace(string root,string source,string key) {
        var timer=Stopwatch.StartNew();
        while(timer.Elapsed<TimeSpan.FromHours(24)) {
            FileStream guard=null;
            try {guard=new FileStream(Path.Combine(root,"session.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None);} catch(IOException) {Thread.Sleep(1000);continue;}
            using(guard) {
                try {
                    Replace(root,source,key,stable=>{
                        string marker=Path.Combine(root,Guid.NewGuid().ToString("N")+".launcher-ready"),token=Guid.NewGuid().ToString("N");
                        try {using(var p=Process.Start(new ProcessStartInfo(stable,"--launcher-health "+Q(marker)+" "+token){UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden})) {
                            if(!p.WaitForExit(15000)){p.Kill();p.WaitForExit();return false;}
                            return p.ExitCode==0 && File.Exists(marker) && File.ReadAllText(marker)==token;
                        }} finally {if(File.Exists(marker))File.Delete(marker);}
                    });return 0;
                } catch(Exception e) {File.AppendAllText(Path.Combine(root,"update.log"),DateTime.Now.ToString("s")+" Launcher rollback: "+e.Message+Environment.NewLine);return 1;}
            }
        }
        return 2;
    }
    public static string PublicKey() {
        using(var input=typeof(SelfUpdate).Assembly.GetManifestResourceStream("public-key.xml")) using(var reader=new StreamReader(input)) return reader.ReadToEnd();
    }
}
