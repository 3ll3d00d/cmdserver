#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.

global stdout := FileOpen("*", "w")
stdout.WriteLine("")

SendCmdToMpc(msg) 
{
	SendMessage,0x0111,msg,,,ahk_class MPC-BE
}

CloseIEIfNecessary()
{
	IfWinExist ahk_class IEFrame
	{
		stdout.WriteLine("Closing IE")
	    WinClose ahk_class IEFrame
		stdout.WriteLine("Closed IE")
	}
}

KillProcessIfNecessary(Name) {
	Process, Exist, %Name%
	if (errorlevel) {
		stdout.WriteLine("Killing " . Name)
		Process, Close, %Name%
		stdout.WriteLine("Killed " . Name)
	} else {
		stdout.WriteLine("Process not running " . Name)
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

stdout.WriteLine("Executing Command: " . targetApp)

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
} else if (targetApp = "CloseAll") {
    closeIE := true
	closeJR := true
	closeNetflix := true
	closeMPC := true
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
			stdout.WriteLine("Closing Netflix")
			WinClose Netflix ahk_class ApplicationFrameWindow 
			stdout.WriteLine("Closed Netflix")
		}
	} else {
		stdout.WriteLine("Unable to handle Netflix, unknown OS " . A_OSVersion)
	}
} 

if (closeJR) {
	stdout.WriteLine("Minimising JRiver")
	Run, "C:\Program Files\J River\Media Center 23\MC23.exe" /MCC 10014
	stdout.WriteLine("Minimised JRiver")
}

if (closeMPC) {
	IfWinExist ahk_class MPC-BE
	{
		stdout.WriteLine("Closing MPC-BE")
		WinClose ahk_class MPC-BE
		stdout.WriteLine("Closed MPC-BE")
	}
	KillProcessIfNecessary("mpc-be64.exe")
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
		stdout.WriteLine("Unable to open IE, unknown target " . targetApp)
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
				stdout.WriteLine("IE already open")
			} else {
				CloseIEIfNecessary()
			}
		}
		if (openIE) {
			stdout.WriteLine("Opening IE")
			Run, "C:\Program Files\Internet Explorer\iexplore.exe" -k %targetUrl%
			stdout.WriteLine("Opened IE")
		}
	}
}

if (!closeNetflix) {
	stdout.WriteLine("Opening Netflix")
	Run % netflixLoc
	stdout.WriteLine("Opened Netflix")
}

if (!closeJR) {
	if (jriverActivity != "Film") {
		stdout.WriteLine("Switching to MC Playing Now")
		Run, "C:\Program Files\J River\Media Center 23\MC23.exe" /MCC 22001`,2
		stdout.WriteLine("Switched to MC Playing Now")
	}
}

if (!closeMPC) {
	IfWinExist ahk_class MPC-BE
	{
		stdout.WriteLine("Activating MPC-BE")
		winactivate ahk_class MPC-BE
		stdout.WriteLine("Activated MPC-BE")
	}
	else
	{
		stdout.WriteLine("Launching MPC-BE")
		Run, C:\Program Files\MPC-BE x64\mpc-be64.exe
		stdout.WriteLine("Launched MPC-BE")
		WinWaitActive ahk_class MPC-BE, , 3
		if ErrorLevel
		{	
			stdout.WriteLine("Unable to activate MPC-BE")
			Exit, 1
		} 
		else 
		{
			IfWinActive, ahk_class MPC-BE
			{
				stdout.WriteLine("Adjusting lipsync offset")
				SendInput, ^v
				Sleep, 5000
				Loop, 14
				{
					SendCmdToMpc(906)
					Sleep 200
				}
				stdout.WriteLine("Adjusted lipsync offset")
				SendCmdToMpc(830)
				stdout.WriteLine("Set to Fullscreen")
			}
		}
	}
}