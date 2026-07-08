@echo off
echo Starting InstaFlow Local Assistant...
echo This will check for videos older than 3 days, edit them, and move them to your staging folder.
echo Please keep this window open for the assistant to run.
cd /d "D:\insta upload"

:loop
python local_assistant.py
echo Waiting 1 hour before checking for new videos again...
timeout /t 3600 /nobreak
goto loop
