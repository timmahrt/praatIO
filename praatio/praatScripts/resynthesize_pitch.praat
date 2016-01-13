form Resynthesize pitch
    sentence Input_audio_file_name
    sentence Input_pitch_file_name
    sentence Output_audio_file_name
    real MinPitch 75
    real MaxPitch 350
endform

Read from file: input_audio_file_name$
sound = selected ("Sound")

Read from file: input_pitch_file_name$
pitchtier = selected ("PitchTier")

selectObject: sound
To Manipulation: 0.01, minPitch, maxPitch
manipulation = selected ("Manipulation")

selectObject: pitchtier
plus manipulation
Replace pitch tier

selectObject: manipulation
Get resynthesis (overlap-add)
Save as WAV file: output_audio_file_name$
Remove

selectObject: manipulation
Remove
selectObject: pitchtier
Remove
selectObject: sound
Remove

exitScript()
