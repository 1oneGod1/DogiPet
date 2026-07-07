#define MyAppName "DogiPet"
#define MyAppPublisher "1oneGod1"
#define MyAppURL "https://github.com/1oneGod1/DogiPet"
#define MyAppExeName "DogiPet.exe"
#define MyAppVersion GetEnv("DOGIPET_VERSION")

[Setup]
AppId={{7F3FB13F-903E-4E27-8E55-19921A5567E7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=DogiPet-Setup
SetupIconFile=..\assets\dogipet.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Buat pintasan di desktop"; GroupDescription: "Pintasan tambahan:"; Flags: unchecked
Name: "startup"; Description: "Jalankan DogiPet saat masuk Windows"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\dist\DogiPet.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Jalankan {#MyAppName}"; Flags: nowait postinstall skipifsilent
