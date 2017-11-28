####################################
# Extracts measures from the spectrum of labeled regions in a textgrid tier
#
# Specifically: 
#   1 center_of_gravity
#   2 standard_deviation
#   3 skewness
#   4 kertosis
#   5 central_movement
####################################

form Get spectral info
    sentence Input_audio_file_name C:\Users\Tim\Downloads\JC_lectura_FINAL.wav
    sentence Input_textgrid_file_name C:\Users\Tim\Downloads\JC_lectura_FINAL_-_for_pulses.TextGrid
    sentence Output_data_file_name C:\Users\Tim\Downloads\JC_lectura_FINAL_-_with_pulses.csv
    sentence Tier_name votAnalysis
    real spectral_power 2
    real spectral_moment 3
endform

# Load audio file
sound = Read from file: input_audio_file_name$
selectObject: sound


# Load textgrid file
tg = Read from file: input_textgrid_file_name$
selectObject: tg


# Find the target tier (assumes each tier name is unique)
nTiers = Get number of tiers
tierID = -1
for i from 1 to nTiers
    tmpTierName$ = Get tier name: i
    if tmpTierName$ = tier_name$
        if tierID < 0
            tierID = i
        endif
    endif
endfor

# Get the spectral information from each interval
table = Create Table with column names: "table", 0, "filename start_time end_time label center_of_gravity standard_deviation skewness kertosis central_movement"
selectObject: tg
numberOfIntervals = Get number of intervals: tierID
for intervalID from 1 to numberOfIntervals

    # Get interval information
    selectObject: tg
    label$ = Get label of interval: tierID, intervalID
    if label$ <> "" and label$ <> "_"
        tmin = Get start point: tierID, intervalID
        tmax = Get end point: tierID, intervalID

        # Extract the subwav
        selectObject: sound
        subSound = Extract part: tmin, tmax, "rectangular", 1, "no"
        
        # Extract the spectrum
        selectObject: subSound
        spectrum = To Spectrum: "yes"
        selectObject: spectrum
        
        # Get spectrum values
        cog = Get centre of gravity: spectral_power
        stdDev = Get standard deviation: spectral_power
        skew = Get skewness: spectral_power
        kurt = Get kurtosis: spectral_power
        centMom = Get central moment: spectral_moment, spectral_power

        # Store the results in the output table
        selectObject: table
        Append row
        current_row = Get number of rows
        Set string value: current_row, "filename", input_audio_file_name$
        Set numeric value: current_row, "start_time", tmin
        Set numeric value: current_row, "end_time", tmax
        Set string value: current_row, "label", label$
        Set numeric value: current_row, "center_of_gravity", cog
        Set numeric value: current_row, "standard_deviation", stdDev
        Set numeric value: current_row, "skewness", skew
        Set numeric value: current_row, "kertosis", kurt
        Set numeric value: current_row, "central_movement", centMom
            
        # For-loop iteration cleanup
        selectObject: subSound
        Remove

        selectObject: spectrum
        Remove

    endif
endfor

selectObject: table
Save as comma-separated file: output_data_file_name$

# Cleanup
selectObject: sound
Remove

selectObject: tg
Remove

selectObject: table
Remove


