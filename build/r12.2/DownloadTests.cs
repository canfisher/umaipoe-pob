using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

public static class DownloadTests {
    static void ServerTest(string root, string name, string response, bool cancel, Action<bool,string> check) {
        var listener = new TcpListener(IPAddress.Loopback, 0); listener.Start();
        int port = ((IPEndPoint)listener.LocalEndpoint).Port;
        var end = new ManualResetEventSlim();
        var server = Task.Run(() => {
            using (var client = listener.AcceptTcpClient()) using (var stream = client.GetStream()) {
                stream.ReadTimeout = 4000; var b = new byte[4096]; stream.Read(b, 0, b.Length);
                if (response != null) { b = Encoding.ASCII.GetBytes(response); stream.Write(b, 0, b.Length); stream.Flush(); }
                end.Wait(4000);
            }
        });
        var timer = Stopwatch.StartNew(); Exception error = null; long progress = 0;
        using (var token = new CancellationTokenSource()) {
            if (cancel) token.CancelAfter(150);
            try { Updater.DownloadCore(new Uri("http://127.0.0.1:"+port+"/"), Path.Combine(root,name), 64, 500, token.Token, bytes=>progress=bytes, uri=>uri.IsLoopback && uri.Port==port); }
            catch (Exception e) { error=e; }
            finally { end.Set(); listener.Stop(); server.GetAwaiter().GetResult(); }
        }
        if (name=="success") check(error==null && progress==2 && File.ReadAllText(Path.Combine(root,name))=="OK", "download reports progress and preserves exact body");
        else check(timer.ElapsedMilliseconds<2500 && (cancel ? error is OperationCanceledException : error is TimeoutException), "bounded download " + name);
    }
    public static void Run(string root, Action<bool,string> check) {
        ServerTest(root,"headers-stall",null,false,check);
        ServerTest(root,"body-stall","HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\nx",false,check);
        ServerTest(root,"cancel","HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\nx",true,check);
        ServerTest(root,"success","HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK",false,check);
    }
}
