form Change intensity
    sentence Input_audio_file_name
    sentence Output_audio_file_name
    real Intensity_val
    
endform

sound = Read from file: input_audio_file_name$
selectObject: sound
Scale intensity: intensity_val
Save as WAV file: output_audio_file_name$

selectObject: sound
Remove

exitScript()