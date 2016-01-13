numSteps = %(num_steps)s

Read from file... %(input_dir)s/%(input_name)s.wav

for iStep to numSteps
    zeroedI = iStep
    
    Create DurationTier... %(input_name)s_'zeroedI' %(start_time)f %(end_time)f
    %(durationTierPoints)s
    
    select Sound %(input_name)s
    To Manipulation... 0.01 %(pitch_lower_bound)d %(pitch_upper_bound)d
    
    select DurationTier %(input_name)s_'zeroedI'
    plus Manipulation %(input_name)s
    Replace duration tier
    
    select Manipulation %(input_name)s
    Get resynthesis (overlap-add)
    if numSteps == 1
        Save as WAV file... %(output_dir)s/%(output_name)s.wav
    else
        Save as WAV file... %(output_dir)s/%(output_name)s_'numSteps'_'zeroedI'.wav
    endif
    
    Remove
    select Manipulation %(input_name)s
    Remove
    select DurationTier %(input_name)s_'zeroedI'
    Remove
endfor

select Sound %(input_name)s
Remove