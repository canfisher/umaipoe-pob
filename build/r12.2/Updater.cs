using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using System.Xml;

[assembly: System.Reflection.AssemblyVersion("3.30.12.2")]
[assembly: System.Reflection.AssemblyTitle("우마이 한글 PoB 자동 업데이트")]

public sealed class Release {
    public int schema, sequence, minLauncher, launcherVersion;
    public string kind;
    public bool healthRequired, koreanToolsRequired;
    public string version, url, sha256;
    public long bytes;
}
public sealed class Envelope { public string payload, signature; }
public sealed class UpdateState {
    public Release current, previous, staged, pending;
    public List<string> rejected = new List<string>();
    public bool imported;
    public string backupPath;
}

public sealed class Updater {
    public const string Feed = "https://github.com/canfisher/umaipoe-pob/releases/latest/download/latest.json";
    public const string ReleasePrefix = "https://github.com/canfisher/umaipoe-pob/releases/download/";
    public const int LauncherVersion = 4;
    public readonly string Root, DataPath;
    public UpdateState State;
    readonly string publicKey;
    static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 1024 * 1024 };
    public Action<string> Report = delegate {};
    public Action ProcessStarted = delegate {};
    public bool BootstrapEnabled = true;

    public Updater(string root, string key) {
        Root = Path.GetFullPath(root); DataPath = Path.Combine(Root, "UserData"); publicKey = key;
        Directory.CreateDirectory(Root); Directory.CreateDirectory(DataPath);
        Directory.CreateDirectory(Path.Combine(DataPath, "Builds"));
        string stateFile = Path.Combine(Root, "state.json");
        if (File.Exists(stateFile)) State = Json.Deserialize<UpdateState>(File.ReadAllText(stateFile));
        else State = new UpdateState();
        if (State == null || State.rejected == null) throw new InvalidDataException("업데이트 상태 파일을 읽을 수 없습니다. 사용자 자료는 그대로 보존됩니다.");
    }
    public static void Atomic(string path, string text) {
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        string temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        using (var f = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None)) {
            byte[] b = new UTF8Encoding(false).GetBytes(text); f.Write(b, 0, b.Length); f.Flush(true);
        }
        if (File.Exists(path)) File.Replace(temp, path, path + ".bak"); else File.Move(temp, path);
    }
    public void Save() { Atomic(Path.Combine(Root, "state.json"), Json.Serialize(State)); }
    public void Log(string text) {
        try { File.AppendAllText(Path.Combine(Root, "update.log"), DateTime.Now.ToString("s") + " " + text + Environment.NewLine); } catch { }
    }
    public static string Hash(string path) {
        using (var s = File.OpenRead(path)) using (var h = SHA256.Create())
            return BitConverter.ToString(h.ComputeHash(s)).Replace("-", "").ToLowerInvariant();
    }
    public Release Verify(string envelope) {
        var signed = Json.Deserialize<Envelope>(envelope);
        byte[] payload = Convert.FromBase64String(signed.payload), signature = Convert.FromBase64String(signed.signature);
        using (var rsa = new RSACryptoServiceProvider()) {
            rsa.PersistKeyInCsp = false; rsa.FromXmlString(publicKey);
            if (!rsa.VerifyData(payload, CryptoConfig.MapNameToOID("SHA256"), signature)) throw new InvalidDataException("배포 서명이 일치하지 않습니다.");
        }
        Release r = Json.Deserialize<Release>(Encoding.UTF8.GetString(payload)); Validate(r);
        return r;
    }
    static void Validate(Release r) {
        if (r == null || r.schema != 1 || r.minLauncher > LauncherVersion || r.sequence < 1
            || !Regex.IsMatch(r.version ?? "", @"^r[0-9]+(?:[.-][A-Za-z0-9]+)*$")
            || !Regex.IsMatch(r.sha256 ?? "", "^[a-f0-9]{64}$") || r.bytes < 1 || r.bytes > 512L * 1024 * 1024
            || !(r.url ?? "").StartsWith(ReleasePrefix, StringComparison.Ordinal))
            throw new InvalidDataException("지원하지 않는 배포 정보입니다. 기존 버전을 유지합니다.");
        Uri uri = new Uri(r.url);
        if (uri.Scheme != "https" || uri.Host != "github.com" || uri.UserInfo != "" || !uri.IsDefaultPort)
            throw new InvalidDataException("잘못된 배포 주소입니다.");
    }
    public string AppPath(Release r) { Validate(r); return Path.Combine(Root, "Versions", r.version + "-" + r.sha256.Substring(0, 12)); }
    public bool Installed(Release r) {
        if (r == null) return false;
        string app = AppPath(r), marker = Path.Combine(app, ".verified");
        return File.Exists(marker) && File.ReadAllText(marker) == r.sha256
            && File.Exists(Path.Combine(app, "pob-zh.exe")) && File.Exists(Path.Combine(app, "PoE1-3.30", "Launch.lua"));
    }
    public static string SafeEntry(string root, string entry) {
        if (String.IsNullOrEmpty(entry) || entry.Contains("\\") || entry.StartsWith("/") || entry.Contains(":"))
            throw new InvalidDataException("잘못된 압축 경로입니다.");
        string[] parts = entry.TrimEnd('/').Split('/');
        foreach (string part in parts)
            if (part == "" || part == "." || part == ".." || part.EndsWith(".") || part.EndsWith(" ")
                || part.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0
                || Regex.IsMatch(part, @"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", RegexOptions.IgnoreCase))
                throw new InvalidDataException("안전하지 않은 압축 경로입니다.");
        string prefix = Path.GetFullPath(root).TrimEnd('\\') + "\\", target = Path.GetFullPath(Path.Combine(root, String.Join("\\", parts)));
        if (!target.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("압축 경로가 범위를 벗어납니다.");
        return target;
    }
    public void Install(Release release, string zip) {
        Validate(release);
        if (new FileInfo(zip).Length != release.bytes || Hash(zip) != release.sha256) throw new InvalidDataException("다운로드 파일 검증에 실패했습니다.");
        if (Installed(release)) return;
        string destination = AppPath(release), staging = Path.Combine(Root, "Staging", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(staging);
        try {
            using (var archive = ZipFile.OpenRead(zip)) {
                if (archive.Entries.Count > 20000 || archive.Entries.Sum(e => e.Length) > 2L * 1024 * 1024 * 1024)
                    throw new InvalidDataException("배포 파일 크기가 허용 범위를 벗어납니다.");
                if (new DriveInfo(Path.GetPathRoot(Root)).AvailableFreeSpace < archive.Entries.Sum(e => e.Length) + 64L * 1024 * 1024)
                    throw new IOException("설치할 디스크의 여유 공간이 부족합니다.");
                var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (var e in archive.Entries) {
                    string target = SafeEntry(staging, e.FullName);
                    if (!seen.Add(target) || ((e.ExternalAttributes >> 16) & 0xF000) == 0xA000)
                        throw new InvalidDataException("중복 경로나 심볼릭 링크가 포함되어 있습니다.");
                    string lower = e.FullName.ToLowerInvariant();
                    if (lower.Contains("/builds/") || lower.EndsWith("/settings.xml") || lower.StartsWith("userdata/"))
                        throw new InvalidDataException("배포본에 사용자 자료가 포함되어 있습니다.");
                    if (e.FullName.EndsWith("/")) { Directory.CreateDirectory(target); continue; }
                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    using (var input = e.Open()) using (var output = new FileStream(target, FileMode.CreateNew)) input.CopyTo(output);
                }
            }
            if (!File.Exists(Path.Combine(staging, "pob-zh.exe")) || !File.Exists(Path.Combine(staging, "PoE1-3.30", "Launch.lua")))
                throw new InvalidDataException("실행에 필요한 파일이 없습니다.");
            if (release.koreanToolsRequired) ValidateToolData(staging);
            File.WriteAllText(Path.Combine(staging, ".verified"), release.sha256);
            Directory.CreateDirectory(Path.GetDirectoryName(destination));
            if (Directory.Exists(destination)) throw new IOException("같은 버전의 불완전한 설치가 있습니다. 사용자 자료를 유지한 채 설치 폴더를 확인하세요.");
            Directory.Move(staging, destination);
            Log("Verified installation " + release.version);
        } finally {
            // Only the freshly created, scoped staging directory is disposable.
            if (Directory.Exists(staging)) Directory.Delete(staging, true);
        }
    }
    static bool AllowedDownload(Uri uri) {
        return uri.Scheme == "https" && uri.UserInfo == "" && uri.IsDefaultPort &&
            (uri.Host == "github.com" || uri.Host == "release-assets.githubusercontent.com" || uri.Host == "objects.githubusercontent.com");
    }
    public static void ValidateToolData(string app) {
        foreach (string file in new[] { "Data/timeless_jewels.json", "Data/passive_tree_poe1.json", "Data/poe1/ko-KR/stats.json", "Data/launcher/ko-KR/launcher.json", "Data/atlas_versions/3.30.0/atlas_tree_poe1.json" }) {
            string path=Path.Combine(app,file);
            if (!File.Exists(path) || new FileInfo(path).Length<10) throw new InvalidDataException("필수 한국어 도구 자료가 없습니다: "+file);
        }
        string tree=File.ReadAllText(Path.Combine(app,"Data/passive_tree_poe1.json"));
        if (!Regex.IsMatch(tree,"\"treeVersion\"\\s*:\\s*\"3_30\"")) throw new InvalidDataException("무궁한 주얼의 3.30 트리 자료가 아닙니다.");
        foreach(string stem in new[]{"BrutalRestraint","ElegantHubris","HeroicTragedy","LethalPride","MilitantFaith"}) {
            string path=Path.Combine(app,"PoE1-3.30/Data/TimelessJewelData",stem+".zip");
            if(!File.Exists(path) || new FileInfo(path).Length<100) throw new InvalidDataException("무궁한 주얼 검색 자료가 없습니다: "+stem);
        }
        for(int part=0;part<5;part++) {
            string path=Path.Combine(app,"PoE1-3.30/Data/TimelessJewelData","GloriousVanity.zip.part"+part);
            if(!File.Exists(path) || new FileInfo(path).Length<100) throw new InvalidDataException("찬란한 허영심 검색 자료가 없습니다.");
        }
    }
    public static void Download(string url, string path, long maxBytes, int timeoutMs, CancellationToken cancellation = default(CancellationToken), Action<long> progress = null) {
        DownloadCore(new Uri(url), path, maxBytes, timeoutMs, cancellation, progress, AllowedDownload);
    }
    internal static void DownloadCore(Uri uri, string path, long maxBytes, int timeoutMs, CancellationToken cancellation, Action<long> progress, Func<Uri,bool> allowed) {
        ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
        var timer = Stopwatch.StartNew();
        for (int redirects = 0; redirects < 6; redirects++) {
            cancellation.ThrowIfCancellationRequested();
            int remaining = timeoutMs - (int)timer.ElapsedMilliseconds;
            if (remaining <= 0) throw new TimeoutException("업데이트 통신 대기 시간을 초과했습니다.");
            if (!allowed(uri)) throw new InvalidDataException("허용되지 않은 다운로드 주소입니다.");
            var req = (HttpWebRequest)WebRequest.Create(uri);
            req.AllowAutoRedirect = false; req.Timeout = Math.Min(remaining, 30000); req.ReadWriteTimeout = Math.Min(remaining, 30000);
            req.UserAgent = "UmaipoePoB-Updater/4";
            using (var abort = cancellation.Register(req.Abort))
            using (var deadline = new System.Threading.Timer(_ => req.Abort(), null, remaining, Timeout.Infinite))
            try {
            using (var resp = (HttpWebResponse)req.GetResponse()) {
                int code = (int)resp.StatusCode;
                if (code >= 300 && code < 400) { uri = new Uri(uri, resp.Headers["Location"]); continue; }
                if (resp.ContentLength > maxBytes) throw new InvalidDataException("다운로드 용량 제한을 초과했습니다.");
                using (var input = resp.GetResponseStream()) using (var output = new FileStream(path, FileMode.CreateNew)) {
                    byte[] buffer = new byte[65536]; long total = 0; int n;
                    while ((n = input.Read(buffer, 0, buffer.Length)) > 0) {
                        cancellation.ThrowIfCancellationRequested();
                        total += n;
                        if (total > maxBytes || timer.ElapsedMilliseconds > timeoutMs) throw new IOException("다운로드 크기 또는 시간 제한을 초과했습니다.");
                        output.Write(buffer, 0, n);
                        if (progress != null) progress(total);
                    }
                    cancellation.ThrowIfCancellationRequested();
                    output.Flush(true);
                }
                return;
            }
            } catch (Exception) {
                cancellation.ThrowIfCancellationRequested();
                if (timer.ElapsedMilliseconds >= timeoutMs) throw new TimeoutException("업데이트 통신 대기 시간을 초과했습니다.");
                throw;
            }
        }
        throw new IOException("다운로드 리디렉션이 너무 많습니다.");
    }
    public void Check() { Check(CancellationToken.None); }
    public void Check(CancellationToken cancellation) {
        string download = Path.Combine(Root, "Downloads"); Directory.CreateDirectory(download);
        string manifest = Path.Combine(download, Guid.NewGuid().ToString("N") + ".json"), zip = null;
        try {
            Report("새 버전을 확인합니다. 통신 대기: 최대 10초"); Download(Feed+"?check="+DateTime.UtcNow.Ticks, manifest, 1024 * 1024, 10000, cancellation);
            Release r = Verify(File.ReadAllText(manifest));
            if (State.rejected.Contains(r.sha256) || (State.current != null && r.sequence <= State.current.sequence)
                || (State.staged != null && r.sequence <= State.staged.sequence)) return;
            zip = Path.Combine(download, Guid.NewGuid().ToString("N") + ".zip");
            Report("새 버전 " + r.version + "을 내려받습니다. " + (r.bytes / 1000000.0).ToString("F1") + " MB");
            long lastReport = -1; var progressTimer = Stopwatch.StartNew();
            Download(r.url, zip, r.bytes, 600000, cancellation, bytes => {
                if (lastReport < 0 || progressTimer.ElapsedMilliseconds - lastReport >= 250) {
                    lastReport = progressTimer.ElapsedMilliseconds;
                    Report(String.Format("{0} 다운로드: {1:F1} / {2:F1} MB ({3:F0}%)", r.version, bytes / 1000000.0, r.bytes / 1000000.0, 100.0 * bytes / r.bytes));
                }
            });
            cancellation.ThrowIfCancellationRequested();
            Report("다운로드 검증 및 설치 중입니다. 기존 빌드와 설정은 보존됩니다."); Install(r, zip);
            State.staged = r; Save(); Report("새 버전 준비 완료. PoB를 시작할 때 적용합니다.");
        } finally {
            if (File.Exists(manifest)) File.Delete(manifest);
            if (zip != null && File.Exists(zip)) File.Delete(zip);
        }
    }
    static IEnumerable<string> SafeFiles(string root) {
        if ((File.GetAttributes(root) & FileAttributes.ReparsePoint) != 0) yield break;
        foreach (string path in Directory.GetFiles(root))
            if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) == 0) yield return path;
        foreach (string dir in Directory.GetDirectories(root)) foreach (string path in SafeFiles(dir)) yield return path;
    }
    public void Import(string folder) {
        folder = Path.GetFullPath(folder);
        if (!File.Exists(Path.Combine(folder, "Launch.lua"))) folder = Path.Combine(folder, "PoE1-3.30");
        if (!Directory.Exists(folder)) throw new DirectoryNotFoundException("기존 PoB 폴더를 찾지 못했습니다.");
        string builds = Path.Combine(folder, "Builds"); int copied = 0;
        if (Directory.Exists(builds)) foreach (string file in SafeFiles(builds)) {
            string relative = file.Substring(builds.Length + 1), target = Path.Combine(DataPath, "Builds", relative);
            if (File.Exists(target) && Hash(target) == Hash(file)) continue;
            if (File.Exists(target)) target = Path.Combine(Path.GetDirectoryName(target), Path.GetFileNameWithoutExtension(target) + "-import-" + Hash(file).Substring(0, 12) + Path.GetExtension(target));
            Directory.CreateDirectory(Path.GetDirectoryName(target));
            if (!File.Exists(target)) { File.Copy(file, target, false); copied++; }
        }
        string sourceSettings = Path.Combine(folder, "Settings.xml"), settings = Path.Combine(DataPath, "Settings.xml");
        if (File.Exists(sourceSettings) && !File.Exists(settings)) {
            var doc = new XmlDocument { XmlResolver = null };
            using (var reader = XmlReader.Create(sourceSettings, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null })) doc.Load(reader);
            XmlNode misc = doc.SelectSingleNode("//Misc[@buildPath]");
            if (misc != null) {
                string value = misc.Attributes["buildPath"].Value;
                if (!Path.IsPathRooted(value) || Path.GetFullPath(value).TrimEnd('\\','/').StartsWith(folder.TrimEnd('\\','/') + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                    misc.Attributes["buildPath"].Value = Path.Combine(DataPath, "Builds").Replace('\\', '/') + "/";
            }
            Atomic(settings, doc.OuterXml);
            File.Copy(sourceSettings, Path.Combine(DataPath, "Settings-import-original.xml"), false);
        }
        string ini = Path.Combine(Directory.GetParent(folder).FullName, "pob-zh.ini");
        string savedIni = Path.Combine(DataPath, "pob-zh.ini");
        if (File.Exists(ini) && !File.Exists(savedIni)) File.Copy(ini, savedIni, false);
        Log("Imported " + copied + " build files from " + folder);
    }
    public void ImportLegacy() {
        if (State.imported) return;
        string parent = Directory.GetParent(Root).FullName;
        foreach (string dir in Directory.GetDirectories(parent).Where(p => Path.GetFileName(p).StartsWith("r", StringComparison.OrdinalIgnoreCase)).OrderByDescending(Directory.GetLastWriteTimeUtc)) {
            if (Directory.Exists(Path.Combine(dir, "PoE1-3.30"))) Import(dir);
        }
        State.imported = true; Save();
    }
    public void Recover() {
        if (State.pending == null) return;
        if(!String.IsNullOrEmpty(State.backupPath)) {
            string expected=Path.Combine(Root,"Backups")+Path.DirectorySeparatorChar;
            string backupRoot=Path.GetFullPath(State.backupPath);
            if(!backupRoot.StartsWith(expected,StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("잘못된 복구 경로");
            string builds=Path.Combine(backupRoot,"Builds");
            if(Directory.Exists(builds)) foreach(string saved in Directory.GetFiles(builds,"*.xml",SearchOption.AllDirectories)) {
                string rel=saved.Substring(builds.Length+1),target=Path.Combine(DataPath,"Builds",rel);
                if(File.Exists(target) && Hash(target)==Hash(saved)) continue;
                if(File.Exists(target)) {string failed=Path.Combine(backupRoot,"AfterFailure",rel);Directory.CreateDirectory(Path.GetDirectoryName(failed));File.Copy(target,failed,true);}
                Atomic(target,File.ReadAllText(saved));
            }
        }
        string settings = Path.Combine(DataPath, "Settings.xml"), backup = Path.Combine(Root, "pending-settings.xml");
        if (File.Exists(settings)) File.Copy(settings, Path.Combine(DataPath, "Settings-failed-" + DateTime.Now.ToString("yyyyMMdd-HHmmssfff") + ".xml"), false);
        if (File.Exists(backup)) Atomic(settings, File.ReadAllText(backup));
        State.rejected.Add(State.pending.sha256); Log("Rollback " + State.pending.version);
        State.pending = null; State.staged = null; Save();
        if (File.Exists(backup)) File.Delete(backup);
    }
    public void Begin(Release release) {
        string snapshot=Path.Combine(Root,"Backups",DateTime.UtcNow.ToString("yyyyMMdd-HHmmssfff")+"-"+Guid.NewGuid().ToString("N"));
        CopyBuilds(Path.Combine(DataPath,"Builds"),Path.Combine(snapshot,"Builds"));
        State.backupPath=snapshot;
        string settings = Path.Combine(DataPath, "Settings.xml"), backup = Path.Combine(Root, "pending-settings.xml");
        if (File.Exists(backup)) File.Delete(backup);
        if (File.Exists(settings)) File.Copy(settings, backup, false);
        State.pending = release; Save();
    }
    static void CopyBuilds(string source,string destination) {
        Directory.CreateDirectory(destination);
        foreach(var item in new DirectoryInfo(source).EnumerateFileSystemInfos()) {
            if((item.Attributes & FileAttributes.ReparsePoint)!=0) continue;
            string target=Path.Combine(destination,item.Name);
            if((item.Attributes & FileAttributes.Directory)!=0) CopyBuilds(item.FullName,target);
            else if(item.Extension.Equals(".xml",StringComparison.OrdinalIgnoreCase)) File.Copy(item.FullName,target,false);
        }
    }
    public void Commit(Release release) {
        if (State.pending == null || State.pending.sha256 != release.sha256) throw new InvalidOperationException("시작 확인 대상이 다릅니다.");
        State.previous = State.current; State.current = release; State.pending = null; State.staged = null; Save();
        string backup = Path.Combine(Root, "pending-settings.xml"); if (File.Exists(backup)) File.Delete(backup);
        Log("Activated " + release.version);
    }
    public void Rollback() {
        if (!Installed(State.previous)) throw new InvalidOperationException("돌아갈 이전 버전이 없습니다.");
        State.rejected.Add(State.current.sha256);
        Release old = State.current; State.current = State.previous; State.previous = old; State.staged = null; Save();
    }
    public Process Start(Release release, bool trial) {
        if (!Installed(release)) throw new IOException("검증된 설치를 찾지 못했습니다.");
        string app = AppPath(release), ready = Path.Combine(Root, "ready-" + Guid.NewGuid().ToString("N")), token = Guid.NewGuid().ToString("N");
        if(release.koreanToolsRequired) ValidateToolData(app);
        if (trial && Installed(State.current) && State.current.sha256 != release.sha256) CopyToolSettings(AppPath(State.current),app);
        string ini = Path.Combine(DataPath, "pob-zh.ini");
        if (File.Exists(ini)) File.Copy(ini, Path.Combine(app, "pob-zh.ini"), true);
        var start = new ProcessStartInfo(Path.Combine(app, "pob-zh.exe"), "--engine PoE1-3.30") { WorkingDirectory = app, UseShellExecute = false };
        start.EnvironmentVariables["UMAIPOE_USER_DATA"] = DataPath.Replace('\\', '/');
        if (trial) {
            start.EnvironmentVariables["UMAIPOE_READY_FILE"] = ready.Replace('\\', '/');
            start.EnvironmentVariables["UMAIPOE_READY_TOKEN"] = token;
        }
        if (BootstrapEnabled) start.EnvironmentVariables["UMAIPOE_LAUNCHER"] = Application.ExecutablePath;
        else start.EnvironmentVariables.Remove("UMAIPOE_LAUNCHER");
        Report(release.version + (trial ? " 실행 및 계산·저장 검사 중입니다." : " 실행 중입니다."));
        Process process = Process.Start(start); Log("Started " + release.version + " pid=" + process.Id);
        ProcessStarted();
        if (!trial) return process;
        var timer = Stopwatch.StartNew();
        try {
            while (timer.Elapsed < TimeSpan.FromSeconds(150)) {
                if (process.HasExited) throw new IOException("새 버전이 정상 시작 전에 종료됐습니다.");
                if(File.Exists(ready+".failed")) throw new IOException(File.ReadAllText(ready+".failed"));
                if (File.Exists(ready) && File.ReadAllText(ready) == token) {
                    Thread.Sleep(1500);
                    if (process.HasExited) throw new IOException("새 버전 시작 직후 종료됐습니다.");
                    if(release.healthRequired) {
                        string result=ready+".health.json";
                        if(!File.Exists(result)) throw new IOException("빌드 계산/저장 검사 결과가 없습니다.");
                        var health=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(result));
                        if(!health.ContainsKey("passed") || !(bool)health["passed"] || !health.ContainsKey("token") || (string)health["token"]!=token) throw new IOException("빌드 계산/저장 검사 실패");
                    }
                    Commit(release); return process;
                }
                Thread.Sleep(200);
            }
            throw new TimeoutException("새 버전의 정상 시작을 확인하지 못했습니다.");
        } catch {
            if (!process.HasExited) { process.Kill(); process.WaitForExit(5000); }
            throw;
        } finally { if (File.Exists(ready)) File.Delete(ready); }
    }
    public Action StartupCheck;
    public static void CopyToolSettings(string source,string destination) {
        string saved=Path.Combine(source,"PobTools"), target=Path.Combine(destination,"PobTools");
        if(!Directory.Exists(saved)) return;
        foreach(string file in SafeFiles(saved)) {
            if(!String.Equals(Path.GetExtension(file),".json",StringComparison.OrdinalIgnoreCase)) continue;
            string next=Path.Combine(target,file.Substring(saved.Length+1));
            if(File.Exists(next)) continue;
            Directory.CreateDirectory(Path.GetDirectoryName(next)); File.Copy(file,next,false);
        }
    }
    public Process Launch() { return Launch(CancellationToken.None); }
    public Process Launch(CancellationToken cancellation) {
        Recover(); ImportLegacy();
        try { if (StartupCheck != null) StartupCheck(); else Check(cancellation); }
        catch (Exception e) {
            if (!Installed(State.current) && !Installed(State.staged)) throw;
            Log("Startup update unavailable: " + e.Message);
            Report("업데이트를 확인하지 못해 설치된 정상 버전으로 시작합니다.");
        }
        if (State.staged != null) {
            Release candidate = State.staged; Begin(candidate);
            try { return Start(candidate, true); }
            catch (Exception e) { Log(e.ToString()); Recover(); if (!Installed(State.current)) throw; Report("새 버전 실행에 실패해 이전 버전으로 돌아갑니다."); }
        }
        return Start(State.current, false);
    }
    public void SaveLauncherSettings(Release release) {
        string ini = Path.Combine(AppPath(release), "pob-zh.ini");
        if (File.Exists(ini)) Atomic(Path.Combine(DataPath, "pob-zh.ini"), File.ReadAllText(ini));
    }
}

#if !TESTING
public sealed class LauncherWindow : Form {
    readonly Updater updater;
    readonly Label status = new Label { Dock = DockStyle.Top, Height = 65 };
    readonly FlowLayoutPanel buttons = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 90 };
    readonly Button skip = new Button { Text = "이번 확인 건너뛰기", Height = 32, Dock = DockStyle.Top, Visible = false };
    CancellationTokenSource cancellation;
    bool busy;
    public LauncherWindow(Updater u, bool manage) {
        updater = u; Text = "우마이 한글 PoB · 자동 업데이트"; ClientSize = new Size(520, 245);
        Font = new Font("맑은 고딕", 10); Padding = new Padding(18); StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.FixedDialog; MaximizeBox = false;
        Controls.Add(buttons); Controls.Add(skip); Controls.Add(status);
        skip.Click += (s,e) => { skip.Enabled = false; if (cancellation != null) cancellation.Cancel(); };
        Add("PoB 실행", Run);
        Add("업데이트 확인", async delegate { await Job(() => updater.Check()); });
        Add("이전 버전 복구", async delegate { await Job(() => updater.Rollback()); });
        Add("기존 폴더 가져오기", async delegate { using (var f = new FolderBrowserDialog { Description = "기존 pob-zh.exe 또는 Launch.lua가 있는 폴더 선택" }) if (f.ShowDialog() == DialogResult.OK) await Job(() => updater.Import(f.SelectedPath)); });
        Add("내 자료 열기", delegate { Process.Start("explorer.exe", updater.DataPath); });
        status.Text = "빌드와 설정은 별도로 보존됩니다.\n일반 실행: 자동 시작 · Shift를 누르고 실행: 관리 메뉴";
        updater.Report = text => { if (!IsDisposed) BeginInvoke((Action)(() => status.Text = text)); };
        updater.ProcessStarted = () => { if (!IsDisposed) BeginInvoke((Action)(() => { skip.Enabled = false; Hide(); })); };
        FormClosing += (s,e) => { if (busy) e.Cancel = true; };
        Shown += async delegate { if (!manage) { await Task.Delay(100); Run(); } };
    }
    void Add(string text, Action action) { var b = new Button { Text = text, AutoSize = true, Height = 32 }; b.Click += (s,e) => action(); buttons.Controls.Add(b); }
    async Task Job(Action action) {
        if (busy) return; busy = true; buttons.Enabled = false;
        try { await Task.Run(action); status.Text = "완료했습니다. 저장한 빌드와 설정은 유지됩니다."; }
        catch (Exception e) { updater.Log(e.ToString()); status.Text = e.Message; }
        finally { busy = false; buttons.Enabled = true; }
    }
    async void Run() {
        if (busy) return; busy = true; buttons.Enabled = false;
        cancellation = new CancellationTokenSource(); skip.Visible = updater.Installed(updater.State.current); skip.Enabled = true;
        try {
            Process process = await Task.Run(() => updater.Launch(cancellation.Token)); Release running = updater.State.current;
            Hide();
            await Task.Run(() => process.WaitForExit());
            updater.SaveLauncherSettings(running);
            busy = false; Close();
        } catch (Exception e) { updater.Log(e.ToString()); Show(); status.Text = e.Message; busy = false; buttons.Enabled = true; }
        finally { skip.Visible = false; cancellation.Dispose(); cancellation = null; }
    }
}
public static class Program {
    public static readonly string Root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "UmaipoePoB", "Auto");
    [STAThread] public static int Main(string[] args) {
        string bootKey=SelfUpdate.PublicKey();
        if(args.Length==3 && args[0]=="--launcher-health") {
            if(!System.Text.RegularExpressions.Regex.IsMatch(Path.GetFileName(args[1]),"^[a-f0-9]{32}\\.launcher-ready$")) return 2;
            File.WriteAllText(args[1],args[2]);return 0;
        }
        if(args.Contains("--replace-launcher")) return SelfUpdate.WaitAndReplace(Root,Application.ExecutablePath,bootKey);
        if(args.Contains("--queue-self-update")) { SelfUpdate.Queue(Root,Application.ExecutablePath,bootKey);return 0; }
        Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
        Directory.CreateDirectory(Root);
        try {
            SelfUpdate.Queue(Root,Application.ExecutablePath,bootKey);
            using (var guard = new FileStream(Path.Combine(Root, "session.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None)) {
                string stable = Path.Combine(Root, "Umaipoe-PoB.exe");
                if (!File.Exists(stable)) File.Copy(Application.ExecutablePath, stable, false);
                try {
                    string shortcutPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "우마이 한글 PoB 자동 업데이트.lnk");
                    if (!File.Exists(shortcutPath)) {
                        dynamic shell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));
                        dynamic shortcut = shell.CreateShortcut(shortcutPath);
                        shortcut.TargetPath = stable; shortcut.WorkingDirectory = Root;
                        shortcut.Description = "자동 업데이트 PoB · Shift를 누르고 실행하면 관리 메뉴"; shortcut.Save();
                    }
                } catch { }
                string key;
                using (var input = typeof(Program).Assembly.GetManifestResourceStream("public-key.xml")) using (var reader = new StreamReader(input)) key = reader.ReadToEnd();
                var updater = new Updater(Root, key);
                Application.Run(new LauncherWindow(updater, args.Contains("--manage") || (Control.ModifierKeys & Keys.Shift) != 0));
            }
            return 0;
        } catch (IOException) { MessageBox.Show("자동 업데이트 PoB가 이미 실행 중이거나 사용자 폴더에 접근할 수 없습니다.", "우마이 PoB"); return 1; }
        catch (Exception e) { MessageBox.Show(e.Message + "\n기존 버전과 사용자 자료는 그대로 보존됩니다.", "우마이 PoB"); return 1; }
    }
}
#endif
