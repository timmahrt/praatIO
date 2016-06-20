# Based on http://www.fon.hum.uva.nl/praat/manual/Script_for_listing_time_--F0_--intensity.html
#

form Soundfile to pitch and intensity
    sentence Input_audio_file_name C:\Users\Tim\Dropbox\workspace\praatIO\examples\files\bobby.wav
    sentence Output_data_file_name C:\Users\Tim\Dropbox\workspace\praatIO\examples\files\bobby.txt
    real Sample_step 0.01
    real Max_formant 5500 (=male:5000; female:5500; children:<8000)
    real Window_length 0.025
    real Preemphasis 50
    real Start_time -1 (= start of the file)
    real End_time -1 (= end of the file)
endform

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

# Get the formants.
selectObject: sound
formants = To Formant (burg)... sample_step 5 max_formant window_length preemphasis

table = Create Table with column names: "table", 0, "time f1 f2 f3"

# Iterate over the formant tracks, one sample at a time
for i to (tmax - tmin) / sample_step
	time = tmin + i * sample_step
	selectObject: formants
	f1 = Get value at time: 1, time, "Hertz", "Linear"
	f2 = Get value at time: 2, time, "Hertz", "Linear"
	f3 = Get value at time: 3, time, "Hertz", "Linear"

	selectObject: table
	Append row
	current_row = Get number of rows
	Set numeric value: current_row, "time", time
  	Set numeric value: current_row, "f1", f1
  	Set numeric value: current_row, "f2", f2
  	Set numeric value: current_row, "f3", f3

endfor

Save as comma-separated file: output_data_file_name$

# Cleanup
selectObject: formants
Remove

selectObject: sound
Remove

selectObject: table
Remove
