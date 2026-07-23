Option Explicit

Dim objShell, objFSO, currentDirectory, binDir, pythonwPath, mainScriptPath

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
currentDirectory = objFSO.GetParentFolderName(WScript.ScriptFullName)

binDir = currentDirectory & "\bin"
pythonwPath = binDir & "\pythonw.exe"
mainScriptPath = currentDirectory & "\core\main.pyw"

' Check if pythonw.exe exists
If Not objFSO.FileExists(pythonwPath) Then
    MsgBox "Python environment not found." & vbCrLf & "Please double-click 'setup.bat' first to initialize.", 16, "Error"
    WScript.Quit 1
End If

' Run the python script silently (0 means hide window)
objShell.Run """" & pythonwPath & """ """ & mainScriptPath & """", 0, False
