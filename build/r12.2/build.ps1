param([switch]$TestsOnly)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$out=Join-Path $root 'outputs/pob330-r12.2'
$compiler=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$refs=@('/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll','/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll','/reference:System.Web.Extensions.dll','/reference:Microsoft.CSharp.dll')
& $compiler '/nologo' '/target:exe' '/optimize+' ('/out:'+(Join-Path $PSScriptRoot 'Fixture.exe')) (Join-Path $PSScriptRoot 'Fixture.cs')
if($LASTEXITCODE -ne 0){throw 'Fixture build failed'}
$sources=@((Join-Path $PSScriptRoot 'Updater.cs'),(Join-Path $PSScriptRoot 'SelfUpdate.cs'))
& $compiler @('/nologo','/target:exe','/define:TESTING','/optimize+') @refs ('/out:'+(Join-Path $PSScriptRoot 'UpdaterTests.exe')) @sources (Join-Path $PSScriptRoot 'UpdaterTests.cs') (Join-Path $PSScriptRoot 'DownloadTests.cs')
if($LASTEXITCODE -ne 0){throw 'Test build failed'}
if($TestsOnly){exit 0}
$public=Join-Path $PSScriptRoot 'public-key.xml'
& $compiler @('/nologo','/target:winexe','/platform:x64','/optimize+') @refs ('/win32manifest:'+(Join-Path $root 'work/pob330-startup/launcher/app.manifest')) ('/win32icon:'+(Join-Path $root 'work/pob330-startup/launcher/app.ico')) ('/resource:'+ $public+',public-key.xml') ('/out:'+(Join-Path $out 'Umaipoe-PoB.exe')) @sources
if($LASTEXITCODE -ne 0){throw 'Launcher build failed'}
Get-Item (Join-Path $out 'Umaipoe-PoB.exe') | Select-Object Name,Length
