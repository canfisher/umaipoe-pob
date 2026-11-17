using System;
using System.IO;
using System.Threading;
public static class Fixture {
    public static int Main() {
        if (File.Exists("fail-start")) return 2;
        string ready=Environment.GetEnvironmentVariable("UMAIPOE_READY_FILE");
        if(!String.IsNullOrEmpty(ready)) File.WriteAllText(ready, Environment.GetEnvironmentVariable("UMAIPOE_READY_TOKEN"));
        Thread.Sleep(15000);
        return 0;
    }
}
