
import asyncssh
import os
import time
import logging

from pyscripts.progress import uploadProgress, downloadProgress


#logging.basicConfig(level=logging.DEBUG)


async def buildCentrifugeScript(
        inputs: list, 
        account: str
):
    """Function to build the Centrifuge script.

    :param inputs: Array of strings containing the names of the
    raw sequences file/s to include in the script.
    """
    # Extracting sequences name
    if len(inputs) == 1:
        seq1 = os.path.basename(inputs[0])
    if len(inputs) == 2:
        seq1 = os.path.basename(inputs[0])
        seq2 = os.path.basename(inputs[1])

    script = '#!/bin/bash' + '\n\n'

    # Add directories
    script += (
        '#SBATCH --job-name=centrifuge\n'
        '#SBATCH --time=24:00:00\n'
        '#SBATCH -p g100_usr_prod \n'
        '#SBATCH -N 1\n'
        '#SBATCH -n 48 \n'
        '#SBATCH --mem=100G \n'
        f'#SBATCH --account {account}\n\n'
    )

    # Add instructions
    # 1. Build the index
    script += (
        'centrifuge-build -p 48 --conversion-table seqid2taxid.map '
        '--taxonomy-tree taxonomy/nodes.dmp --name-table '
        'taxonomy/names.dmp sequences.fna database/abv'
        '\n'
    )
    # 2. Execute Centrifuge on the index
    # 2.1 Case single-end reads
    if len(inputs) == 1:        
        script += (
            f'centrifuge -x database/abv -U {seq1} '
            '-S reports/centrifuge_output.txt -p 48'
            '\n'
        )
    # 2.2 Case paired-end reads
    elif len(inputs) == 2:  
        script += (
            f'centrifuge -x database/abv -1 {seq1} -2 {seq2} '
            '-S reports/centrifuge_output.txt -p 48'
            '\n'
        )

    # Write the script file
    with open('scripts/cen_script.sh', 'w') as file:
        file.write(script)
    
    # Return absolute path of the file
    return os.path.abspath('scripts/cen_script.sh')


async def uploadReads(
    hostname: str, 
    username: str, 
    password: str,
    account: str,  
    inputs: list
):
    """Function to upload input reads and the Centrifuge script
    on the cluster using SFTP.

    :param hostname: A string which is the host name to connect.
    :param username: A string which is the username of the account
    to connect in the host machine.
    :param password: A string which is the password of the account
    to connect in the host machine.
    :param inputs: Array of strings containing the names of the
    raw sequences file/s to include in the script.
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

            # Print all the content of the scratch directory
            ls = await sftp.listdir('.')
            print(f"Content of the directory: \n{ls}")

            # Delete 'dec' directory if already exists
            if 'dec' in ls:
                print("Deleting previous decontamination directory")
                await sftp.rmtree('dec')

            # Create a new 'dec' directory
            print("Creating the decontamination directory")
            await sftp.mkdir('dec')

            # Navigate in the working directory
            print("Moving to dec directory")
            await sftp.chdir('dec')

            # Upload input1 and input 2 files
            for input in inputs:                
                print(f"Uploading file with path: {input}")
                await sftp.put(input, progress_handler=uploadProgress)
                print("OK")

            # Build the script file
            script = await buildCentrifugeScript(inputs, account)

            # Upload script file
            await sftp.put(script, progress_handler=uploadProgress)
            print("OK")

    print("Files uploaded")


async def executeCentrifuge(
    hostname: str, 
    username: str, 
    password: str, 
    domains: list
):
    """Function to connect to Galileo100 and run the Centrifuge
    script.

    :param hostname: A string which is the host name to connect.
    :param username: A string which is the username of the account
    to connect in the host machine.
    :param password: A string which is the password of the account
    to connect in the host machine.
    :param domains: Array of strings containing the names of the
    biological domains.
    """
    # Create the domains string
    dom = ''
    for i in range(len(domains)):
        if i == 0:
            dom = domains[i]
        else:
            dom += ',' + domains[i]

    print("Executing centrifuge")

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

            # Import profile and modules
            proc.stdin.write('module load profile/bioinf' + '\n')
            await proc.stdin.drain()
            proc.stdin.write('module load autoload gcc' + '\n')
            await proc.stdin.drain()
            proc.stdin.write('module load autoload python' + '\n')
            await proc.stdin.drain()
            print("Module loaded")

            # Export $PATH to include centrifuge
            proc.stdin.write('export PATH=$SCRATCH/centrifuge:$PATH' + '\n')
            await proc.stdin.drain()
            print("Path exported")

            # Create directories
            proc.stdin.write('mkdir taxonomy library database reports' + '\n')
            await proc.stdin.drain()
            print("directories created")

            # Download taxonomy
            proc.stdin.write(
                'echo "$(centrifuge-download -o taxonomy taxonomy)$"' + '\n'
            )
            await proc.stdin.drain()
            result = await proc.stdout.readuntil('$')
            print(result[:-1])
            print("taxonomy downloaded")

            # Download sequences
            print(f"Started library download ({dom})")         
            proc.stdin.write(
                f'echo "$(centrifuge-download -v -l -P 4 '
                f'-o library -d "{dom}" '
                'refseq > seqid2taxid.map)$"'
                '\n'
            )
            await proc.stdin.drain()
            result = await proc.stdout.readuntil('$')
            print(result[:-1])
            print("Library downloaded")                         

            # Concatenate all the downloaded sequences
            print(f"Started sequences concatenation")           
            proc.stdin.write(
                'echo $(cat library/*/*.fna > sequences.fna)$'
                '\n'
            )
            await proc.stdin.drain()
            result = await proc.stdout.readuntil('$')
            print(result[:-1])
            print("Sequences concatenated")                      

            # Execute the centrifuge script
            print("Started running Centrifuge script")        
            proc.stdin.write(
                'echo "$(sbatch cen_script.sh | awk \'{print $4}\')$"'
                '\n'
            )
            await proc.stdin.drain()
            
            # Save the JobID of the script
            result = await proc.stdout.readuntil('$')
            job_ID = result[:-1].replace('\n', '')

            print(f"JobID = {job_ID}")
            
            print("Waiting for the centrifuge job to be finished")
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
                elif state == 'FAILED':
                    print("Something went wrong")
                else:
                    time.sleep(3)

            print("Script executed")


async def downloadCentrifugeReport(
    hostname: str, 
    username: str, 
    password: str
):
    """Function to download the Centrifuge summary report from Galileo100.

    :param hostname: A string which is the host name to connect.
    :param username: A string which is the username of the account
    to connect in the host machine.
    :param password: A string which is the password of the account
    to connect in the host machine.
    """
    try:
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

                # Print all the content of the scratch directory
                ls = await sftp.listdir('.')
                print(f"Content of the directory: \n{ls}")

                # Navigate in the working directory
                print("Moving to dec directory")
                await sftp.chdir('dec')

                # Download the centrifuge_report.tsv file
                print("Downloading the centrifuge summary report")
                await sftp.get(
                    'centrifuge_report.tsv', 
                    'download/centrifuge_report.tsv', 
                    progress_handler=downloadProgress
                )
                print("OK")
    except asyncssh.sftp.SFTPNoSuchFile as e:
        print(f"ERROR: Centrifuge report not found.\n{e}")
    
    print("Report downloaded")