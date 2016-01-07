# Based on http://www.fon.hum.uva.nl/praat/manual/Script_for_listing_time_--F0_--intensity.html
#

form Soundfile to pitch and intensity
    sentence Input_audio_file_name C:\Users\Tim\Dropbox\workspace\praatIO\test\files\bobby.wav
    sentence Output_audio_file_name C:\Users\Tim\Dropbox\workspace\praatIO\test\files\pitch_extraction\pitch\bobby.txt
    real Sample_step 0.01
    real Min_pitch 75
    real Max_pitch 450
endform

# Pitch and intensity parameters
# male: 50, 350
# female: 75, 450
# sample_step: 0.01 

Read from file: input_audio_file_name$

#Pitch settings: min_pitch, max_pitch, "Hertz", "autocorrelation", "automatic"

sound = selected ("Sound")
selectObject: sound
tmin = Get start time
tmax = Get end time

To Pitch: 0.001, min_pitch, max_pitch
Rename: "pitch"

selectObject: sound
To Intensity: min_pitch, 0.001, 1
Rename: "intensity"

for i to (tmax-tmin)/sample_step
	time = tmin + i * sample_step
	selectObject: "Pitch pitch"
	pitch = Get value at time: time, "Hertz", "Linear"
	selectObject: "Intensity intensity"
	intensity = Get value at time: time, "Cubic"
	appendFileLine: output_audio_file_name$, fixed$ (time, 2), ",", fixed$ (pitch, 3), ",", fixed$ (intensity, 3)
endfor


# Cleanup

selectObject: "Pitch pitch"
Remove

selectObject: "Intensity intensity"
Remove

selectObject: sound
Remove


