form Klattgrid to soundfile
    sentence Input_audio_file_name
    sentence Input_klatt_file_name
    sentence Output_audio_file_name
    sentence Resynthesis_method "Cascade"
endform

Read from file: input_audio_file_name$
Read from file: input_klatt_file_name$
plusObject: 1
Filter by vocal tract: resynthesis_method$
Save as WAV file: output_audio_file_name$

exitScript()
