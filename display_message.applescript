on run argv
    set theBuddy to item 1 of argv
    set theMessage to " " 

    tell application "Messages" 
        set theService to 1st service whose service type is iMessage
        set theBuddy to buddy theBuddy of theService
        set theChat to make new text chat with properties {participants:{theBuddy}}
        
        send theMessage to theChat
    end tell
end run
