def get_create_keynote_prompt(text="Apple", width=540, height=430):
    return f"""
tell application "Keynote"
    -- Open Keynote and create a new presentation
    activate
    delay 2
    
    -- Create a new presentation
    make new document
    delay 2
    
    -- Get a reference to the first slide
    tell front document
        tell the current slide
            -- Create a new shape (rectangle)
            set newShape to make new shape
            
            -- Set shape properties - using simple
            set the width of newShape to {width}
            set the height of newShape to {height}
            
            -- Center the shape on the slide
            set the position of newShape to {{400,540}} 
            
            -- Add text to the shape
            set the object text of newShape to "{text}"
            
            -- Format the text
            tell the object text of newShape
                set the font to "Helvetica"
                set the size to 72
                set the alignment to center
            end tell
        end tell
    end tell
end tell
"""

def get_save_keynote_prompt():
    return """
tell application "System Events"
    tell process "Keynote"
        set frontmost to true
        
        -- Press Command+S to open save dialog
        keystroke "s" using command down
        delay 1
        
        -- Type the file path
        keystroke "my_new"
        delay 1
        
        -- Press Return to save
        keystroke return
        delay 2
        
        -- If a file exists dialog appears, press Replace
        try
            if exists button "Replace" of sheet 1 of window 1 then
                click button "Replace" of sheet 1 of window 1
                delay 1
            end if
        end try
        
        -- Press Command+Q to quit Keynote
        keystroke "q" using command down
    end tell
end tell
"""