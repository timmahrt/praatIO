form Resynthesize duration
    sentence Input_audio_file_name
    sentence Input_duration_file_name
    sentence Output_audio_file_name
    real MinPitch 75
    real MaxPitch 350
endform

Read from file: input_audio_file_name$
sound = selected ("Sound")

Read from file: input_duration_file_name$
durationtier = selected ("DurationTier")

selectObject: sound
To Manipulation: 0.01, minPitch, maxPitch
manipulation = selected ("Manipulation")

selectObject: durationtier
plus manipulation
Replace duration tier

selectObject: manipulation
Get resynthesis (overlap-add)
Save as WAV file: output_audio_file_name$


exitScript()


