# Based on http://www.fon.hum.uva.nl/praat/manual/Script_for_listing_time_--F0_--intensity.html
#

form Soundfile to pitch and intensity
    sentence Input_audio_file_name C:\Users\Tim\Dropbox\workspace\praatIO\test\files\bobby.wav
    sentence Output_audio_file_name C:\Users\Tim\Dropbox\workspace\praatIO\test\files\pitch_extraction\pitch\bobby.txt
    real Sample_step 0.01
    real Min_pitch 75
    real Max_pitch 450
    real Silence_threshold 0.03
    real Start_time -1 (= start of the file)
    real End_time -1 (= end of the file)
endform

# Pitch and intensity parameters
# male: 50, 350
# female: 75, 450

# Load audio file
sound = Read from file: input_audio_file_name$
selectObject: sound


# Set the start and end times
if start_time < 0
	tmin = Get start time
else
	tmin = start_time
endif

if end_time <= 0
	tmax = Get end time
else
	tmax = end_time
endif


# Get pitch and intensity tracks
To Pitch (ac): sample_step, min_pitch, 15, "no", silence_threshold, 0.45, 0.01, 0.35, 0.14, max_pitch
Rename: "pitch"

selectObject: sound
To Intensity: min_pitch, sample_step, 1
Rename: "intensity"


# Iterate over the pitch and intensity tracks, one sample at a time
for i to (tmax - tmin) / sample_step
	time = tmin + i * sample_step
	selectObject: "Pitch pitch"
	pitch = Get value at time: time, "Hertz", "Linear"
	selectObject: "Intensity intensity"
	intensity = Get value at time: time, "Cubic"
	appendFileLine: output_data_file_name$, fixed$ (time, 3), ",", fixed$ (pitch, 3), ",", fixed$ (intensity, 3)
endfor


# Cleanup
selectObject: "Pitch pitch"
Remove

selectObject: "Intensity intensity"
Remove

selectObject: sound
Remove
