property scriptToRun : (path to desktop as text) & "your.scpt" -- your path to .scpt file
property lookForThisText : "cowin" -- your search term
property theseTitles : {}
repeat
    getNotificationTitles()
    delay 0.1
    set flag_quit to False
    repeat with theItem in theseTitles 
        do shell script "echo `date` " &(theItem as text) & " >> log.txt"
        if theItem contains lookForThisText then
            do shell script "echo " & (theItem as text) & " | sed -e \"s|.*[^0-9]\\([0-9][0-9][0-9][0-9][0-9][0-9]\\)[^0-9].*|\\1|\" > otp.txt"
            set flag_quit to True
           -- tell current application to beep 3 -- Just For Testing
        end if
    end repeat
    if flag_quit is True then
        exit repeat
    end if
end repeat

on quit
    --  Executed when the script quits
    continue quit -- allows the script to quit
end quit

on getNotificationTitles()
    -- This Gets The Titles Of The Currently Displaying Notification Alerts And Banners
    tell application id "com.apple.SystemEvents"
        tell (the first process whose bundle identifier = "com.apple.notificationcenterui")
            set theseWindows to every window whose subrole is ¬
                "AXNotificationCenterAlert" or subrole is "AXNotificationCenterBanner"
            set theseTitles to {}
            repeat with thisWindow in theseWindows
                set titleText to the value of static text 1 of thisWindow
                set the end of theseTitles to titleText
                set subTitleText to the value of static text 1 of scroll area 1 of thisWindow
                set the end of theseTitles to subTitleText
                set notificationText to the value of static text 2 of scroll area 1 of thisWindow
                set the end of theseTitles to notificationText
            end repeat
        end tell
    end tell
end getNotificationTitles
