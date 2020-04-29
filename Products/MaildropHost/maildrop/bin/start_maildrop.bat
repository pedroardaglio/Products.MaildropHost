rem    ***
rem    Start script to run the maildrop python process
rem    Developed and graciously contributed by Chris Beaven
rem    You must change the values to reflect your own preferences
rem    ***

rem    Set the maildrop configuration file
set maildropcfg=C:\Program Files\Zope\lib\Python\Products\MaildropHost\config

rem    Where is the python executable?
set pythonexe=C:\Program Files\Zope\bin\python.exe

rem    ----------- No changes needed below this line ----------
"%pythonexe%" "%maildrophome%/maildrop.py" "%maildropcfg%"
pause
