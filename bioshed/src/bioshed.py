import os, sys, json
SCRIPT_DIR = str(os.path.dirname(os.path.realpath(__file__)))
HOME_PATH = os.path.expanduser('~')
INIT_PATH = os.path.join(HOME_PATH, '.bioshedinit/')
BIOCONTAINERS_REGISTRY = 'public.ecr.aws/biocontainers'

sys.path.append(os.path.join(SCRIPT_DIR))
import bioshed_core_utils
import bioshed_init
import bioshed_deploy_core
sys.path.append(os.path.join(SCRIPT_DIR, 'bioshed_utils/'))
import docker_utils
import aws_batch_utils
import quick_utils
sys.path.append(os.path.join(SCRIPT_DIR, 'bioshed_atlas/'))
import atlas_encode_utils
import atlas_tcga_utils

AWS_CONFIG_FILE = os.path.join(INIT_PATH,'aws_config_constants.json')
GCP_CONFIG_FILE = ''
PROVIDER_FILE = os.path.join(INIT_PATH, 'hs_providers.tf')
MAIN_FILE = os.path.join(INIT_PATH, 'main.tf')
SYSTEM_TYPE = bioshed_core_utils.detect_os()
VALID_COMMANDS = ['init', 'setup', 'connect', 'build', 'run', 'runlocal', 'deploy', 'search', 'download', 'teardown', 'keygen']
VALID_PROVIDERS = ['aws', 'amazon', 'gcp', 'google']

def bioshed_cli_entrypoint():
    bioshed_cli_main( sys.argv )
    return

def bioshed_cli_main( args ):
    """ Main function for parsing command line arguments and running stuff.
    args: list of command-line args

    [TODO] figure out local search
    [DONE] add docker installation to "pip install bioshed"
    """
    ogargs = quick_utils.format_type(args, 'space-str')       # original arguments

    if SYSTEM_TYPE == 'unsupported' or SYSTEM_TYPE == 'windows': # until I can support windows
        print('Unsupported system OS. Linux (Ubuntu, Debian, RedHat, AmazonLinux) or Mac OS X currently supported.\n')
    elif len(args) > 1:
        cmd = args[1].strip()
        if cmd in ['run', 'runlocal'] and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            parseRunCommand( cmd, args )

        elif cmd == 'build' and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            if len(args) < 3:
                print('You must specify a module to build: bioshed build <MODULE> <ARGS>')
                print('For help: "bioshed build --help"')
                return
            module = args[2].strip()
            build_args = getCommandOptions(args[3:])
            # parsed_args = bioshed_core_utils.parse_build_args( args[3:] )
            if 'help' in build_args or 'install' not in build_args:
                print_help_menu('build')
            elif 'install' in build_args:
                print('Building container for {}.'.format(str(module)))
                if 'codebase' not in build_args:
                    build_args['codebase'] = 'python'
                docker_utils.build_container( dict(name=module, requirements=build_args['install'], codebase=build_args['codebase'] ))

        elif cmd == 'connect' and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            if len(args) > 2:
                cloud_provider = args[2].lower()
                cmd_options = getCommandOptions( args[3:] )
                if 'help' in cmd_options or 'h' in cmd_options:
                    print_help_menu('connect')
                    return
                if cloud_provider in ['aws', 'amazon']:
                    bioshed_connect_args = dict( cloud=cloud_provider, initpath=INIT_PATH, configfile=AWS_CONFIG_FILE, providerfile=PROVIDER_FILE, mainfile=MAIN_FILE)
                    if 'keyfile' in cmd_options:
                        bioshed_connect_args['apikeyfile'] = cmd_options['keyfile']
                    bioshed_init.bioshed_connect(bioshed_connect_args)
                else:
                    print('Provider {} currently not supported.'.format(cloud_provider))
            else:
                print('Must specify a cloud provider - e.g., bioshed connect aws')

        elif cmd == 'init':
            optional_args = getCommandOptions(args[2:])
            if 'help' in optional_args:
                print_help_menu('init')
                return
            initialize_bioshed()

        elif cmd == 'deploy' and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            if len(args) < 4 or '--help' in args:
                print_help_menu('deploy')
                return
            # resource to deploy - e.g., core
            deploy_resource = args[2]
            provider = args[3]
            deploy_option = quick_utils.format_type(args[4:], 'space-str') if len(args) > 4 else ''
            bioshed_deploy_core.bioshed_deploy_core(dict(cloud_provider=provider, initpath=INIT_PATH, configfile=AWS_CONFIG_FILE, deployoption=deploy_option))

        elif cmd == 'teardown' and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            if len(args) < 3:
                print("Must specify a resource provider to teardown - e.g., bioshed teardown aws")
                return
            r = input('You are going to tear down your entire bioshed infrastructure. Are you sure? y/n: ') or "N"
            # [TODO] have another credential-based check - ask for AWS credentials or some password
            if r.upper() == "Y":
                provider = args[2]
                teardown_options = quick_utils.format_type(args[3:], 'space-str') if len(args) > 3 else ''
                bioshed_init.bioshed_teardown( dict(initpath=INIT_PATH, cloud=provider, options=teardown_options))

        elif cmd == 'search' and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            if len(args) < 3:
                print_help_menu('search')
                return
            optional_args = getCommandOptions(args[3:])
            if 'help' in optional_args:
                print_help_menu('search')
                return
            elif str(args[2]).lower() == 'encode':
                search_terms = str(' '.join(args[3:])).strip()
                print('Searching ENCODE for: {}'.format(search_terms))
                atlas_encode_utils.search_encode( dict(searchterms=search_terms))
            elif str(args[2]).lower() in ['tcga', 'gdc']:
                search_terms = str(' '.join(args[3:])).strip()
                print('Searching Genomic Data Commons for: {}'.format(search_terms))
                atlas_tcga_utils.search_gdc( dict(searchterms=search_terms))
            elif str(args[2]).lower() == 'ncbi':
                print('NCBI search coming soon!')
            elif str(args[2]).lower() == 'local':
                print('Local search coming soon!')
            else:
                print('Currently supported searches: encode, tcga, gdc. Coming soon: nbci, local')
                
        elif cmd == 'download' and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            if len(args) < 3:
                print_help_menu('download')
                return
            optional_args = getCommandOptions(args[3:])
            if 'help' in optional_args:
                print_help_menu('search')
                return
            elif str(args[2]).lower() == 'encode':
                atlas_encode_utils.download_encode( dict(downloadstr=str(' '.join(args[3:])).strip()))
            elif str(args[2]).lower() in ['tcga', 'gdc']:
                atlas_tcga_utils.download_gdc( dict(downloadstr=str(' '.join(args[3:])).strip()))
            elif str(args[2]).lower() == 'ncbi':
                print('NCBI download coming soon!')
            elif str(args[2]).lower() == 'local':
                print('Local download coming soon!')
            else:
                print('Currently supported downloads: encode, nbci, local')

        elif cmd == 'keygen' and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            if len(args) < 3 or (len(args) >=3 and str(args[2]).lower() not in VALID_PROVIDERS):
                print('Specify a valid cloud provider to generate an API key for.')
                print('\tbioshed keygen aws')
                print('\tbioshed keygen gcp')
                return
            if str(args[2]).lower() in ['aws', 'amazon']:
                key_file = bioshed_init.generate_api_key( dict(cloud='aws', configfile=AWS_CONFIG_FILE))
                print_key = bioshed_init.get_public_key( dict(configfile=AWS_CONFIG_FILE))
                print(print_key)
            elif str(args[2]).lower() in ['gcp', 'google']:
                key_file = bioshed_init.generate_api_key( dict(cloud='gcp', configfile=GCP_CONFIG_FILE))
                print_key = bioshed_init.get_public_key( dict(configfile=AWS_CONFIG_FILE))
                print(print_key)

        elif cmd in VALID_COMMANDS and not bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            print('Not logged on. Please type "bioshed init" and login first.')
        else:
            print_help_menu()
    else:
        print_help_menu()
    return


def initialize_bioshed():
    """ $ bioshed init
        Initialize Bioshed by creating a unique bioshed init directory and creating necessary config files and API keys.
    """
    ## Bioshed creates an init directory (.bioshedinit) under a user's HOME directory to store config files, TF files, and API keys.
    if not os.path.exists(INIT_PATH):
        os.mkdir(INIT_PATH)
    ## Bioshed uses a JSON file for configuring AWS access. This JSON file lives in the Bioshed init directory.
    if not os.path.exists(AWS_CONFIG_FILE):
        with open(AWS_CONFIG_FILE,'w') as fout:
            fout.write('{}')
    ## A user must login before initializing Bioshed.
    login_success = bioshed_init.bioshed_login()
    if login_success["login"]:
        quick_utils.add_to_json(AWS_CONFIG_FILE, {"login": login_success["user"]})
        which_os = bioshed_init.bioshed_init(dict(system=SYSTEM_TYPE, initpath=INIT_PATH))
        print("""
        BioShed initial install complete. Follow-up options are:

        1) Type "bioshed connect aws" and then "bioshed deploy core" to setup AWS infrastructure for Bioshed.
        2) Type "bioshed build <module> <args>" to build a new bioinformatics application module.
        3) Type "bioshed search encode/ncbi/local/etc..." to search a system or repository for datasets.
        4) Type "bioshed run --local <module> <args>" to run a bioinformatics application locally (make sure Docker is running on your system)

        For each of these commands, you can get help:
        $ bioshed <command> --help

        """)
    return


def parseRunCommand( cmd, args ):
    """
    Parse "bioshed run <PROGRAM> ..." from the command line

    cmd: command (comes after "bioshed")
    args: everything typed after "bioshed" (list)
    ---
    status: status code
        -1: error in command or program start
        0: program started without error
        1: help menu or error in command that triggers a help message

    [NOTE] bioshed now has basic support for running biocontainers - "bioshed run biocontainers <CMD>"
    [TODO] write simple test cases for different run commands
    """
    ogargs = quick_utils.format_type(args, 'space-str')       # original arguments

    if len(args) < 3:
        print('You must specify a module with at least one argument - ex: bioshed run fastqc -h')
        print('Type: "bioshed run --help" for full documentation.')
        return 1

    # special case: CMD --example -> always run locally
    if args[-1] == '--example':
        if cmd == 'run' and '--local' not in args:
            args = args[0:2] + ['--local'] + args[2:-1]

    # special case: CMD --help -> always run locally
    if args[-1] == '--help' and len(args) > 3 and args[-2] not in ['run', 'runlocal'] and 'biocontainers' not in ogargs:
        if cmd == 'run' and '--local' not in args:
            args = args[0:2] + ['--local'] + args[2:]

    # special case: bioshed run --list => list possible applications
    if args[-1] == '--list' and len(args) == 3 and 'biocontainers' not in ogargs:
        public_containers = docker_utils.list_containers()
        print('Use "bioshed run" to run one of the applications below:\n')
        for public_container in sorted(public_containers):
            if public_container not in ['test']:
                print('\t{}'.format(public_container))
        print('')
        print('Type: "bioshed run --help" for full documentation.\n')
        return 1

    # special case: if no cloud provider is fully setup, then run locally
    if not (bioshed_init.cloud_configured({}) and bioshed_init.cloud_core_setup( dict(configfile=AWS_CONFIG_FILE))):
        args = args[0:2] + ['--local'] + args[2:]

    args = args[2:] # don't need to parse "bioshed run/runlocal" -> parse everything after from the command line
    dockerargs = ''
    registry = ''
    ctag = ''
    need_user = ''

    # optional argument is specified (--OPTIONAL_ARG)
    while args[0].startswith('--') or args[0]=='-u':
        if args[0]=='--aws-env-file':
            if len(args) < 2:
                print('Either did not specify env file or module name - ex: bioshed runlocal --aws-env-file .env fastqc -h')
            dockerargs += '--env-file {} '.format(args[1])
            args = args[2:]
        elif args[0]=='--local':
            cmd = 'runlocal'
            # when running locally, files in current directory get passed into /input/ dir of container
            current_dir = str(os.getcwd()).replace(' ','\ ')
            #if '--inputdir' not in ogargs:
            #    dockerargs += '-v {}:/input/ '.format(current_dir)
            if 'biocontainers' not in ogargs:
                args = docker_utils.specify_output_dir( dict(program_args=args[1:], default_dir=current_dir))
                # if no cloud bucket is specified, then output to local.
                if 's3://' not in quick_utils.format_type(args, 'space-str') and 'gcp://' not in quick_utils.format_type(args, 'space-str'):
                    dockerargs += '-v {}:/output/:Z '.format(current_dir)
                if '--aws-env-file' not in ogargs and 's3://' in quick_utils.format_type(args, 'space-str'):
                    # if S3 bucket is specified and aws-env-file is not specified, then use default aws config file
                    args = ['--aws-env-file', bioshed_init.get_env_file(dict(cloud='aws', initpath=INIT_PATH))] + args
            else:
                args = args[1:]
        elif args[0]=='--inputdir':
            if len(args) < 2:
                print('You need to specify an input directory.')
            if args[1] == '.':
                args[1] = '$(pwd)'
            if 'biocontainers' not in ogargs:
                dockerargs += '-v {}:/input/ '.format(args[1])
                args = docker_utils.specify_output_dir( dict(program_args=args[2:], default_dir=args[1]))
                # add local flag if not explicitly specified
                if '--local' not in ogargs:
                    args = ['--local'] + args
            else:
                # special case: biocontainers
                dockerargs += '-v {}:/data/ '.format(args[1])
        elif args[0]=='--help':
            bioshed_init.bioshed_run_help()
            return
        elif args[0] == '-u':
            # special case: -u <USER> for sudo argument
            need_user = args[1]
            args = args[2:]
    module = args[0].strip().lower()

    # special case: biocontainers
    if module.lower() == 'biocontainers':
        if len(args) < 2 or (len(args) == 3 and '--help' in ogargs):
            bioshed_init.biocontainers_help()
            return
        module = str(args[1].split(':')[0]).strip().lower()
        registry = BIOCONTAINERS_REGISTRY
        ctag = str(args[1].split(':')[1]) if len(args[1].split(':')) > 1 else 'latest'
        args = args[2:]
        cmd = 'runlocal'  # biocontainers can only be run locally
        if '-v' not in dockerargs and ':/data' not in dockerargs and '--inputdir' not in ogargs:
            dockerargs += '-v $(pwd):/data/ '
    # special case: CMD --example
    elif ogargs.endswith('--example'):
        args = ['cat', '/example.txt']
    # special case: e.g., fastqc - need to explicitly specify output directory
    elif module.lower() in ['fastqc']:
        args = [args[0]] + ['-o', '/output/'] + args[1:]
    # run module
    if cmd == 'run':
        # run module as a batch job in AWS
        # [TODO] expand support for running batch jobs in other cloud providers
        jobinfo = aws_batch_utils.submit_job_awsbatch( dict(name=module, program_args=args))
        print('SUBMITTED JOB INFO: '+str(jobinfo))
    elif cmd == 'runlocal':
        # run module as a local container
        print('TOTAL COMMAND: {} | {}'.format(str(dockerargs), str(args)))
        print('NOTE: If you get an AWS credentials error, you may need to specify an AWS ENV file: --aws-env-file <.ENV>')
        docker_utils.run_container_local( dict(name=module, args=args, dockerargs=dockerargs, registry=registry, tag=ctag, need_user=need_user))
    return 0


def getCommandOptions( _args ):
    """ Given a list of optional arguments, parses into a dictionary.

    Example: --keyfile mykey.pub --dryrun
    Output: {'keyfile': 'mykey.pub', 'dryrun': ''}

    [TODO] type-checking and testing
    """
    out_args = {}
    while len(_args) > 0:
        if len(_args) > 1 and _args[0].startswith('--') and not _args[1].startswith('--'):
            out_args[_args[0][2:]] = _args[1]
            _args = _args[2:]
        elif _args[0].startswith('--') and (len(_args)==1 or _args[1].startswith('--')):
            out_args[_args[0][2:]] = ''
            _args = _args[1:]
        else:
            _args = _args[1:]
    return out_args



def print_help_menu( which_menu = 'base' ):
    """ Various help menus depending on the command run
    """
    if which_menu == 'base':
        print("""
        Welcome to Bioshed, an open-source bioinformatics infrastructure toolkit.

        Specify a valid subcommand. Valid subcommands are:

        $ bioshed init
        $ bioshed connect aws
        $ bioshed deploy core aws
        $ bioshed teardown aws
        $ bioshed keygen aws
        
        $ bioshed run
        $ bioshed build
        
        $ bioshed search encode
        $ bioshed search tcga
        $ bioshed search gdc
        
        $ bioshed download encode
        $ bioshed download tcga
        $ bioshed download gdc
        
        You can add --help option to each subcommand for specific help.
        
        """)
    elif which_menu == 'init':
        print("""
        To initialize Bioshed on this device, just type "bioshed init" and log into your account as instructed.
        The necessary packages and libraries for running Bioshed will be installed on your device.

        """)
    elif which_menu == 'deploy':
        print("""
        Must specify a resource to deploy - e.g., bioshed deploy aws core
        """)
    elif which_menu == 'connect':
        print("""
        This sets up this device to connect to your AWS environment. Examples:

            $ bioshed connect aws
            $ bioshed connect aws --keyfile ~/.ssh/mykey.pub
        """)
    elif which_menu == 'build':
        print("""
        Build a container image given a requirements.txt file and a specified codebase image (default: python)

        EXAMPLE: bioshed build bowtie --install bowtie.requirements.txt --codebase python
        """)
    elif which_menu in ['search', 'download']:
        print("""
        Search and download datasets from public sequencing repositories.

        Specify a system or repository to search and type your search terms. Examples:
            bioshed search encode <SEARCH_TERMS>
            bioshed search gdc <SEARCH_TERMS>
            bioshed search tcga <SEARCH_TERMS>
            bioshed search ncbi <SEARCH_TERMS>
        """)
    return
