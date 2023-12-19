on run {contactName}
    tell application "Contacts"

        set thePerson to first person whose name contains contactName
        set theNumbers to the phones of thePerson

        repeat with aNumber in theNumbers
            if label of aNumber is equal to "mobile" then
                return value of aNumber
            end if
        end repeat

        if (count of theNumbers) > 0 then
            return value of first item of theNumbers
        else
            return "No number found"
        end if

    end tell
end run
