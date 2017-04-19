####################################
# Splits a file into sound and silence segments
####################################

form Annotate sound files for silence
    sentence Input_audio_fn C:\Users\Tim\Desktop\gen_specs\sirl_project_recordings\whole_speech_recordings_raw\sirl_en_03_synced.wav
    sentence Output_audio_fn C:\Users\Tim\Desktop\gen_specs\sirl_project_recordings\whole_speech_recordings_raw\sirl_en_03_synced_silence.TextGrid
    real Min_pitch_(Hz) 100
    real Time_step_(s) 0.0 (= auto)
    real Sil_threshold_(dB) -25.0
    real Min_sil_dur_(s) 0.1
    real Min_sound_dur_(s) 0.1
    sentence Silent_interval_label silence
    sentence Sounding_interval_label sound
endform

# Load audio file
sound = Read from file: input_audio_fn$
selectObject: sound

# Annotation
textgrid = To TextGrid (silences): min_pitch, time_step, sil_threshold, min_sil_dur, min_sound_dur, silent_interval_label$, sounding_interval_label$
selectObject: textgrid

# Output textgrid
Save as text file: output_audio_fn$

# Cleanup
selectObject: sound
Remove

selectObject: textgrid
Remove
