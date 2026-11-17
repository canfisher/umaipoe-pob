using System;
using System.IO;
using System.Reflection;
using System.Windows.Forms;
public static class LayoutTests {
    [STAThread] public static int Main(string[] args) {
        Application.EnableVisualStyles();
        using (var form = new LauncherWindow(new Updater(args[0], File.ReadAllText(args[1])), true)) {
            var flags = BindingFlags.NonPublic | BindingFlags.Instance;
            var skip = (Control)typeof(LauncherWindow).GetField("skip",flags).GetValue(form);
            var status = (Control)typeof(LauncherWindow).GetField("status",flags).GetValue(form);
            var buttons = (Control)typeof(LauncherWindow).GetField("buttons",flags).GetValue(form);
            skip.Visible = true; form.CreateControl(); form.PerformLayout();
            if (!form.ClientRectangle.Contains(skip.Bounds) || skip.Bounds.IntersectsWith(status.Bounds) || skip.Bounds.IntersectsWith(buttons.Bounds)) throw new Exception("Skip button is clipped or covered");
            Console.WriteLine("LAYOUT_PASSED status="+status.Bounds+" skip="+skip.Bounds+" buttons="+buttons.Bounds);
        }
        return 0;
    }
}
