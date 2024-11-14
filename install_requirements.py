
import subprocess
import sys


def installRequirements():
    # File containing the list of requirements
    requirements_file = "requirements.txt"

    try:
        with open(requirements_file, 'r') as file:
            # Read the list of requirements from the requirements.txt file
            packages = file.readlines()

            for package in packages:
                    package = package.strip()
                    if package:
                        # Install the package if not already installed
                        print(f"Installation of package: {package}")
                        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                                
        print("Installation completed")
    except FileNotFoundError:
        print(f"The {requirements_file} file was not found.")
    except subprocess.CalledProcessError as e:
        print(f"Error during installation of package {package}: {e}")


if __name__ == '__main__':
    # Install python requirements
    installRequirements()