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
		IfWinExist Netflix ahk_class Windows.UI.Core.CoreWindow ahk_exe Netflix.exe
		{
			WinClose Netflix ahk_class Windows.UI.Core.CoreWindow ahk_exe Netflix.exe
		}
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
	; stop playback
	Run, "C:\Program Files\J River\Media Center 23\MC23.exe" /MCC 10002
	; minimise
	Run, "C:\Program Files\J River\Media Center 23\MC23.exe" /MCC 10014
	; set volume in IPC zone to 40%
	Run, "C:\Program Files\J River\Media Center 23\MC23.exe" /MCC "10020`,40:2"
	; set the active zone to IPC to enable volume hot keys
	Run, "C:\Program Files\J River\Media Center 23\MC23.exe" /MCC 10011`,2
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
	} else if (targetApp = "4od") {
		targetUrl := "https://www.channel4.com/"
	} else if (targetApp = "itv") {
		targetUrl := "https://www.itv.com/"
	} else if (targetApp = "prime") {
		targetUrl := "https://www.amazon.com/Prime-Video/b?node=2676882011"
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
	if (jriverActivity = "Music") {
		Run, "C:\Program Files\J River\Media Center 23\MC23.exe" /MCC 22001`,3
	} else if (jriverActivity = "Film") {
		Run, "C:\Program Files\J River\Media Center 23\MC23.exe" /MCC 22001`,5
	} else {
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
