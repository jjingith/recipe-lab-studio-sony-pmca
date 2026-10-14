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
; The app keeps settings.json and library\ beside its own exe, so it must land in a folder its owner
; can write to — hence a per-user install by default (no UAC prompt, {autopf} resolving to
; %LocalAppData%\Programs). The override below puts an "all users / this user only" choice on the
; first page: choosing all users elevates and installs to {commonpf} instead, and the data folder
; falls back to %APPDATA% (see core\library.py) when that folder is not writable.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\release
OutputBaseFilename=RecipeLabStudio-{#MyAppVersion}-Setup
SetupIconFile=..\data\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; the free-of-charge / not-for-sale notice is not a stock LicenseFile page but a first-page site
; notice built in [Code] below: it shows tools\license.txt (all three languages in the one file) and
; gates the Next button on a tick box, which a LicenseFile page cannot do.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "chinesetraditional"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

; The stock messages cover the desktop icon but not a Start Menu one, and say nothing about the
; notice page — so the extra strings live here, one entry per language, keyed by the [Languages]
; Name. {#MyAppName} is expanded by ISPP at compile time, as everywhere else in this script.
[CustomMessages]
english.CreateStartMenuIcon=Create a &Start Menu shortcut
chinesesimplified.CreateStartMenuIcon=创建开始菜单快捷方式(&S)
chinesetraditional.CreateStartMenuIcon=建立開始功能表捷徑(&S)

english.UninstallShortcut=Uninstall {#MyAppName}
chinesesimplified.UninstallShortcut=卸载 {#MyAppName}
chinesetraditional.UninstallShortcut=解除安裝 {#MyAppName}

english.NoticePageTitle=Before you install
chinesesimplified.NoticePageTitle=使用须知
chinesetraditional.NoticePageTitle=使用須知
english.NoticePageSubtitle=Please read the notice below; tick the box to accept it and continue.
chinesesimplified.NoticePageSubtitle=请阅读下面的须知，勾选同意后才能继续。
chinesetraditional.NoticePageSubtitle=請閱讀下面的須知，勾選同意後才能繼續。
english.NoticeHead=Recipe Lab Studio — free-of-charge notice
chinesesimplified.NoticeHead=Recipe Lab Studio —— 使用须知
chinesetraditional.NoticeHead=Recipe Lab Studio —— 使用須知
english.NoticeAgree=I have read the notice above and I agree to it.
chinesesimplified.NoticeAgree=我已阅读并同意上面的须知。
chinesetraditional.NoticeAgree=我已閱讀並同意上面的須知。
english.NoticeMustAgree=Please tick "I have read the notice above and I agree to it" to continue.
chinesesimplified.NoticeMustAgree=请先勾选「我已阅读并同意上面的须知」再继续。
chinesetraditional.NoticeMustAgree=請先勾選「我已閱讀並同意上面的須知」再繼續。

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "menuicon"; Description: "{cm:CreateStartMenuIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\RecipeLabStudio.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
; read by the notice page ([Code]) through ExtractTemporaryFile — never installed anywhere
Source: "..\tools\license.txt"; Flags: dontcopy

[Icons]
; both group entries follow the menuicon task, so unchecking it leaves no Start Menu folder at all
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: menuicon
Name: "{group}\{cm:UninstallShortcut}"; Filename: "{uninstallexe}"; Tasks: menuicon
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

; {app}\library (the user's recipes) and settings.json are deliberately NOT listed for deletion on
; uninstall: they are user data the app creates at run time, not files this installer put there.

[Code]
// The first page: the free-of-charge / not-for-sale notice in a scrollable memo, with a tick box that
// has to be ticked before Next works. Inno's own LicenseFile page has no such box — its Next button
// is always live — so the page is assembled here instead. The text is tools\license.txt, shipped as a
// dontcopy file and extracted to {tmp} on demand; it carries a UTF-8 BOM, which is what lets
// LoadStringsFromFile read the Chinese as Unicode rather than as ANSI bytes.
var
  NoticePage: TWizardPage;
  NoticeMemo: TNewMemo;
  NoticeCheck: TNewCheckBox;

procedure InitializeWizard;
var
  NoticeLines: TArrayOfString;
  I: Integer;
begin
  NoticePage := CreateCustomPage(wpWelcome, ExpandConstant('{cm:NoticePageTitle}'),
                                 ExpandConstant('{cm:NoticePageSubtitle}'));

  NoticeMemo := TNewMemo.Create(NoticePage);
  NoticeMemo.Parent := NoticePage.Surface;
  NoticeMemo.SetBounds(0, 0, NoticePage.SurfaceWidth, NoticePage.SurfaceHeight - 48);
  NoticeMemo.ReadOnly := True;
  NoticeMemo.WordWrap := True;
  NoticeMemo.ScrollBars := ssVertical;
  NoticeMemo.Lines.Add(ExpandConstant('{cm:NoticeHead}'));
  NoticeMemo.Lines.Add('');
  ExtractTemporaryFile('license.txt');
  // the strings go in one at a time: PascalScript's TStrings.AddStrings takes a TStrings, not the
  // TArrayOfString that LoadStringsFromFile hands back
  if LoadStringsFromFile(ExpandConstant('{tmp}') + '\license.txt', NoticeLines) then
    for I := 0 to GetArrayLength(NoticeLines) - 1 do
      NoticeMemo.Lines.Add(NoticeLines[I]);

  NoticeCheck := TNewCheckBox.Create(NoticePage);
  NoticeCheck.Parent := NoticePage.Surface;
  NoticeCheck.SetBounds(0, NoticePage.SurfaceHeight - 40, NoticePage.SurfaceWidth, 24);
  NoticeCheck.Caption := ExpandConstant('{cm:NoticeAgree}');
  NoticeCheck.Checked := False;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (NoticePage <> nil) and (CurPageID = NoticePage.ID) and (not NoticeCheck.Checked) then
  begin
    MsgBox(ExpandConstant('{cm:NoticeMustAgree}'), mbError, MB_OK);
    Result := False;
  end;
end;
