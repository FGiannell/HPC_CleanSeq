#!/bin/bash

#SBATCH --job-name=recentrifuge
#SBATCH --time=24:00:00
#SBATCH -p g100_usr_prod 
#SBATCH -N 1
#SBATCH -n 48 
#SBATCH --mem=100G 
#SBATCH --account ELIX5_dimartin

rcf -f reports/centrifuge_output.txt -n taxonomy -e CSV
mv reports/*rcf* reports/recentrifuge_reports
