#!/bin/bash

#SBATCH --job-name=rextract
#SBATCH --time=24:00:00
#SBATCH -p g100_usr_prod 
#SBATCH -N 1
#SBATCH -n 48 
#SBATCH --mem=100G 
#SBATCH --account ELIX5_dimartin

rextract -f reports/centrifuge_output.txt -n taxonomy -1 C_os_4_1.fastq.gz -2 C_os_4_2.fastq.gz -c -d
mv *rxtr* cleaned_sequences
tar -czvf cleaned_sequences.tar.gz cleaned_sequences/
