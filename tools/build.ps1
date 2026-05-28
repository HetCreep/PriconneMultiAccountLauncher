.\.venv\Scripts\pip.exe freeze > requirements.lock.txt
.\.venv\Scripts\python.exe .\tools\build.py

Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "*.spec" -Force -ErrorAction SilentlyContinue

.\.venv\Scripts\pyinstaller.exe PriconneMultiAccountLauncher\PriconneMultiAccountLauncher.py --noconsole --onefile --collect-all customtkinter --collect-all selenium --icon assets\icons\PriconneMultiAccountLauncher.ico

Copy-Item -Path "dist\PriconneMultiAccountLauncher.exe" -Destination "windows" -Force
Copy-Item -Path "assets" -Destination "windows" -Force -Recurse

# Run Inno Setup compiler from user profile directory dynamically
$ISCC = "$env:USERPROFILE\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
& $ISCC setup.iss

Compress-Archive -Path "windows\*" -DestinationPath "dist\PriconneMultiAccountLauncher.zip" -Force
