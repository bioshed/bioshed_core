import sys, os, subprocess, platform
from argparse import ArgumentParser

def detect_os():
    """ Detect system OS, if not provided.
    https://stackoverflow.com/questions/394230/how-to-detect-the-os-from-a-bash-script
    https://stackoverflow.com/questions/110362/how-can-i-find-the-current-os-in-python
    Can get env variable: OSTYPE = os.environ['OSTYPE']
    For linux distros: 'hostnamectl' gets full info
    """
    which_os = 'unsupported'
    which_platform = str(platform.platform()).lower()
    which_version = str(platform.version()).lower()
    which_release = str(platform.release()).lower()
    which_system = str(platform.system()).lower()

    if 'linux' in which_system:
        # Linux distro
        if 'debian' in which_version or 'debian' in which_platform or 'debian' in which_release:
            which_os = 'debian'
        elif 'ubuntu' in which_version or 'ubuntu' in which_platform or 'ubuntu' in which_release:
            which_os = 'ubuntu'
        elif 'redhat' in which_version or 'redhat' in which_platform or 'redhat' in which_release:
            which_os = 'redhat'
        elif 'centos' in which_version or 'centos' in which_platform or 'centos' in which_release:
            which_os = 'centos'
        elif 'amzn' in which_version or 'amzn' in which_platform or 'amzn' in which_release:
            which_os = 'amazonlinux'
        else:
            which_os = 'unsupported'
    elif 'darwin' in which_system:
        # mac os x
        which_os = 'macosx'
    elif "windows" in which_system:
        # windows
        which_os = 'windows'
    else:
        which_os = 'unsupported'
    print('Detected system OS: {}'.format(which_os))
    return which_os

def parse_build_args( args ):
    """ Parse arguments to bioshed build.
    """
    _ARGS = {'install': ['requirements file for commands and installing packages - see docs', True, ''],
             'codebase': ['code base required to run program - supported: python, R, ubuntu', False, 'python']}
    def error_msg():
        help_string = "bioshed build [MODULE] "
        for _ARG in _ARGS:
            help_string += "--{} {}".format(_ARG, _ARG.upper())
        help_string += "\n\nEXAMPLE: bioshed build bowtie --install bowtie.requirements.txt --codebase python\n---"
        return help_string

    argparser = ArgumentParser(usage=error_msg())
    file_path_group = argparser.add_argument_group(title='bioshed build arguments')
    for _ARG in _ARGS:
        file_path_group.add_argument('--{}'.format(_ARG), help=_ARGS[_ARG][0], required=_ARGS[_ARG][1], default=_ARGS[_ARG][2])
    # parsed_args = argparser.parse_args()
    parsed_args, unknown_args = argparser.parse_known_args() # ['--install', 'ARG'])
    return parsed_args

def write_resource_block( args ):
    """ Writes a TF-format resource block
    file: file to write / add
    type: resource type
    name: resource name
    block: internal of block, as dict/JSON

    NOTE: functions within a block are a special case and are defined as:
    {"policy": {"jsonencode()": {"Version": "2012-10-17", Statement: [{"Action":...}]}}}}
    to define:
    policy = jsonencode(
      {
        Version = "2012-10-17"
        Statement = [
          {
          Action = ...
          }
        ]
      }
    )
    """
    """
    rtype = args['type']
    rname = args['name']
    rblock = args['block']
    rid = args['type']+'.'+args['name']
    indent = 0

    with open(args['file'],'a') as f:
        f.write("resource {} {} {\n".format(rtype, rname))
        # iterate through resource arguments inside block
        indent += 2
        for rarg in rblock:
            rvalue = rblock[rarg]
            if type(value) == type({}):
                f.write(indent*" "+"{} = {\n".format(str(rarg)))
                indent += 2
                f.write(indent*" "+"{}")
    """
    return
