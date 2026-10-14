; Inno Setup script for Recipe Lab Studio — the single-exe installer published on GitHub beside the
; portable zip. tools\package_release.py compiles this, generating a defines file from ui\i18n.py
; (build\release_defines.iss) and pointing RELEASE_DEFINES at it, so the version, publisher and
; repo URL live in exactly one place — ui\i18n.py — and never have to be retyped here.

#ifdef RELEASE_DEFINES
  #include RELEASE_DEFINES
#endif

; fallbacks, used only when this script is compiled directly without package_release.py
#ifndef MyAppVersion
  #define MyAppVersion "1.1"
#endif
#ifndef MyAppPublisher
  #define MyAppPublisher "jiajun zhou"
#endif
#ifndef MyAppURL
  #define MyAppURL "https://github.com/"
#endif

#define MyAppName "Recipe Lab Studio"
#define MyAppExeName "RecipeLabStudio.exe"

[Setup]
AppId={{2A7F51E8-9C43-4B6D-8E15-3F0D9A6C4B72}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; A per-user install (no UAC prompt): the app writes settings.json and library\ next to its own exe,
; so it has to live in a folder the user owns.
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=RecipeLabStudio-{#MyAppVersion}-Setup
SetupIconFile=..\data\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; a license page the user must accept before installing: the free-of-charge / not-for-sale notice,
; with all three UI languages in the one file (Inno shows a single LicenseFile whatever the language)
LicenseFile=..\tools\license.txt
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "chinesetraditional"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\RecipeLabStudio.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

; {app}\library (the user's recipes) and settings.json are deliberately NOT listed for deletion on
; uninstall: they are user data the app creates at run time, not files this installer put there.
