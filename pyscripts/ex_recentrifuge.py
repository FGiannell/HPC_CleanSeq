
import asyncssh
import os
import time

from pyscripts.progress import uploadProgress, downloadProgress


async def buildRecentrifugeScript(account: str):
    """Build script to execute Recentrifuge.
    """
    # Write the script file
    with open('scripts/rec_script.sh', 'w', newline='\n') as file:
        file.write('#!/bin/bash' + '\n\n')

        # Add directories
        file.write(
            '#SBATCH --job-name=recentrifuge\n'
            '#SBATCH --time=24:00:00\n'
            '#SBATCH -p g100_usr_bmem \n'
            '#SBATCH -N 1\n'
            '#SBATCH -n 48 \n'
            '#SBATCH --mem=500G \n'
            f'#SBATCH --account {account}\n\n'
        )

        # Add instructions
        # 1. Execute Recentrifuge
        file.write(
            'rcf -f reports/centrifuge_output.txt -n taxonomy -e CSV'
            '\n'
        )
        # 2. Move Recentrifuge output files in recentrifuge_reports directory
        file.write(
            'mv reports/*rcf* reports/recentrifuge_reports'
            '\n'
        )
    
    # Return absolute path of the file
    return os.path.abspath('scripts/rec_script.sh')


async def executeRecentrifuge(
    hostname: str, 
    username: str, 
    password: str
):
    """Function to connect to Galileo100 and run the Recentrifuge script.

    :param hostname: A string which is the host name to connect.
    :param username: A string which is the username of the account
    to connect in the host machine.
    :param password: A string which is the password of the account
    to connect in the host machine.
    """
    print("Executing Recentrifuge")

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

            # Export $PATH to include centrifuge
            proc.stdin.write('export PATH=$SCRATCH/centrifuge:$PATH' + '\n')
            await proc.stdin.drain()
            print("Path exported")

            # Create recentrifuge_reports directory
            proc.stdin.write('mkdir reports/recentrifuge_reports' + '\n')
            await proc.stdin.drain()
            print("directory created")                                              

            # Execute the Recentrifuge script
            print("Started running Recentrifuge script")        
            proc.stdin.write(
                'echo "$(sbatch rec_script.sh | awk \'{print $4}\')$"'
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


async def uploadRecentrifugeScript(
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

        # Start the sftp client
        async with conn.start_sftp_client() as sftp:
            # Navigate to $SCRATCH directory
            await sftp.chdir(scratch_dir)
            
            # Navigate in the working directory
            print("Moving to dec directory")
            await sftp.chdir('dec')

            # Build the script file
            script = await buildRecentrifugeScript(account)

            # Upload script file
            await sftp.put(script, progress_handler=uploadProgress)
            print("OK")

        print("Recentrifuge script uploaded")


async def downloadRecentrifugeReport(
    hostname: str, 
    username: str, 
    password: str
):
    """Function to download the Recentrifuge report from Galileo100.
    
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
            
            # Print all the content of the scratch directory
            ls = await sftp.listdir('.')
            print(f"Content of the directory: \n{ls}")
            
            # Navigate in the working directory
            print("Moving to dec directory")
            await sftp.chdir('dec')

            # Navigate in the reports/recentrifuge_reports directory
            print("Moving to recentrifuge_reports directory")
            await sftp.chdir('reports/recentrifuge_reports')

            # Download the recentrifuge report HTML page
            print("Downloading the centrifuge summary report")
            await sftp.get(
                'centrifuge_output.txt.rcf.html', 
                'templates/recentrifuge_output.html', 
                progress_handler=downloadProgress
            )
            print("OK")

    print("Report page downloaded")