; Reel — AI voice-over studio. Inno Setup script.
; Build:  iscc install.iss   (run from video_voiceover\ after build.ps1)
; Requires dist\VideoVoiceOver to exist (run build.ps1 first).

#define AppName "Reel"
#define AppVersion "1.0.0"
#define AppPublisher "Eslam Nabawy"
#define AppExe "VideoVoiceOver.exe"
#define CliExe "VideoVoiceOver_CLI.exe"
#define SrcDir "dist\VideoVoiceOver"

[Setup]
AppId={{9F2C4A17-6B3D-4E58-A1C0-7D5E8B24F913}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=release
OutputBaseFilename=Reel-Setup-{#AppVersion}
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#AppExe}
CloseApplications=yes
RestartApplications=no
ChangesEnvironment=no
DisableDirPage=no

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "models"; Description: "Download AI models now (about 1 GB, needs internet)"; GroupDescription: "Setup options:"; Flags: unchecked

[Files]
Source: "{#SrcDir}\{#AppExe}";         DestDir: "{app}"; Flags: ignoreversion
Source: "{#SrcDir}\{#CliExe}";        DestDir: "{app}"; Flags: ignoreversion
Source: "{#SrcDir}\icon.ico";         DestDir: "{app}"; Flags: ignoreversion
Source: "{#SrcDir}\README.txt";       DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SrcDir}\.env.example";     DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SrcDir}\_internal\*";      DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\output"
Name: "{app}\work"

[Icons]
Name: "{group}\{#AppName}";            Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} CLI";        Filename: "{app}\{#CliExe}"
Name: "{group}\Uninstall {#AppName}";  Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";      Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#CliExe}"; Parameters: "--install-models"; \
    WorkingDir: "{app}"; StatusMsg: "Downloading AI models (about 1 GB)…"; \
    Flags: runhidden waituntilterminated; Tasks: models
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; \
    WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
