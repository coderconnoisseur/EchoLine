; Build: iscc /DAppVersion=0.3.0 packaging\installer.iss   (after PyInstaller; output: build\installer\)
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{3F919242-11F4-4A4F-8DD9-F9DEDF2E07D9}
AppName=EchoLine
AppVersion={#AppVersion}
AppPublisher=coderconnoisseur
AppPublisherURL=https://github.com/coderconnoisseur/EchoLine
DefaultDirName={localappdata}\Programs\EchoLine
DefaultGroupName=EchoLine
DisableProgramGroupPage=yes
; Per-user install: no admin prompt, works on locked-down work PCs.
PrivilegesRequired=lowest
OutputDir=..\build\installer
OutputBaseFilename=EchoLine-Setup-{#AppVersion}
SetupIconFile=echoline.ico
UninstallDisplayIcon={app}\EchoLine.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\build\dist\EchoLine\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\EchoLine"; Filename: "{app}\EchoLine.exe"
Name: "{autodesktop}\EchoLine"; Filename: "{app}\EchoLine.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\EchoLine.exe"; Description: "Start EchoLine"; Flags: nowait postinstall skipifsilent

[Registry]
; "Start with Windows" writes this value; remove it with the app.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "EchoLine"; Flags: uninsdeletevalue dontcreatekey
