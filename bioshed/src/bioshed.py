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
VALID_COMMANDS = ['init', 'setup', 'build', 'run', 'runlocal', 'deploy', 'search', 'download', 'teardown', 'keygen']
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
            if len(args) < 3:
                print('You must specify a module with at least one argument - ex: bioshed run fastqc -h')
                print('Type: "bioshed run --help" for full documentation.')
                return

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
                return

            # special case: if no cloud provider is fully setup, then run locally
            if not (bioshed_init.cloud_configured({}) and bioshed_init.cloud_core_setup( dict(configfile=AWS_CONFIG_FILE))):
                args = args[0:2] + ['--local'] + args[2:]

            args = args[2:] # don't need to parse "bioshed run/runlocal"
            dockerargs = ''
            registry = ''
            ctag = ''
            need_user = ''

            # special case: -u <USER> for sudo argument
            if args[0] == '-u':
                need_user = args[1]
                args = args[2:]

            # optional argument is specified
            while args[0].startswith('--'):
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
                    else:
                        # special case: biocontainers
                        dockerargs += '-v {}:/data/ '.format(args[1])
                elif args[0]=='--help':
                    bioshed_init.bioshed_run_help()
                    return
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
                jobinfo = aws_batch_utils.submit_job_awsbatch( dict(name=module, program_args=args))
                print('SUBMITTED JOB INFO: '+str(jobinfo))
            elif cmd == 'runlocal':
                print('TOTAL COMMAND: {} | {}'.format(str(dockerargs), str(args)))
                print('NOTE: If you get an AWS credentials error, you may need to specify an AWS ENV file: --aws-env-file <.ENV>')
                docker_utils.run_container_local( dict(name=module, args=args, dockerargs=dockerargs, registry=registry, tag=ctag, need_user=need_user))

        elif cmd == 'build' and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            if len(args) < 3:
                print('You must specify a module to build: bioshed build <MODULE> <ARGS>')
                return
            module = args[2].strip()
            parsed_args = bioshed_core_utils.parse_build_args( args[3:] )
            print('MODULE: '+str(module))
            if 'install' in parsed_args:
                docker_utils.build_container( dict(name=module, requirements=parsed_args.install, codebase=parsed_args.codebase ))
        elif cmd == 'setup' and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            if len(args) > 2:
                cloud_provider = args[2].lower()
                if cloud_provider in ['aws', 'amazon']:
                    bioshed_init.bioshed_setup(dict( cloud=cloud_provider, initpath=INIT_PATH, configfile=AWS_CONFIG_FILE, providerfile=PROVIDER_FILE, mainfile=MAIN_FILE))
                else:
                    print('Provider {} currently not supported.'.format(cloud_provider))
            else:
                print('Must specify a cloud provider - e.g., bioshed setup aws')
        elif cmd == 'init':
            # first create init directory if doesn't exist
            if not os.path.exists(INIT_PATH):
                os.mkdir(INIT_PATH)
            # create config file if doesn't exist
            if not os.path.exists(AWS_CONFIG_FILE):
                with open(AWS_CONFIG_FILE,'w') as fout:
                    fout.write('{}')
            # ask for login name (email)
            login_success = bioshed_init.bioshed_login()
            if login_success["login"]:
                quick_utils.add_to_json(AWS_CONFIG_FILE, {"login": login_success["user"]})
                which_os = bioshed_init.bioshed_init(dict(system=SYSTEM_TYPE, initpath=INIT_PATH))
                print('BioShed initial install complete. Follow-up options are:')
                print('1) Type "bioshed setup aws" and then "bioshed deploy core" to setup AWS infrastructure for Bioshed.')
                print('2) Type "bioshed build <module> <args>" to build a new bioinformatics application module.')
                print('3) Type "bioshed search encode/ncbi/local/etc..." to search a system or repository for datasets.')
                print('')
        elif cmd == 'deploy' and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            if len(args) < 3:
                print('Must specify a resource to deploy - e.g., bioshed deploy core\n')
                return
            deploy_resource = args[2]
            # for now, assume cloud provider is AWS
            provider = 'aws'
            deploy_option = args[3] if len(args) > 3 else ''
            bioshed_deploy_core.bioshed_deploy_core(dict(cloud_provider=provider, initpath=INIT_PATH, configfile=AWS_CONFIG_FILE, deployoption=deploy_option))
        elif cmd == 'teardown' and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            r = input('You are going to tear down your entire bioshed infrastructure. Are you sure? y/n: ') or "N"
            # have another credential-based check - ask for AWS credentials or some password
            if r.upper() == "Y":
                bioshed_init.bioshed_teardown( dict(initpath=INIT_PATH))
        elif cmd == 'search' and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            if len(args) < 3:
                print('Specify a system or repository to search and type your search terms. Examples:')
                print('\tbioshed search encode <SEARCH_TERMS>')
                print('\tbioshed search gdc <SEARCH_TERMS>')
                print('\tbioshed search tcga <SEARCH_TERMS>')
                print('\tbioshed search ncbi <SEARCH_TERMS>')
                return
            if str(args[2]).lower() == 'encode':
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
                print('Specify a system or repository to download files from. Examples:')
                print('\tbioshed download encode')
                print('\tbioshed download gdc')
                print('\tbioshed download tcga')
                print('\tbioshed download ncbi')
                return
            if str(args[2]).lower() == 'encode':
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

def print_help_menu():
    print('Specify a valid subcommand. Valid subcommands are:\n')
    print('\t$ bioshed init')
    print('\t$ bioshed setup aws')
    print('\t$ bioshed deploy core')
    print('\t$ bioshed teardown aws')
    print('\t$ bioshed keygen aws')
    print('')
    print('\t$ bioshed run')
    print('\t$ bioshed build')
    print('')
    print('\t$ bioshed search encode')
    print('\t$ bioshed search tcga')
    print('\t$ bioshed search gdc')
    print('')
    print('\t$ bioshed download encode')
    print('\t$ bioshed download tcga')
    print('\t$ bioshed download gdc')
    print('')
    return
