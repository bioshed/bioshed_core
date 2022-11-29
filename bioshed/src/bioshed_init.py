import os, sys, subprocess, json, uuid

SCRIPT_DIR = str(os.path.dirname(os.path.realpath(__file__)))
HOME_PATH = os.path.expanduser('~')
INIT_PATH = os.path.join(HOME_PATH, '.bioshedinit/')
VALID_REGIONS = ['us-west-2', 'us-west-1', 'us-east-1', 'us-east-2', 'af-south-1', 'ap-east-1', \
                 'ap-southeast-3', 'ap-south-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', \
                 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-south-1', 'eu-west-3', 'eu-north-1', \
                 'me-south-1', 'me-central-1', 'se-east-1']
VALID_REGION_NUMBERS = {'1': 'us-west-1', '2': 'us-west-2', '3': 'us-east-1', '4': 'us-east-2', '5': 'ap-south-1', \
                        '6': 'ap-northeast-1', '7': 'ap-northeast-2', '8': 'ap-southeast-1', '9': 'ca-central-1', '10': 'eu-west-1', '11': 'eu-west-2', \
                        '12': 'eu-west-3', '13': 'eu-central-1'}

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
    elif 'centos' in system_type.lower():
        bioshed_init_redhat()
        which_os = 'centos'
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
    setup_again = 'Y'

    if cloud_provider.lower() in ['aws','amazon']:
        cloud_provider = 'aws'
        if cloud_setup( dict(cloud=cloud_provider, configfile=config_file) ):
            setup_again = PKEY_INPUT = input('Detected existing setup. Overwrite? (Y/N): ') or 'N'
        if setup_again.upper()[0] == 'Y':
            bioshed_init_aws()
            api_key_file = generate_api_key( dict(cloud=cloud_provider, configfile=config_file))
            provider_file = bioshed_setup_aws( dict(initpath=init_path, configfile=config_file, providerfile=provider_file, mainfile=main_file, keyfile=api_key_file))
            env_file = write_env_file( dict(cloud=cloud_provider, initpath=init_path))
            print('\nBioShed AWS integration setup successful! To setup the core AWS resources, now type:')
            print('\t$ bioshed deploy core')
            print('\n Or try one of the following to test your setup:')
            print('\t$ bioshed run fastqc --help')
            print('\t$ bioshed run fastqc --example')
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
    if int(subprocess.call('aws --help', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)) > 3:
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
    keyfile: API key file
    ---
    """
    # setup terraform provider (AWS): https://learn.hashicorp.com/tutorials/terraform/aws-build
    cwd = os.getcwd()
    INIT_PATH = args['initpath']
    if not os.path.exists(INIT_PATH):
        os.mkdir(INIT_PATH)
    apikeyfile = args['keyfile'] if 'keyfile' in args else ''
    PROVIDER_FILE = args['providerfile'] # os.path.join(INIT_PATH, 'hs_providers.tf')
    MAIN_FILE = args['mainfile'] # os.path.join(INIT_PATH, 'main.tf')
    AWS_CONFIG_FILE = args['configfile']
    KEYS_FILE = os.path.join(INIT_PATH, 'hsconfig.tf')
    AWS_REGION = input('Which region do you want to setup your bioshed infrastructure?\n1: us-west-1 (california)\n2: us-west-2 (oregon) - COMMONLY USED\n3: us-east-1 (virginia) - COMMONLY USED\n4: us-east-2 (ohio)\n5: ap-south-1 (india) - COMMONLY USED\n6: ap-northeast-1 (tokyo)\n7: ap-northeast-2 (seoul)\n8: ap-southeast-1 (singapore)\n9: ca-central-1 (canada)\n10: eu-west-1 (ireland) - COMMONLY USED\n11: eu-west-2 (london)\n12: eu-west-3 (paris)\n13: eu-central-1 (germany)\n\nType a number or a region name: ')
    if AWS_REGION not in VALID_REGIONS and AWS_REGION not in VALID_REGION_NUMBERS:
        AWS_REGION = input('Please type a valid number or AWS region (default: us-west-2): ') or "us-west-2"
    if AWS_REGION in VALID_REGION_NUMBERS:
        AWS_REGION = VALID_REGION_NUMBERS[AWS_REGION]
    AWS_CONSTANTS_JSON = {}
    AWS_CONSTANTS_JSON["ecr_registry"] = ECR_PUBLIC_REGISTRY
    AWS_CONSTANTS_JSON["aws_region"] = AWS_REGION

    if apikeyfile == '':
        PKEY_INPUT = input('Provide a valid public key for accessing AWS resources (in a separate window, type "bioshed keygen aws" or type "ssh-keygen" and paste the public key here). Press ENTER to skip if not using AWS resources: ')
    else:
        PKEY_INPUT = get_public_key( dict(configfile=AWS_CONFIG_FILE))

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
    AWS_CONSTANTS_JSON['setup'] = 'True'
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

def write_env_file( args ):
    """ Writes environment file for use with cloud provider containers.

    cloud: cloud_provider
    initpath: path of config and init files for bioshed
    group: key group if multiple credentials are in credentials file. Default: 'default'
    ---
    envfile: path and name of env file
    """
    cloud = args['cloud'] if 'cloud' in args else 'aws'
    initpath = args['initpath'] if 'initpath' in args else ''
    HOME_PATH = os.path.expanduser('~')
    group = args['group'] if 'group' in args else 'default'
    envfile = os.path.join(initpath,'.env_{}'.format(cloud))
    credfile = ''
    access_key = ''
    secret_key = ''
    current_group = ''
    if initpath != '' and os.path.exists(initpath):
        if cloud in ['aws','amazon']:
            credfile = os.path.join(HOME_PATH,'.aws/credentials')
            if os.path.exists(credfile):
                with open(credfile,'r') as f:
                    r = 'start'
                    while r != '':
                        r = f.readline()
                        if 'aws_access_key_id' in r and current_group == group:
                            access_key = str(r.strip().split('=')[-1]).strip()
                        elif 'aws_secret_access_key' in r and current_group == group:
                            secret_key = str(r.strip().split('=')[-1]).strip()
                        elif '[' in r and ']' in r:
                            if group in r:
                                current_group = group
                            else:
                                current_group = ''
            with open(envfile,'w') as fout:
                fout.write('AWS_ACCESS_KEY_ID={}\n'.format(access_key))
                fout.write('AWS_SECRET_ACCESS_KEY={}\n'.format(secret_key))
    return envfile

def get_env_file( args ):
    """ Gets environment file for cloud provider.

    cloud: cloud provider
    initpath: init path with all config and env files
    ---
    envfile: env file for that cloud provider
    """
    cloud = args['cloud'] if 'cloud' in args else 'aws'
    initpath = args['initpath'] if 'initpath' in args else ''
    if cloud=='aws' and initpath != '':
        return os.path.join(initpath,'.env_{}'.format(cloud))
    else:
        return ''

def cloud_setup( args ):
    """ Checks if cloud provider already setup in Bioshed. (bioshed setup [cloud])
    Assumes that config file has a key 'setup = True' or 'setup' = 'Yes' if setup properly.

    cloud: which cloud provider
    configfile: config file for cloud provider
    ---
    boolean: True/False is cloud setup already?

    """
    isSetup = False
    cloud = args['cloud'] if 'cloud'in args else 'aws'
    configfile = args['configfile'] if 'configfile' in args else ''
    if os.path.exists(configfile):
        config_json = quick_utils.loadJSON(configfile)
        is_cloud_setup = config_json['setup'] if 'setup' in config_json else 'False'
        if is_cloud_setup.upper()[0] in ['T','Y']:
            isSetup = True
    return isSetup

def cloud_configured( args ):
    """ Checks if a cloud provider is configured properly

    cloud: which cloud provider to check. If empty, then check all.
    ---
    boolean: True/False if cloud is configured or not
    """
    cloud = args['cloud'] if 'cloud' in args else 'all'
    pnum = 127
    if cloud in ['aws','amazon','all']:
        pnum = min(int(subprocess.call('aws s3 ls', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)), pnum)
    if cloud in ['gcp','all']:
        pnum = min(int(subprocess.call('gcp --help', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)), pnum)

    if pnum > 3:
        return False
    else:
        return True

def cloud_core_setup( args ):
    """ Checks if cloud core is setup (i.e., bioshed deploy core) has been run).

    configfile: config file for core setup.
    ---
    boolean: True/False if cloud is configured or not
    """
    isCoreSetup = False
    configfile = args['configfile'] if 'configfile' in args else ''
    if configfile!='' and os.path.exists(configfile):
        config_json = quick_utils.loadJSON(configfile)
        is_core_setup = config_json['core_setup'] if 'core_setup' in config_json else 'N'
    if is_core_setup.upper()[0] in ['Y','T']:
        isCoreSetup = True
    return isCoreSetup

def generate_api_key( args ):
    """ Generates an API key for a cloud provider.

    cloud: which cloud provider to generate key for.
    configfile: cloud provider config file
    ---
    keyfile: name of generated public key file

    [NOTE] https://stackoverflow.com/questions/43235179/how-to-execute-ssh-keygen-without-prompt

    """
    cloud = args['cloud'] if 'cloud' in args else 'aws'
    configfile = args['configfile'] if 'configfile' in args else ''
    CONFIG_JSON = {}
    unique_key_id = str(uuid.uuid4())[0:4]
    keyfile = os.path.join(INIT_PATH, 'bioshed_{}_{}'.format(cloud, unique_key_id))
    while os.path.exists(keyfile):
        # in the rare event that key with unique id already exists, generate a new one
        unique_key_id = str(uuid.uuid4())[0:4]
        keyfile = os.path.join(INIT_PATH, 'bioshed_{}_{}'.format(cloud, unique_key_id))
    if configfile != '':
        # generate a new public/private key pair for cloud API.
        rcode = subprocess.call("ssh-keygen -t rsa -N '' -f {}".format(keyfile), shell=True)
        CONFIG_JSON['apikeyfile'] = keyfile
        if int(rcode) == 0:
            print('Public/private key generated at {}'.format(keyfile))
        # reference key file name within config file
        quick_utils.add_to_json( configfile, CONFIG_JSON)
    else:
        print('ERROR: No key generated. Must specify a cloud config file.')
    return keyfile

def get_public_key( args ):
    """ Gets public key for a given key file specified within config file.

    configfile: config file where key file name is stored
    ---
    pubkey: public key
    """
    configfile = args['configfile']
    keyfile = ''
    pubkey = ''

    if os.path.exists(configfile):
        configjson = quick_utils.loadJSON(configfile)
        keyfile = configjson['apikeyfile']
    if keyfile != '' and os.path.exists(keyfile+'.pub'):
        with open(keyfile+'.pub','r') as f:
            # takes last line as key
            for r in f:
                pubkey = r.strip()
    return pubkey

def bioshed_run_help():
    """ Help menu for bioshed run.
    """
    print("""

    ------------------------------------------------------------
    BioShed RUN
    ------------------------------------------------------------
    Welcome to BioShed Run! With this tool, you can:
        - Run bioinformatics applications as you would normally, but without the hassle of installation or setup.
        - Perform bioinformatics on your own computer or in the cloud.
        - Seamlessly work with data files on local or remote cloud file systems.

    Usage:
        bioshed run <optional:CONFIG-ARGS> <APP> <PROGRAM-ARGS> out::OUTPUT_DIR(optional)

    <optional CONFIG-ARGS>
        --local                 Explicitly run on local system. Requires docker installed and running
        --aws-env-file <.ENV>   AWS environment file with the following format:
                                  AWS_ACCESS_KEY_ID=[ID]
                                  AWS_SECRET_ACCESS_KEY=[KEY]
                                  AWS_DEFAULT_REGION=[region]
        --inputdir <DIR>        Full path of local input directory. Requires --local. By default, the current directory is used.


    <APP>
        Type "bioshed run --list" to see a list of available applications. Examples are:
            fastqc              FastQC Quality Control for sequencing data
            STAR                RNA-STAR aligner
            bwa                 Burrows-Wheeler aligner
            gatk                GATK sequencing workflow toolkit

        You can also run BioContainers on BioShed. For help with this, just type:
            $ bioshed run biocontainers --help

    <PROGRAM-ARGS>
        Run any bioinformatics application as you would normally. 
        One special case is: 
            /input/<FILE>       When running locally, prefix any local files with /input/ - ex: /input/my.fastq


    out::OUTPUT_DIR (optional)
        out::<OUTPUT_DIR>       Optional output directory for all data + log files. Specify full path (local or remote).
                                Without this option, files are output back to the input path.
        out::local              Special case - use the current local directory as the output directory.


    The following files are output:
        bioshed.run.out         All text printed to the console (STDOUT)
        program.cat.<TIME>.log  Log file of program output
        run.<TIME>.log          Run log JSON
        out::<OUTPUT_FOLDER>    Output folder for all log and data files. You can explicitly specify local by "out::local"
                                If no output folder is specified, then the input folder is used as the output folder.                                

    ------------------------------------------------------------
    EXAMPLES
    ------------------------------------------------------------
        Using cloud storage:
            $ bioshed run fastqc s3://folder1/seq.fastq.gz
            $ bioshed run bwa mem s3://genomes/bwa_index s3://folder1/seq.fastq.gz out://s3://alignments/
            $ bioshed run STAR --genomeDir s3://genomes/hg38_STAR_index/ --readFilesIn s3://fastqs/my.fastq.gz out::s3://alignments/

        Using local storage:
            $ bioshed run zcat /input/my.fastq.gz out::local
            $ bioshed run fastqc file.fastq.gz out::local
            $ bioshed run --local --inputdir /home/ cat /input/README.txt

        Using local and cloud (hybrid) storage:
            $ bioshed run bedtools merge s3://folder1/test.bed out::/data/
            $ bioshed run fastqc s3://bioshed-examples/fastq/rnaseq_mouse_test_tiny1_R1.fastq.gz out::local

    ------------------------------------------------------------
    HELP
    ------------------------------------------------------------
        For help on how to run an application, type one of the following:
            $ bioshed run <APP> --help
            $ bioshed run <APP> --example

        Examples:
            $ bioshed run fastqc --help     Shows help menu for FASTQC - output to local file "bioshed.run.out"
            $ bioshed run fastqc --example  Shows an example of running FASTQC - output to local file "bioshed.run.out"

    """)

def biocontainers_help():
    """ Help menu for bioshed run biocontainers.
    """
    print("""
    BioShed allows you to run BioContainers without knowing details about Docker.

    To run a basic biocontainer, type (for example):
    $ bioshed run biocontainers blast:2.2.31 makeblastdb --help

    The basic format is:
    $ bioshed run biocontainers <IMAGE>:<TAG> <COMMAND>

    You must know the image name and tag of the biocontainer you want to run.
    For more information, refer to the Biocontainers documentation at:
    https://biocontainers.pro/

    """)
