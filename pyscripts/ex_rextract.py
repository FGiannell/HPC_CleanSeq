
import asyncssh
import os
import time

from pyscripts.progress import uploadProgress, downloadProgress


async def buildRextractScript(
        inputs: list, 
        account: str
):
    """Build script to execute Rextract.

    :param inputs: Array containg the absolute paths of the input
    sequences (string).
    """
    # Extracting sequences name
    if len(inputs) == 1:
        seq1 = os.path.basename(inputs[0])
    if len(inputs) == 2:
        seq1 = os.path.basename(inputs[0])
        seq2 = os.path.basename(inputs[1])

    # Write the script file
    with open('scripts/rex_script.sh', 'w', newline='\n') as file:
        file.write('#!/bin/bash' + '\n\n')

        # Add directories
        file.write(
            '#SBATCH --job-name=rextract\n'
            '#SBATCH --time=24:00:00\n'
            '#SBATCH -p g100_usr_prod \n'
            '#SBATCH -N 1\n'
            '#SBATCH -n 48 \n'
            '#SBATCH --mem=100G \n'
            f'#SBATCH --account {account}\n\n'
        )

        # Add instructions
        # 1. Execute Recentrifuge
        # 1.1 Case single-end reads
        if len(inputs) == 1:  
            file.write(
                f'rextract -f reports/centrifuge_output.txt -n taxonomy '
                f'-q {seq1} -c -u -d'
                '\n'
            )
        # 1.2 Case paired-end reads
        elif len(inputs) == 2:
            file.write(
                f'rextract -f reports/centrifuge_output.txt -n taxonomy '
                f'-1 {seq1} -2 {seq2} -c -u -d'
                '\n'
            )
    
    # Return absolute path of the file
    return os.path.abspath('scripts/rex_script.sh')


async def executeRextract(
    hostname: str, 
    username: str, 
    password: str
):
    """Function to connect to Galileo100 and run the Rextract script.

    :param hostname: A string which is the host name to connect.
    :param username: A string which is the username of the account
    to connect in the host machine.
    :param password: A string which is the password of the account
    to connect in the host machine.
    """
    print("Executing Rextract")

    # Connect to remote host
    async with asyncssh.connect(
        hostname, 
        username=username,
        password=password, 
        known_hosts=None
    ) as conn:
        async with conn.create_process() as proc:
            # Navigate in the working directory
            proc.stdin.write('cd $SCRATCH/dec' + '\n')
            await proc.stdin.drain()

            # Import profile and modules and activate python environment
            proc.stdin.write('module load profile/bioinf' + '\n')
            await proc.stdin.drain()
            proc.stdin.write('module load autoload gcc' + '\n')
            await proc.stdin.drain()
            proc.stdin.write('module load python/3.8.12--gcc--10.2.0' + '\n')
            await proc.stdin.drain()
            proc.stdin.write('python3 -m venv recenv' + '\n')
            await proc.stdin.drain()
            proc.stdin.write('source recenv/bin/activate' + '\n')
            await proc.stdin.drain()
            proc.stdin.write('echo "$(pip install recentrifuge xlrd)$"' + '\n')
            await proc.stdin.drain()
            result = await proc.stdout.readuntil('$')
            print("Module loaded and python environment activated")

            # Create cleaned_sequences directory
            proc.stdin.write('mkdir cleaned_sequences' + '\n')
            await proc.stdin.drain()
            print("directory created")                                              

            # Execute the Rextract script
            print("Started running Rextract script")        
            proc.stdin.write(
                'echo "$(sbatch rex_script.sh | awk \'{print $4}\')$"'
                '\n'
            )
            await proc.stdin.drain()
            
            # Save the JobID of the script
            result = await proc.stdout.readuntil('$')
            job_ID = result[:-1].replace('\n', '')

            print(f"JobID = {job_ID}")
            
            print("Waiting for the rextract job to be finished")

            # Wait for the job to be finished
            while True:
                proc.stdin.write(
                    f'echo $(squeue -j {job_ID} --format="%T" -h)$'
                    '\n'
                )
                await proc.stdin.drain()
                result = await proc.stdout.readuntil('$')
                state = result[:-1].replace('\n', '')

                print(
                    f"\rJobId = {job_ID}: state -> {state}", 
                    end='', 
                    flush=True
                )

                if state not in ['PENDING', 'RUNNING', 'CONFIGURING']:
                    break
                else:
                    time.sleep(3)

            print("Script executed")


async def uploadRextractScript(
    hostname: str, 
    username: str, 
    password: str,
    account: str
):
    """Upload script on cluster using SFTP.
    
    :param hostname: A string which is the host name to connect.
    :param username: A string which is the username of the account
    to connect in the host machine.
    :param password: A string which is the password of the account
    to connect in the host machine.
    """
    async with asyncssh.connect(
        hostname, 
        username=username,
        password=password, 
        known_hosts=None
    ) as conn:
        # Get $SCRATCH directory path
        command = await conn.run('echo $SCRATCH')
        scratch_dir = command.stdout[:-1]

        # Get input files names
        command = await conn.run('echo $(ls $SCRATCH/dec/*fastq*)')
        inputs = (command.stdout[:-1]).split()

        # Start the sftp client
        async with conn.start_sftp_client() as sftp:
            # Navigate to $SCRATCH directory
            await sftp.chdir(scratch_dir)
            
            # Navigate in the working directory
            print("Moving to dec directory")
            await sftp.chdir('dec')

            # Build the script file
            script = await buildRextractScript(inputs, account)

            # Upload script file
            await sftp.put(script, progress_handler=uploadProgress)
            print("OK")

        print("Rextract script uploaded")


async def downloadRextractSequences(
    hostname: str, 
    username: str, 
    password: str
):
    """Function to download the Rextract cleaned sequences from Galileo100.
    
    :param hostname: A string which is the host name to connect.
    :param username: A string which is the username of the account
    to connect in the host machine.
    :param password: A string which is the password of the account
    to connect in the host machine.
    """
    async with asyncssh.connect(
        hostname, 
        username=username,
        password=password, 
        known_hosts=None
    ) as conn:
        # Get $SCRATCH directory path
        command = await conn.run('echo $SCRATCH')
        scratch_dir = command.stdout[:-1]

        # Start the sftp client
        async with conn.start_sftp_client() as sftp:
            # Navigate to $SCRATCH directory
            await sftp.chdir(scratch_dir)
            
            # Navigate in the working directory
            print("Moving to dec directory")
            await sftp.chdir('dec')

            # Print all the content of the scratch directory
            ls = await sftp.listdir('.')
            print(f"Content of the directory: \n{ls}")

            # Get the names of the "cleaned" sequences
            files = []
            for file in ls:
                if "rxtr" in file:
                    files.append(file)
                    print(file)

            # Download the cleaned_sequences directory
            print("Downloading the cleaned sequences")
            for file in files:
                await sftp.get(
                    file, 
                    'download/', 
                    progress_handler=downloadProgress
                )
            print("OK")

    print("Cleaned sequences downloaded")