' Basic for COE Rock Island
' Scheduled basic program.
' Should be run a second or so
' after the sensors are measured.

Public Sub Sched_IEEDisplay

Const Comport = "COM2:"

REM Initialize constants
	const NOPARITY = 0
	const ODDPARITY = 1
	const EVENPARITY = 2
	const MARKPARITY = 3
	const SPACEPARITY = 4
	const ONESTOPBIT = 0
	const ONE5STOPBITS = 1
	const TWOSTOPBITS = 2
	const NOHANDSHAKE = 0
	const HANDSHAKE = 1

REM Open COM2 if that is were display is.  Otherwise change to correct COM.
  On Error Resume Next
  aFile = FreeFile
  StatusMsg "File handle = " + str(aFile)
  Open Comport as aFile NoWait
  If Err <>0 Then
     ErrorMsg "FAILED TO OPEN COM2 FOR DISPLAY"
     Exit Sub
  End If

REM Setup up com port
   SetPort aFile, 9600, NOPARITY, 8, ONESTOPBIT, NOHANDSHAKE

   'get lastest head and tailwater values
   A = Tag("PL1")
   StatusMsg "Head: "&(A)
   AV = Format("%1.3f", A)
   B = Tag("TL2")
   StatusMsg "Tail: "&(B)
   BV = Format("%1.3f", B)

   Print aFile, ""
   Print aFile, ""
   Line1 =  "HEAD "+AV+" FT"
   Line2 =  "TAIL "+BV+" FT";
   Print aFile, Line1
   Print aFile, Line2
   SLEEP 5
   REM Close com port
   Close aFile
End Sub
