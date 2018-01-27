#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.

IPLAYER := 1000
ITV := 2000
FOUR_OD := 3000
PRIME := 4000
NETFLIX := 5000
TIVO := 6000

IsSameSite(target, active) {
	matchSite := SubStr(target, 9)
	matchLen := StrLen(matchSite)
	activeSite := SubStr(active, 8)
	if (SubStr(activeSite, 1, 1) = "/") {
		activeSite := SubStr(activeSite, 2)
	}
	; TODO convert to using a regex to strip out the site portion of the URL
	; https://stackoverflow.com/questions/27745/getting-parts-of-a-url-regex
	activeSite := SubStr(activeSite, 1, matchLen)
	;MsgBox % "active " . activeSite . " target " . matchSite
	if (activeSite = matchSite) {
		Return true
	} else {
		Return false
	}
}

#Include GetActiveBrowserURL.ahk

IfWinExist ahk_class IEFrame 
{
	activeUrl := GetActiveBrowserURL()
	if (IsSameSite("https://www.bbc.co.uk/iplayer", activeUrl)) {
		Exit, IPLAYER
	} else if (IsSameSite("https://www.itv.com/", activeUrl)) {
		Exit, ITV
	} else if (IsSameSite("https://www.channel4.com/", activeUrl)) {
		Exit, FOUR_OD
	} else if (IsSameSite("https://www.amazon.com/Prime-Video/b?node=2676882011", activeUrl)) {
		Exit, PRIME
	} 
} 

if (A_OSVersion = "WIN_8.1") {
	Process, Exist, "Netflix.exe"
	; this doesn't work
;	IfWinExist Netflix ahk_class Windows.UI.Core.CoreWindow ahk_exe Netflix.exe
	if (errorlevel) {
		Exit, NETFLIX
	}
} else if (substr(A_OSVersion, 1, 2) = 10) {
	IfWinExist Netflix ahk_class ApplicationFrameWindow 
	{
		Exit, NETFLIX
	}
}
IfWinExist ahk_class MPC-BE 
{
	Exit, TIVO
}

