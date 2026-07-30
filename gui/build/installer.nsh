; Custom NSIS hooks for Game AI Foundry (electron-builder include).
; Assisted installer already shows directory page when oneClick=false +
; allowToChangeInstallationDirectory=true.
;
; On uninstall (not on upgrade), remove Electron userData/cache and ~/.gamefactory
; so API keys, toolchain downloads, and workspace are gone.

!include "LogicLib.nsh"

!macro customUnInstall
  ${IfNot} ${isUpdated}
    ; Current-user context for roaming / local AppData and PROFILE.
    SetShellVarContext current
    RMDir /r "$APPDATA\game-ai-foundry-gui"
    RMDir /r "$LOCALAPPDATA\game-ai-foundry-gui"
    RMDir /r "$PROFILE\.gamefactory"

    ; If installed for all users, also wipe the installing admin's data above;
    ; all-users AppData for other accounts is not touched (Windows limitation).
    SetShellVarContext all
    RMDir /r "$APPDATA\game-ai-foundry-gui"
    RMDir /r "$LOCALAPPDATA\game-ai-foundry-gui"
  ${EndIf}
!macroend
