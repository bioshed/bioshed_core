import os, sys, json
SCRIPT_DIR = str(os.path.dirname(os.path.realpath(__file__)))
HOME_PATH = os.path.expanduser('~')
INIT_PATH = os.path.join(HOME_PATH, '.bioshedinit/')

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

AWS_CONFIG_FILE = os.path.join(INIT_PATH,'aws_config_constants.json')
PROVIDER_FILE = os.path.join(INIT_PATH, 'hs_providers.tf')
MAIN_FILE = os.path.join(INIT_PATH, 'main.tf')
SYSTEM_TYPE = bioshed_core_utils.detect_os()
VALID_COMMANDS = ['init', 'setup', 'build', 'run', 'runlocal', 'deploy', 'search', 'download', 'teardown']

def bioshed_cli_entrypoint():
    bioshed_cli_main( sys.argv )
    return

def bioshed_cli_main( args ):
    """ Main function for parsing command line arguments and running stuff.
    args: list of command-line args

    [TODO] figure out local search
    [TODO] add docker installation to "pip install bioshed"
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
            if args[-1] == '--help' and len(args) > 3 and args[-2] not in ['run', 'runlocal']:
                if cmd == 'run' and '--local' not in args:
                    args = args[0:2] + ['--local'] + args[2:]

            args = args[2:] # don't need to parse "bioshed run/runlocal"
            dockerargs = ''
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
                    args = docker_utils.specify_output_dir( dict(program_args=args[1:], default_dir=current_dir))
                    # if no cloud bucket is specified, then output to local.
                    if 's3://' not in quick_utils.format_type(args, 'space-str') and 'gcp://' not in quick_utils.format_type(args, 'space-str'):
                        dockerargs += '-v {}:/output/:Z '.format(current_dir)
                    # args = args[1:]
                elif args[0]=='--inputdir':
                    if len(args) < 2:
                        print('You need to specify an input directory.')
                    if args[1] == '.':
                        args[1] = '$(pwd)'
                    dockerargs += '-v {}:/input/ '.format(args[1])
                    args = docker_utils.specify_output_dir( dict(program_args=args[2:], default_dir=args[1]))
                elif args[0]=='--help':
                    bioshed_init.bioshed_run_help()
                    return
            module = args[0].strip().lower()

            # special case: CMD --example
            if ogargs.endswith('--example'):
                args = ['cat', '/example.txt']

            # run module
            if cmd == 'run':
                jobinfo = aws_batch_utils.submit_job_awsbatch( dict(name=module, program_args=args))
                print('SUBMITTED JOB INFO: '+str(jobinfo))
            elif cmd == 'runlocal':
                print('TOTAL COMMAND: {} | {}'.format(str(dockerargs), str(args)))
                print('NOTE: If you get an AWS credentials error, you may need to specify an AWS ENV file: --aws-env-file <.ENV>')
                docker_utils.run_container_local( dict(name=module, args=args, dockerargs=dockerargs))

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
                print('\tbioshed search ncbi <SEARCH_TERMS>')
                print('\tbioshed search local <SEARCH_TERMS>')
                return
            if str(args[2]).lower() == 'encode':
                search_terms = str(' '.join(args[3:])).strip()
                print('Searching ENCODE for: {}'.format(search_terms))
                atlas_encode_utils.search_encode( dict(searchterms=search_terms))
            elif str(args[2]).lower() == 'ncbi':
                print('NCBI search coming soon!')
            elif str(args[2]).lower() == 'local':
                print('Local search coming soon!')
            else:
                print('Currently supported searches: encode, nbci, local')
        elif cmd == 'download' and bioshed_init.userExists( dict(quick_utils.loadJSON(AWS_CONFIG_FILE)).get("login", "") ):
            if len(args) < 3:
                print('Specify a system or repository to download files from. Examples:')
                print('\tbioshed download encode')
                print('\tbioshed download ncbi')
                print('\tbioshed download local')
                return
            if str(args[2]).lower() == 'encode':
                atlas_encode_utils.download_encode( dict(downloadstr=str(' '.join(args[3:])).strip()))
            elif str(args[2]).lower() == 'ncbi':
                print('NCBI download coming soon!')
            elif str(args[2]).lower() == 'local':
                print('Local download coming soon!')
            else:
                print('Currently supported downloads: encode, nbci, local')
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
    print('')
    print('\t$ bioshed run')
    print('\t$ bioshed build')
    print('')
    print('\t$ bioshed search encode')
    print('\t$ bioshed search ncbi')
    print('\t$ bioshed search local')
    print('')
    print('\t$ bioshed download encode')
    print('\t$ bioshed download ncbi')
    print('\t$ bioshed download local')
    print('')
    return
