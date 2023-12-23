on run {targetBuddyPhone, targetMessage}
    tell application "Messages"
        try
            -- Try to send using iMessage service
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy targetBuddyPhone of targetService
            send targetMessage to targetBuddy
        on error
            try
                -- If iMessage fails, try to send using SMS service
                set targetService to 1st service whose service type = SMS
                set targetBuddy to buddy targetBuddyPhone of targetService
                send targetMessage to targetBuddy
            on error errorMessage
                -- If both iMessage and SMS fail, log or handle the error
                display dialog "Failed to send message: " & errorMessage
            end try
        end try
    end tell
end run