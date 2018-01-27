#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.

SendCmdToMpc(msg) 
{
	SendMessage,0x0111,msg,,,ahk_class MPC-BE
}

CloseIEIfNecessary()
{
	IfWinExist ahk_class IEFrame
	{
	    WinClose ahk_class IEFrame
	}
}

KillProcessIfNecessary(Name) {
	Process, Exist, %Name%
	if (errorlevel) {
		Process, Close, %Name%
	}
}

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

EnvGet, desktopParent, USERPROFILE
netflixLoc := desktopParent . "\Desktop\Netflix"
targetApp = %1%
jriverActivity = %2%
closeIE := false
closeJR := false
closeNetflix := false
closeMPC := false

if (targetApp = "Netflix") {
	closeIE := true
	closeJR := true
	closeMPC := true
} else if (targetApp = "JRiver") {
	closeIE := true
	closeNetflix := true
	closeMPC := true
} else if (targetApp = "TiVO") {
    closeIE := true
	closeJR := true
	closeNetflix := true
} else {
	closeJR := true
	closeNetflix := true
	closeMPC := true
}	

if (closeIE) {
	CloseIEIfNecessary()
} 

if (closeNetflix) {
	if (A_OSVersion = "WIN_8.1") {
		KillProcessIfNecessary("Netflix.exe")
	} else if (substr(A_OSVersion, 1, 2) = 10) {
		IfWinExist Netflix ahk_class ApplicationFrameWindow 
		{
			WinClose Netflix ahk_class ApplicationFrameWindow 
		}
	} else {
		MsgBox % "Running on unknown OS " . A_OSVersion
	}
} 

if (closeJR) {
	; minimise
	Run, "C:\Program Files\J River\Media Center 23\MC23.exe" /MCC 10014
}

if (closeMPC) {
	IfWinExist ahk_class MPC-BE
	{
		WinClose ahk_class MPC-BE
	}
}

if (!closeIE) {
	targetUrl := ""
	if (targetApp = "iplayer") {
		targetUrl := "https://www.bbc.co.uk/iplayer"
	} else if (targetApp = "all4") {
		targetUrl := "https://www.channel4.com/"
	} else if (targetApp = "itv") {
		targetUrl := "https://www.itv.com/"
	} else if (targetApp = "amazon") {
		targetUrl := "https://www.amazon.co.uk/gp/video/watchlist"
	}
	if (targetUrl = "") {
		MsgBox % "Unknown target " . targetApp
	} else {
		openIE := true
		IfWinExist ahk_class IEFrame
		{
			WinActivate
			WinWaitActive, ahk_class IEFrame, , 1
			activeUrl := GetActiveBrowserURL()
			isSameSite := IsSameSite(targetUrl, activeUrl)
			if (isSameSite) {
				openIE := false
			} else {
				CloseIEIfNecessary()
			}
		}
		if (openIE) {
			Run, "C:\Program Files\Internet Explorer\iexplore.exe" -k %targetUrl%
		}
	}
}

if (!closeNetflix) {
	Run % netflixLoc
}

if (!closeJR) {
	if (jriverActivity != "Film") {
		; show playing now
		Run, "C:\Program Files\J River\Media Center 23\MC23.exe" /MCC 22001`,2
	}
}

if (!closeMPC) {
	IfWinExist ahk_class MPC-BE
	{
		winactivate ahk_class MPC-BE
	}
	else
	{
		Run, C:\Program Files\MPC-BE x64\mpc-be64.exe /fullscreen
		WinWaitActive ahk_class MPC-BE
		IfWinActive, ahk_class MPC-BE
		{
			SendInput, ^v
			Sleep, 5000
			Loop, 14
			{
				SendCmdToMpc(906)
				Sleep 200
			}
		}
	}
}
