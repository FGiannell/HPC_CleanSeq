#!/bin/bash

#SBATCH --job-name=centrifuge
#SBATCH --time=24:00:00
#SBATCH -p g100_usr_prod 
#SBATCH -N 1
#SBATCH -n 48 
#SBATCH --mem=100G 
#SBATCH --account ELIX5_dimartin

centrifuge-build -p 48 --conversion-table seqid2taxid.map --taxonomy-tree taxonomy/nodes.dmp --name-table taxonomy/names.dmp sequences.fna database/abv
centrifuge -x database/abv -1 C_os_1_1.fastq.gz -2 C_os_1_2.fastq.gz -S reports/centrifuge_output.txt -p 48
