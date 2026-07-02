@echo off
echo Starting InstaFlow Local Pusher...
echo This will check for videos, edit them, and push them to the GitHub Cloud Queue.
echo Please keep this window open for the automation to run.
cd /d "D:\insta upload"

:loop
python local_pusher.py
echo Waiting 10 minutes before checking for new videos again...
timeout /t 600 /nobreak
goto loop
