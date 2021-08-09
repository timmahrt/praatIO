form Change gender
    sentence Input_audio_file_name
    sentence Output_audio_file_name
    real Pitch_floor 75.0
    real Pitch_ceiling 600.0
    real Formant_shift_ratio 1.1
    real New_pitch_median 0.0 # No change
    real Pitch_range_factor 1.0 # No change
    real Duration_factor 1.0
endform

Read from file: input_audio_file_name$
Change gender: pitch_floor, pitch_ceiling, formant_shift_ratio, new_pitch_median, pitch_range_factor, duration_factor
Save as WAV file: output_audio_file_name$

exitScript()
