form Soundfile to klattgrid
    sentence Input_audio_file_name
    sentence Output_audio_file_name
    real Time_step_s 0.005
    real Num_formants 5
    real Max_formant_hz 5500
    real Window_length_s 0.025
    real Pre_emphasis_hz 50.0
    real Pitch_floor_hz 60.0
    real Pitch_ceiling_hz 600.0
    real Min_pitch_for_intensity_hz 100.0
    sentence Subtract_mean_flag "yes"
endform

Read from file: input_audio_file_name$
To KlattGrid (simple): time_step_s, num_formants, max_formant_hz, window_length_s, pre_emphasis_hz, pitch_floor_hz, pitch_ceiling_hz, min_pitch_for_intensity_hz, subtract_mean_flag$
Save as text file: output_audio_file_name$

exitScript()
