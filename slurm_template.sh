#!/bin/bash -l
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --mem=16g
#SBATCH -t 96:00:00
#SBATCH --mail-type=END 
#
python p_wrapper.py $SLURM_ARRAY_TASK_ID
