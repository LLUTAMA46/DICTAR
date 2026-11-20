; Instal·lador de DICTAR per a Windows (Inno Setup 6).
; S'instal·la només per a l'usuari: no demana contrasenya d'administrador.

#define NomApp "DICTAR"
#define VersioApp "1.0"

[Setup]
AppId={{6E2B7C1A-4D3F-4B8E-9A51-2C7D0F3B9E14}
AppName={#NomApp}
AppVersion={#VersioApp}
AppPublisher=La Casa de l'Escriptura
DefaultDirName={localappdata}\Programs\{#NomApp}
DefaultGroupName={#NomApp}
DisableProgramGroupPage=yes
DisableDirPage=yes
DisableReadyPage=yes
PrivilegesRequired=lowest
OutputDir=..\sortida
OutputBaseFilename=Instal-la-DICTAR
SetupIconFile=dictar.ico
UninstallDisplayIcon={app}\DICTAR.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
CloseApplications=yes
ShowLanguageDialog=no

[Languages]
Name: "catala"; MessagesFile: "compiler:Languages\Catalan.isl"

[Files]
Source: "..\dist\DICTAR\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\DICTAR"; Filename: "{app}\DICTAR.exe"
Name: "{group}\DICTAR"; Filename: "{app}\DICTAR.exe"
Name: "{group}\Desinstal·la DICTAR"; Filename: "{uninstallexe}"

[Registry]
; DICTAR s'engega sol en obrir l'ordinador (es pot treure des del seu menú)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "DICTAR"; ValueData: """{app}\DICTAR.exe"""; Flags: uninsdeletevalue

[Run]
Filename: "{app}\DICTAR.exe"; Description: "Obre DICTAR ara"; Flags: nowait postinstall
