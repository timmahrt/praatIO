# Based on http://www.fon.hum.uva.nl/praat/manual/Script_for_listing_time_--F0_--intensity.html
#

form Soundfile to pitch and intensity segments
    sentence Input_audio_file_name C:\Users\Tim\Dropbox\workspace\praatIO\test\files\bobby.wav
    sentence Output_audio_file_name C:\Users\Tim\Dropbox\workspace\praatIO\test\files\pitch_extraction\pitch\bobby.txt
    sentence Input_textgrid_file_name C:\Users\Tim\Downloads\MCRPfiles.tar\bobby_phones.Textgrid
    sentence tier_name phone
    real Sample_step 0.01
    real Min_pitch 75
    real Max_pitch 450
    real Silence_threshold 0.03
endform

# Pitch and intensity parameters
# male: 50, 350
# female: 75, 450


# Load audio file
sound = Read from file: input_audio_file_name$
selectObject: sound


# Get pitch and intensity tracks
To Pitch (ac): sample_step, min_pitch, 15, "no", silence_threshold, 0.45, 0.01, 0.35, 0.14, max_pitch
Rename: "pitch"

selectObject: sound
To Intensity: min_pitch, sample_step, 1
Rename: "intensity"


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


# Get the pitch values within each entry
numberOfIntervals = Get number of intervals: tierID
for intervalID from 1 to numberOfIntervals

    selectObject: tg
    intervalName$ = Get label of interval: tierID, intervalID
    if intervalName$ <> ""
        tmin = Get start point: tierID, intervalID
        tmax = Get end point: tierID, intervalID

	# Iterate over the pitch and intensity tracks, one sample at a time
        for i to (tmax - tmin) / sample_step
	    time = tmin + i * sample_step
	    selectObject: "Pitch pitch"
	    pitch = Get value at time: time, "Hertz", "Linear"
	    selectObject: "Intensity intensity"
	    intensity = Get value at time: time, "Cubic"
	    appendFileLine: output_data_file_name$, fixed$ (time, 3), ",", fixed$ (pitch, 3), ",", fixed$ (intensity, 3)
        endfor
    endif
endfor


# Cleanup
selectObject: "Pitch pitch"
Remove

selectObject: "Intensity intensity"
Remove

selectObject: sound
Remove

selectObject: tg
Remove
