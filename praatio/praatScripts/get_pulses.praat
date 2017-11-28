
form Get Pulses
    sentence Input_audio_file_name C:\Users\Tim\Dropbox\workspace\praatIO\examples\files\bobby.wav
    sentence Output_data_file_name C:\Users\Tim\Dropbox\workspace\praatIO\examples\files\bobby.pulses
    real MinPitch 75
    real MaxPitch 600
endform

# Load audio file
sound = Read from file: input_audio_file_name$

# Get the pulses.
selectObject: sound
pulses = To PointProcess (periodic, cc): minPitch, maxPitch

# Save the pulses
selectObject: pulses
Save as short text file: output_data_file_name$

# Cleanup
selectObject: pulses
Remove

selectObject: sound
Remove