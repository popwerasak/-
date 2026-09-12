; Inno Setup script - สร้างตัวติดตั้ง (Setup.exe) สำหรับโปรแกรมแตกไฟล์ ZIP/RAR
; คอมไพล์ด้วย Inno Setup 6 (https://jrsoftware.org/isinfo.php)
;   ISCC.exe installer\setup.iss
; ต้อง build ไฟล์ dist\ExtractZipRar.exe ด้วย PyInstaller ไว้ก่อน (ดู README.md)

#define MyAppName "ExtractZipRar"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ExtractZipRar"
#define MyAppExeName "ExtractZipRar.exe"

[Setup]
AppId={{8F1E7B2A-6C3D-4E5A-9B1F-2D3C4E5F6A7B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=ExtractZipRarSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "สร้างไอคอนบนหน้าจอ (Desktop)"; GroupDescription: "ทางลัดเพิ่มเติม:"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\ถอนการติดตั้ง {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "เปิดโปรแกรมทันทีหลังติดตั้ง"; Flags: nowait postinstall skipifsilent
