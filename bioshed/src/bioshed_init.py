import os, sys, subprocess, json

SCRIPT_DIR = str(os.path.dirname(os.path.realpath(__file__)))
HOME_PATH = os.path.expanduser('~')
INIT_PATH = os.path.join(HOME_PATH, '.bioshedinit/')
VALID_REGIONS = ['us-west-2', 'us-west-1', 'us-east-1', 'us-east-2', 'af-south-1', 'ap-east-1', \
                 'ap-southeast-3', 'ap-south-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', \
                 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-south-1', 'eu-west-3', 'eu-north-1', \
                 'me-south-1', 'me-central-1', 'se-east-1']
ECR_PUBLIC_REGISTRY = "public.ecr.aws/w7q0j5w1"
BIOSHED_SERVERLESS_API = "https://hu9ug76w32.execute-api.us-west-2.amazonaws.com/prod"

sys.path.append(os.path.join(SCRIPT_DIR, 'bioshed_utils/'))
import quick_utils

def userExists( user ):
    """ Check if username exists in the user database.
    """
    mybody = {"user": user}
    user_exists = quick_utils.post_request(dict(url=BIOSHED_SERVERLESS_API+'/searchusers', body=mybody))
    if "user_found" in user_exists and str(user_exists["user_found"])[0].upper() == "T":
        return True
    else:
        return False

def bioshed_login():
    """ Log into BioShed.
    """
    myuser = input('Enter your BioShed username (email address): ') or ""
    user_exists = False
    if myuser != "":
        user_exists = userExists(myuser)
    if not user_exists:
        print("ERROR: User {} does not exist.".format(str(myuser)))
    return {"login": False, "user": myuser} if not user_exists else {"login": True, "user": myuser}

def bioshed_init( args ):
    """
    system: ubuntu, macosx,...
    cloud: aws, gcp,...
    initpath: path to all init and setup files
    configfile: config file for important config constants
    providerfile: TF provider file
    mainfile: TF main file
    ---
    provider_file

    """
    system_type = args['system']
    init_path = args['initpath']
    which_os = ''

    # first create init directory if doesn't exist
    if not os.path.exists(init_path):
        os.mkdir(init_path)

    if 'ubuntu' in system_type.lower():
        bioshed_init_ubuntu()
        which_os = 'ubuntu'
    elif 'debian' in system_type.lower():
        bioshed_init_ubuntu()
        which_os = 'debian'
    elif 'redhat' in system_type.lower():
        bioshed_init_redhat()
        which_os = 'redhat'
    elif 'macosx' in system_type.lower():
        bioshed_init_macosx()
        which_os = 'macosx'
    elif 'amazon' in system_type.lower():
        bioshed_init_amazonlinux()
        which_os = 'amazonlinux'
    else:
        print('ERROR: Unsupported system OS - exiting.')

    return which_os

def bioshed_setup( args ):
    """
    cloud: aws, gcp,...
    initpath: path to all init and setup files
    configfile: config file for important config constants
    providerfile: TF provider file
    mainfile: TF main file
    ---
    provider_file

    [TODO] fix this: Found preexisting AWS CLI installation: /usr/local/aws-cli/v2/current. Please rerun install script with --update flag.
    """
    cloud_provider = args['cloud']
    init_path = args['initpath']
    config_file = args['configfile']
    provider_file = args['providerfile']
    main_file = args['mainfile']

    if cloud_provider.lower() in ['aws','amazon']:
        bioshed_init_aws()
        provider_file = bioshed_setup_aws( dict(initpath=init_path, configfile=config_file, providerfile=provider_file, mainfile=main_file))
    return provider_file

def bioshed_init_macosx():
    # first make sure brew is installed: https://brew.sh/
    # to install pip: subprocess.call('brew install brew-pip', shell=True)
    # install terraform
    if int(subprocess.call('brew --help', shell=True)) != 0:
        subprocess.call('/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"', shell=True)
        # brew update ?
        # brew upgrade ?
    if int(subprocess.call('terraform --help', shell=True)) != 0:
        subprocess.call('brew tap hashicorp/tap', shell=True)
        subprocess.call('brew install hashicorp/tap/terraform', shell=True)
    if int(subprocess.call('docker --help')) != 0:
        subproess.call('brew cask install docker', shell=True)
    return

def bioshed_init_amazonlinux():
    # install pip
    subprocess.call('sudo yum -y update', shell=True)
    subprocess.call('sudo yum -y install python3-pip zip unzip', shell=True)
    subprocess.call('sudo yum install -y yum-utils', shell=True)

    # install terraform: https://learn.hashicorp.com/tutorials/terraform/install-cli?in=terraform/aws-get-started
    if int(subprocess.call('terraform --help', shell=True)) != 0:
        subprocess.call('sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo', shell=True)
        subprocess.call('sudo yum -y install terraform', shell=True)

    # install docker
    if int(subprocess.call('docker --help', shell=True)) != 0:
        subprocess.call('sudo yum install docker', shell=True)
    return

def bioshed_init_redhat():
    # install pip
    subprocess.call('sudo yum -y update', shell=True)
    subprocess.call('sudo yum -y install python3-pip zip unzip', shell=True)

    # install terraform: https://learn.hashicorp.com/tutorials/terraform/install-cli?in=terraform/aws-get-started
    subprocess.call('sudo yum install -y yum-utils', shell=True)
    subprocess.call('sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo', shell=True)
    subprocess.call('sudo yum -y install terraform', shell=True)

    # install docker
    if int(subprocess.call('docker --help', shell=True)) != 0:
        subprocess.call('sudo yum install docker', shell=True)
    return

def bioshed_init_ubuntu():
    # install pip
    subprocess.call('sudo apt-get -y update', shell=True)
    subprocess.call('sudo apt-get -y install python3-pip zip unzip', shell=True)

    # install terraform: https://learn.hashicorp.com/tutorials/terraform/install-cli?in=terraform/aws-get-started
    subprocess.call('sudo apt-get install -y gnupg software-properties-common', shell=True)
    subprocess.call('wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg', shell=True)
    subprocess.call('gpg --no-default-keyring --keyring /usr/share/keyrings/hashicorp-archive-keyring.gpg --fingerprint', shell=True)
    subprocess.call('echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list', shell=True)
    subprocess.call('sudo apt update', shell=True)
    subprocess.call('sudo apt-get install terraform', shell=True)

    # boto3 for python-based infra control
    # subprocess.call('pip install boto3', shell=True)

    # install docker
    if int(subprocess.call('docker --help', shell=True)) != 0:
        subprocess.call('sudo apt-get install -y docker.io', shell=True)
        # subprocess.call('sudo snap install docker', shell=True)

    return

def bioshed_init_aws():
    # install aws cli and configure
    subprocess.call('pip install awscli', shell=True)
    subprocess.call('curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"', shell=True)
    subprocess.call('unzip awscliv2.zip', shell=True)
    subprocess.call('sudo ./aws/install', shell=True)
    subprocess.call('aws configure', shell=True)

def bioshed_setup_aws( args ):
    """
    initpath: init path
    configfile: config file for important config constants
    providerfile: TF provider file
    mainfile: TF main file
    ---
    """
    # setup terraform provider (AWS): https://learn.hashicorp.com/tutorials/terraform/aws-build
    cwd = os.getcwd()
    INIT_PATH = args['initpath']
    if not os.path.exists(INIT_PATH):
        os.mkdir(INIT_PATH)
    PROVIDER_FILE = args['providerfile'] # os.path.join(INIT_PATH, 'hs_providers.tf')
    MAIN_FILE = args['mainfile'] # os.path.join(INIT_PATH, 'main.tf')
    AWS_CONFIG_FILE = args['configfile']
    KEYS_FILE = os.path.join(INIT_PATH, 'hsconfig.tf')
    AWS_REGION = input('Which region do you want to setup your bioshed infrastructure? (ex: us-west-2, us-east-1, eu-south-1, ca-central-1): ')
    if AWS_REGION not in VALID_REGIONS:
        AWS_REGION = input('Please type a valid AWS region (default: us-west-2): ') or "us-west-2"
    AWS_CONSTANTS_JSON = {}
    AWS_CONSTANTS_JSON["ecr_registry"] = ECR_PUBLIC_REGISTRY
    AWS_CONSTANTS_JSON["aws_region"] = AWS_REGION

    PKEY_INPUT = input('(Needed for running stuff on the cloud): Provide a valid public key for accessing AWS resources (in a separate window, type "ssh-keygen" and paste the public key here) or press ENTER to skip for now: ')
    with open(PROVIDER_FILE,'w') as f:
        f.write('terraform {\n')
        f.write('  required_providers {\n')
        f.write('    aws = {\n')
        f.write('      source  = "hashicorp/aws"\n')
        f.write('      version = "~> 3.0"\n')
        f.write('    }\n')
        f.write('  }\n')
        f.write('}\n')
        f.write('\n')
        f.write('provider "aws" {\n')
        f.write('  region = "{}"\n'.format(AWS_REGION))
        f.write('  shared_credentials_file = "$HOME/.aws/credentials"\n')
        f.write('}\n')
    with open(MAIN_FILE,'w') as f:
        f.write('\n')
    if PKEY_INPUT not in ['',' ',[]]:
        with open(KEYS_FILE,'w') as f:
            f.write(
            """
            resource "aws_key_pair" "deployer" {
              key_name   = "bioshed-managed-key-for-ec2-instances"
            """
            )
            f.write('  public_key = "{}"\n'.format(PKEY_INPUT))
            f.write('}\n\n')
    quick_utils.add_to_json( AWS_CONFIG_FILE, AWS_CONSTANTS_JSON)
    # with open(AWS_CONFIG_FILE,'w') as f:
    #     json.dump(AWS_CONSTANTS_JSON, f)
    os.chdir(INIT_PATH)
    # initialize terraform
    subprocess.call('terraform init', shell=True)
    os.chdir(cwd)
    return PROVIDER_FILE

def bioshed_teardown( args ):
    """ Destroys cloud infrastructure setup by bioshed.
    Be very careful before doing this.

    initpath: init path
    """
    cwd = os.getcwd()
    INIT_PATH = args['initpath']
    os.chdir(INIT_PATH)
    subprocess.call('terraform plan -destroy', shell=True)
    subprocess.call('terraform apply -destroy', shell=True)
    os.chdir(cwd)
    return

def bioshed_run_help():
    """ Help menu for bioshed run.
    """
    print("""
    Run bioinformatics applications with BioShed.
    BioShed allows you to run applications as you would normally.
    Since BioShed is integrated with your cloud environment, you can specify remote file paths.

    Usage:
        bioshed run <optional:CONFIG-ARGS> <MODULE> <PROGRAM-ARGS>

    Examples using AWS cloud storage:
        $ bioshed run fastqc s3://folder1/seq.fastq.gz
        $ bioshed run bwa mem s3://genomes/bwa_index s3://folder1/seq.fastq.gz out://s3://alignments/
        $ bioshed run STAR --genomeDir s3://genomes/hg38_STAR_index/ --readFilesIn s3://fastqs/my.fastq.gz out::s3://alignments/

    Examples using local storage:
        $ bioshed run --local --aws-env-file .env --inputdir /home/fastq/ zcat /input/my.fastq.gz
        $ bioshed run --local cat /input/README.txt

    Examples using hybrid environment:
        $ bioshed run bedtools merge s3://folder1/test.bed out::/data/

    Output:
        bioshed.run.out                 All text printed to the console (STDOUT)
        program.cat.<TIMESTAMP>.1.log   Log file of program output
        run.<TIMESTAMP>.log             Run log JSON
        out::<OUTPUT_FOLDER>            Output folder for all log and data files.
                                        If no output folder is specified, then the input folder is used as the output folder.

    optional CONFIG-ARGS:
        --local                Run application on local system. Requires docker to be installed.
        --aws-env-file <.ENV>  AWS environment file with the following format:
                                 AWS_ACCESS_KEY_ID=[ID]
                                 AWS_SECRET_ACCESS_KEY=[KEY]
                                 AWS_DEFAULT_REGION=[region]
        --inputdir <DIR>       Full path of local input directory. Requires --local.
                               If no input dir is specified, then the current local directory is used as the input directory.

    PROGRAM-ARGS:
        out::<OUTPUT_FOLDER>   Output folder for all log and data files. Specify full remote path.
                               You can also specify full local path if --local option is on.
                               Without this option, files are output back to the input path.
        /input/<FILE>          When using --local and --inputdir options, prefix any local files located in --inputdir with /input/

    """)
