import os, sys, json
SCRIPT_DIR = str(os.path.dirname(os.path.realpath(__file__)))
HOME_PATH = os.path.expanduser('~')
INIT_PATH = os.path.join(HOME_PATH, '.bioshedinit/')

import bioshed_core_utils
import bioshed_init
import bioshed_deploy_core
sys.path.append(os.path.join(SCRIPT_DIR, 'bioshed_utils/'))
import docker_utils
import aws_batch_utils

AWS_CONFIG_FILE = os.path.join(INIT_PATH,'aws_config_constants.json')
PROVIDER_FILE = os.path.join(INIT_PATH, 'hs_providers.tf')
MAIN_FILE = os.path.join(INIT_PATH, 'main.tf')
SYSTEM_TYPE = bioshed_core_utils.detect_os()

def bioshed_cli_entrypoint():
    bioshed_cli_main( sys.argv )
    return

def bioshed_cli_main( args ):
    """ Main function for parsing command line arguments and running stuff.
    args: list of command-line args
    """
    if SYSTEM_TYPE == 'unsupported' or SYSTEM_TYPE == 'windows': # until I can support windows
        print('Unsupported system OS. Linux (Ubuntu, Debian, RedHat, AmazonLinux) or Mac OS X currently supported.\n')
    elif len(args) > 1:
        cmd = args[1].strip()
        if cmd in ['run', 'runlocal']:
            if len(args) < 3:
                print('You must specify a module with at least one argument - ex: bioshed run fastqc -h')
            # optional argument is specified
            if args[2].startswith('--'):
                if args[2]=='--aws-env-file':
                    if len(args) < 5:
                        print('Either did not specify env file or module name - ex: bioshed runlocal --aws-env-file .env fastqc -h')
                    dockerargs = '--env-file {}'.format(args[3])
                    args = args[4:]
            else:
                dockerargs = ''
                args = args[2:]
            module = args[0].strip()
            # run module
            if cmd == 'run':
                jobinfo = aws_batch_utils.submit_job_awsbatch( dict(name=module, program_args=args))
                print('SUBMITTED JOB INFO: '+str(jobinfo))
            elif cmd == 'runlocal':
                docker_utils.run_container_local( dict(name=module, args=args, dockerargs=dockerargs))

        elif cmd == 'build':
            if len(args) > 2:
                module = args[2].strip()
                parsed_args = bioshed_core_utils.parse_build_args( args[3:] )
                print('MODULE: '+str(module))
                if 'install' in parsed_args:
                    docker_utils.build_container( dict(name=module, requirements=parsed_args.install, codebase=parsed_args.codebase ))
        elif cmd == 'init':
            if len(args) > 2:
                cloud_provider = args[2].lower()
                if cloud_provider in ['aws', 'amazon']:
                    bioshed_init.bioshed_init(dict(system=SYSTEM_TYPE, cloud=cloud_provider, initpath=INIT_PATH, configfile=AWS_CONFIG_FILE, providerfile=PROVIDER_FILE, mainfile=MAIN_FILE))
                else:
                    print('Provider {} currently not supported.'.format(cloud_provider))
            else:
                print('Must specify a cloud provider - e.g., bioshed init aws')
        elif cmd == 'deploy':
            if len(args) < 3:
                print('Must specify a resource to deploy - e.g., bioshed deploy core\n')
                return
            deploy_resource = args[2]
            # for now, assume cloud provider is AWS
            provider = 'aws'
            deploy_option = args[3] if len(args) > 3 else ''
            bioshed_deploy_core.bioshed_deploy_core(dict(cloud_provider=provider, initpath=INIT_PATH, configfile=AWS_CONFIG_FILE, deployoption=deploy_option))
        elif cmd == 'teardown':
            r = input('You are going to tear down your entire bioshed infrastructure. Are you sure? y/n: ') or "N"
            # have another credential-based check - ask for AWS credentials or some password
            if r.upper() == "Y":
                bioshed_init.bioshed_teardown( dict(initpath=INIT_PATH))
    else:
        print('Specify a subcommand. Valid subcommands are:\n\n')
        print('$ bioshed init aws\n')
        print('$ bioshed deploy core\n')
        print('$ bioshed teardown aws\n')
    return
