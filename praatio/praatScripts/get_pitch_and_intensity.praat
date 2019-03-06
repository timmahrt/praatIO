# Based on http://www.fon.hum.uva.nl/praat/manual/Script_for_listing_time_--F0_--intensity.html
#

form Soundfile to pitch and intensity
    sentence Input_audio_file_name C:\Users\Tim\Dropbox\workspace\praatIO\examples\files\bobby.wav
    sentence Output_data_file_name C:\Users\Tim\Dropbox\workspace\praatIO\examples\files\pitch_extraction\pitch\bobby.txt
    real Sample_step 0.01
    real Min_pitch 75
    real Max_pitch 450
    real Silence_threshold 0.03
    sentence pitch_unit Hertz
    real Start_time -1 (= start of the file)
    real End_time -1 (= end of the file)
    real Median_filter_window_size 0
    boolean Do_pitch_quadratic_interpolation 0
endform

# Pitch and intensity parameters
# male: 50, 350
# female: 75, 450

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


# Get pitch track
pitch = To Pitch (ac): sample_step, min_pitch, 15, "no", silence_threshold, 0.45, 0.01, 0.35, 0.14, max_pitch


# Do median filtering
if median_filter_window_size > 0
    old_pitch = pitch
    selectObject: pitch
    pitchTier = Down to PitchTier

    selectObject: pitchTier
    num_points = Get number of points

    half_num_samples = floor(median_filter_window_size / 2)
    starting_index = 1 + half_num_samples
    ending_index = num_points - half_num_samples
    
    # We'll reuse the table, rewriting over old values with each pass
    data_table = Create TableOfReal: "table", median_filter_window_size, 1
        
    for point_i from starting_index to ending_index
        
        sub_starting_index = point_i - half_num_samples
        sub_ending_index = point_i + half_num_samples
        
        # Get values
        table_i = 1
        for sub_point_i from sub_starting_index to sub_ending_index
            selectObject: pitchTier
            tmpVal = Get value at index: sub_point_i
            
            selectObject: data_table
            Set value: table_i, 1, tmpVal
            table_i = table_i + 1
        endfor
        
        # Sort values
        selectObject: data_table
        Sort by label: 1, 0
        
        # Get the median
        median_i = half_num_samples + 1
        selectObject: data_table
        median_value = Get value: median_i, 1
        
        # Replace original value
        selectObject: pitchTier
        point_time = Get time from index: point_i
        Remove point: point_i
        Add point: point_time, median_value
        
    endfor
    
    selectObject: pitchTier
    pitch = To Pitch: sample_step, min_pitch, max_pitch

    # Cleanup
    selectObject: data_table
    Remove
    selectObject: pitchTier
    Remove
    selectObject: old_pitch
    Remove
endif


# Do quadratic interpolation if requested
if do_pitch_quadratic_interpolation == 1
    old_pitch = pitch
    selectObject: pitch
    pitchTier = Down to PitchTier
    
    selectObject: pitchTier
    Interpolate quadratically: 4, "Hz"
    pitch = To Pitch: sample_step, min_pitch, max_pitch
    
    selectObject: pitchTier
    Remove
    selectObject: old_pitch
    Remove
endif

# Get intensity track
selectObject: sound
intensity = To Intensity: min_pitch, sample_step, 1

table = Create Table with column names: "table", 0, "time pitch intensity"

# Iterate over the pitch and intensity tracks, one sample at a time
for i to (tmax - tmin) / sample_step
	time = tmin + i * sample_step
	selectObject: pitch
	pitchVal = Get value at time: time, pitch_unit$, "Linear"
	selectObject: intensity
	intensityVal = Get value at time: time, "Cubic"
	
	selectObject: table
	Append row
	current_row = Get number of rows
  	Set numeric value: current_row, "time", time
  	Set numeric value: current_row, "pitch", pitchVal
  	Set numeric value: current_row, "intensity", intensityVal
endfor

Save as comma-separated file: output_data_file_name$

# Cleanup
selectObject: pitch
Remove

selectObject: intensity
Remove

selectObject: sound
Remove

selectObject: table
Remove
