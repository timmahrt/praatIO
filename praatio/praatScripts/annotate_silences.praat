####################################
# Splits a file into sound and silence segments
####################################

form Batch annotate sound files for silence
    sentence Input_audio_path C:\Users\Tim\Dropbox\workspace\praatIO\examples\files
    sentence Output_audio_path C:\Users\Tim\Dropbox\workspace\praatIO\examples\files\silence_marked_textgrids
    real Min_pitch_(Hz) 100
    real Time_step_(s) 0.0 (= auto)
    real Sil_threshold_(dB) -25.0
    real Min_sil_dur_(s) 0.1
    real Min_sound_dur_(s) 0.1
    sentence Silent_interval_label silence
    sentence Sounding_interval_label sound
endform

createDirectory: output_audio_path$

strings = Create Strings as file list... list 'input_audio_path$'/*.wav
numberOfFiles = Get number of strings


# BEGIN LOOP
for ifile to numberOfFiles
select strings
filename$ = Get string... ifile

# Load audio file
sound = Read from file: input_audio_path$ + "/" + filename$
selectObject: sound

# Annotation
textgrid = To TextGrid (silences): min_pitch, time_step, sil_threshold, min_sil_dur, min_sound_dur, silent_interval_label$, sounding_interval_label$
selectObject: textgrid

# Output textgrid
Save as text file: output_audio_path$ + "/" + filename$ - ".wav" + ".TextGrid"

# Loop cleanup
selectObject: sound
Remove

selectObject: textgrid
Remove

endfor
# END LOOP


# Final cleanup
selectObject: strings
Remove
