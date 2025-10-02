[Setup]
AppName=InventoryApp
AppVersion=1.0
DefaultDirName={pf}\InventoryApp

[Files]
Source: "main.py"; DestDir: "{app}"
Source: "start_app.bat"; DestDir: "{app}"
Source: "requirements.txt"; DestDir: "{app}"

Source: "modules\*"; DestDir: "{app}\modules"; Flags: recursesubdirs createallsubdirs
Source: "venv\*"; DestDir: "{app}\venv"; Flags: recursesubdirs createallsubdirs
Source: "database\*"; DestDir: "{app}\database"; Flags: recursesubdirs createallsubdirs
Source: "images\*"; DestDir: "{app}\images"; Flags: recursesubdirs createallsubdirs
Source: "*.csv"; DestDir: "{app}"
Source: "*.html"; DestDir: "{app}"

[Icons]
Name: "{group}\InventoryApp"; Filename: "{app}\start_app.bat"

Name: "{group}\Uygulamayı Kaldır"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Inventory Management Assistant"; Filename: "{app}\start_app.bat"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"; GroupDescription: "Ekstra Kısayollar:"

[Run]
Filename: "{app}\start_app.bat"; Description: "Uygulamayı Başlat"; Flags: nowait postinstall skipifsilent
