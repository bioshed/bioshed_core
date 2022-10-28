import os, sys, subprocess
SCRIPT_DIR = str(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.join(SCRIPT_DIR, 'bioshed_utils/'))
import quick_utils
import aws_s3_utils

def bioshed_deploy_core( args ):
    """
    cloud_provider: aws, gcp,...
    initpath: path to init files
    configfile: AWS config file
    deployoption: option for deployment - test, dryrun,...
    ---
    """
    cloud = args['cloud_provider']
    initpath = args['initpath']
    configfile = args['configfile']
    deployoption = args['deployoption'] if 'deployoption' in args else ''
    if cloud.lower() in ['aws','amazon']:
        if deployoption.lower() == 'test':
            bioshed_deploy_core_aws_test( dict(initpath=initpath))
        else:
            bioshed_deploy_core_aws_public( dict(initpath=initpath, deployoption=deployoption, configfile=configfile))
    return

def bioshed_deploy_core_aws_test( args ):
    """ Deploys test core infrastructure.

    initpath: path to init files
    deployoption: option for deployment - ex: dryrun
    ---
    """
    cwd = os.getcwd()
    INIT_PATH = args['initpath'] # os.path.join(os.getcwd(), 'hsinit')
    deployoption = args['deployoption'] if 'deployoption' in args else ''
    with open(os.path.join(INIT_PATH,'main.tf'),'w') as f:
        f.write(
        """
        resource "aws_instance" "app_server" {
          ami = "ami-830c94e3"
          instance_type = "t2.micro"
          associate_public_ip_address = false
          tags = {
            Name = "ExampleAppServerInstance"
          }
        }

        """
        )
        f.write(
        """
        resource "aws_eip" "lb" {
          instance = aws_instance.app_server.id
          vpc      = false
        }
        """
        )
        f.write(
        """
        resource "aws_iam_role" "test_role" {
        name = "test_role"
        assume_role_policy = jsonencode({
          Version = "2012-10-17"
          Statement = [
            {
              Action = "sts:AssumeRole"
              Effect = "Allow"
              Sid    = ""
              Principal = {
                Service = "ec2.amazonaws.com"
              }
            },
          ]
        })
        tags = {
          tag-key = "tag-value"
        }
      }
      """
      )
    os.chdir(INIT_PATH)
    subprocess.call('terraform plan -out hs_deploy_core.plan', shell=True)
    subprocess.call('terraform apply hs_deploy_core.plan', shell=True)
    os.chdir(cwd)
    return

def bioshed_deploy_core_aws_public( args ):
    """ Deploys core infrastructure of public resources for running bioshed modules.

    initpath: path to init files
    configfile = args['configfile']
    region: region to deploy files
    deployoption = args['deployoption'] if 'deployoption' in args else ''
    ---

    TODO: add to existing TF files instead of overwriting.
    TODO: check if VPC CIDR block is already taken before assigning
    TODO: use generated key and public AMI - set this up
    """
    cwd = os.getcwd()
    INIT_PATH = args['initpath'] # os.path.join(os.getcwd(), 'hsinit')
    configfile = args['configfile']
    deployoption = args['deployoption'] if 'deployoption' in args else ''
    region = args['region'] if 'region' in args else 'us-west-2'
    aws_id = aws_s3_utils.get_aws_id()
    with open(os.path.join(INIT_PATH,'variables.tf'),'w') as f:
        f.write(
        """
        variable "name_prefix" {
          type        = string
          description = "Naming prefix for resources"
          default     = "bioshed-managed"
        }

        variable "aws_region" {
          type        = string
          description = "Region for AWS Resources"
        """
        )
        f.write('  default = "{}"\n'.format(region))
        f.write('}\n\n')
        f.write(
        """
        variable "aws_azs" {
          type        = list(string)
          description = "AWS Available Zones to use"
        """
        )
        f.write('  default     = ["{}a", "{}b", "{}c", "{}d"]\n'.format(region, region, region, region))
        f.write('}\n\n')
        f.write(
        """
        # assume that CIDR block is not taken
        variable "vpc_cidr_block" {
          type        = string
          description = "Base CIDR Block for VPC"
          default     = "10.35.0.0/16"
        }

        variable "vpc_cidr_range_public_subnets" {
          type        = list(string)
          description = "CIDR ranges for public subnets"
          default     = ["10.35.0.0/17"]
        }

        variable "enable_dns_hostnames" {
          type        = bool
          description = "Enable DNS hostnames in VPC"
          default     = true
        }

        variable "vpc_subnet_count" {
          type        = number
          description = "Number of private or public subnets to create in VPC"
          default     = 1
        }

        """
        )
        f.write(
        """
        variable "public_ecs_batch_service_role_policy_arns" {
          type        = list(string)
          description = "IAM Role Policies for Batch to be able to start instances"
          default     = ["arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess", "arn:aws:iam::aws:policy/AmazonElasticContainerRegistryPublicReadOnly", "arn:aws:iam::aws:policy/AmazonS3FullAccess", "arn:aws:iam::aws:policy/CloudWatchFullAccess", "arn:aws:iam::aws:policy/AmazonECS_FullAccess", "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceRole", "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"]
        }

        variable "bioshed_ecs_instance_role_policy_arn" {
          type        = list(string)
          description = "IAM Role Policiy to attach to instances run within Batch"
          default     = ["arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role", "arn:aws:iam::aws:policy/AmazonS3FullAccess", "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess", "arn:aws:iam::aws:policy/AmazonElasticContainerRegistryPublicReadOnly"]
        }

        # use public ID later
        variable "batch_ami_id_tiny" {
          type        = string
          description = "AMI for Batch EC2 instances with 100GB storage"
          default     = "ami-08576a4860f85fa6d"
        }

        # use aws_key_pair.deployer later
        variable "batch_ec2_key" {
          type        = string
          description = "EC2 key pair for Batch instances"
          default     = "npi_aws_batch"
        }

        """
        )
    with open(os.path.join(INIT_PATH,'main.tf'),'w') as f:
        f.write(
        """
        # Setup VPC and subnets and route tables
        resource "aws_vpc" "vpc" {
          cidr_block           = var.vpc_cidr_block
          enable_dns_hostnames = var.enable_dns_hostnames
          tags = { Name = "${var.name_prefix}-vpc" }
        }

        resource "aws_internet_gateway" "igw" {
          vpc_id = aws_vpc.vpc.id
          tags = { Name = "${var.name_prefix}-igw" }
        }

        resource "aws_subnet" "public_subnets" {
          count                   = var.vpc_subnet_count
          cidr_block              = var.vpc_cidr_range_public_subnets[count.index]
          vpc_id                  = aws_vpc.vpc.id
          map_public_ip_on_launch = true
          availability_zone       = var.aws_azs[count.index]
          tags = { Name = "${var.name_prefix}-public-subnet-${count.index}" }
        }

        # public route table - mapping of VPC CIDR block to local is added automatically
        resource "aws_route_table" "public_route_table" {
          vpc_id = aws_vpc.vpc.id
          route {
            cidr_block = "0.0.0.0/0"
            gateway_id = aws_internet_gateway.igw.id
          }
          tags = { Name = "${var.name_prefix}-public-route-table" }
        }

        # set main route table
        resource "aws_main_route_table_association" "rta-main-public" {
          vpc_id         = aws_vpc.vpc.id
          route_table_id = aws_route_table.public_route_table.id
        }

        # route table associations
        resource "aws_route_table_association" "rta-public-subnets" {
          count          = var.vpc_subnet_count
          subnet_id      = aws_subnet.public_subnets[count.index].id
          route_table_id = aws_route_table.public_route_table.id
        }

        # s3 endpoint inside VPC - routes any S3-bound traffic to this endpoint instead of through NAT->IGW
        resource "aws_vpc_endpoint_route_table_association" "rta-s3-public" {
          route_table_id = aws_route_table.public_route_table.id
          vpc_endpoint_id = aws_vpc_endpoint.s3.id
        }

        resource "aws_vpc_endpoint" "s3" {
          vpc_id = aws_vpc.vpc.id
        """
        )
        f.write('service_name = "com.amazonaws.{}.s3"\n'.format(region))
        f.write('}\n\n')
        f.write(
        """
        # reachable-from-vpc allows full access to a resource if within the VPC.
        resource "aws_security_group" "reachable_from_vpc" {
          name   = "${var.name_prefix}-reachable-from-vpc"
          vpc_id = aws_vpc.vpc.id

          # inbound - full access from inside VPC
          ingress {
            from_port   = 0
            to_port     = 0
            protocol    = "-1"
            cidr_blocks = [var.vpc_cidr_block]
          }

          # outbound - internet access
          egress {
            from_port   = 0
            to_port     = 0
            protocol    = "-1"
            cidr_blocks = ["0.0.0.0/0"]
          }
          tags = { Name = "${var.name_prefix}-reachable-from-vpc" }
        }

        # reachable-with-ssh allows external SSH access for a resource in a public subnet.
        resource "aws_security_group" "reachable_with_ssh" {
          name   = "${var.name_prefix}-reachable-with-ssh"
          vpc_id = aws_vpc.vpc.id

          # inbound - full access from inside VPC
          ingress {
            from_port   = 22
            to_port     = 22
            protocol    = "tcp"
            cidr_blocks = ["0.0.0.0/0"]
          }

          # outbound - internet access
          egress {
            from_port   = 0
            to_port     = 0
            protocol    = "-1"
            cidr_blocks = ["0.0.0.0/0"]
          }

          tags = { Name = "${var.name_prefix}-reachable-with-ssh" }
        }

        """
        )
        f.write(
        """
        # Batch role and policy
        resource "aws_iam_role" "bioshed_aws_batch_service_role" {
          name = "bioshed_aws_batch_service_role"
          assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Effect": "Allow",
      "Principal": {
        "Service": "batch.amazonaws.com"
      }
    }
  ]
}
EOF
        }

        resource "aws_iam_role_policy_attachment" "bioshed_aws_batch_service_role" {
          role       = aws_iam_role.bioshed_aws_batch_service_role.name
          policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
        }

        """
        )
        f.write(
        """
        # gives EC2 instances deployed by Batch permissions to access container regsitry, container agent, and S3.
        resource "aws_iam_role" "bioshed_ecs_instance_role" {
          name = "bioshed_ecs_instance_role"

          assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "sts:AssumeRole",
        "Effect": "Allow",
        "Principal": {
          "Service": ["ec2.amazonaws.com"]
        }
      }
    ]
}
EOF
        }

        resource "aws_iam_role_policy_attachment" "bioshed_ecs_instance_role" {
          role       = aws_iam_role.bioshed_ecs_instance_role.name
          count      = length(var.bioshed_ecs_instance_role_policy_arn)
          policy_arn = var.bioshed_ecs_instance_role_policy_arn[count.index]
        }

        resource "aws_iam_instance_profile" "bioshed_ecs_instance_role" {
          name = "bioshed_ecs_instance_role"
          role = aws_iam_role.bioshed_ecs_instance_role.name
        }

        """
        )
        f.write(
        """
        # Deploys the batch environment within the VPC setup
        resource "aws_batch_compute_environment" "batch_compute_public" {
          compute_environment_name = "${var.name_prefix}_batch_compute_public"

          compute_resources {
            # compute instances within Batch environment will have resource access governed by ECS instance role
            instance_role = aws_iam_instance_profile.bioshed_ecs_instance_role.arn
            instance_type = ["m5.large", "m5.xlarge", "m5.2xlarge", "m5.4xlarge"]

            max_vcpus = 256
            min_vcpus = 0

            security_group_ids = [
              aws_security_group.reachable_from_vpc.id,
              aws_security_group.reachable_with_ssh.id
            ]

            # ec2_key_pair = var.batch_ec2_key
            ec2_key_pair = aws_key_pair.deployer.id

            subnets = [for s in aws_subnet.public_subnets : s.id]

            type = "EC2"

            image_id = var.batch_ami_id_tiny
            # ec2_configuration {
            #  image_id_override = var.batch_ami_id_tiny
            #  image_type = "ECS_AL2"
            # }
          }

          service_role = aws_iam_role.bioshed_aws_batch_service_role.arn
          type         = "MANAGED"
          depends_on   = [aws_iam_role_policy_attachment.bioshed_aws_batch_service_role, aws_iam_instance_profile.bioshed_ecs_instance_role, aws_internet_gateway.igw, aws_security_group.reachable_from_vpc, aws_security_group.reachable_with_ssh]
        }

        resource "aws_batch_job_queue" "batch_job_queue_public" {
          name     = "${var.name_prefix}_batch_job_queue_public"
          state    = "ENABLED"
          priority = 1
          compute_environments = [
            aws_batch_compute_environment.batch_compute_public.arn
          ]
          depends_on  = [aws_batch_compute_environment.batch_compute_public]
        }

        """
        )
        f.write(
        """
        # ECS batch service role and policy - allows Batch access to containers and container agent.
        resource "aws_iam_role" "bioshed_ecs_batch_service_role" {
          name = "bioshed_ecs_batch_service_role"

          assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Effect": "Allow",
      "Principal": {
        "Service": ["ec2.amazonaws.com", "ecs.amazonaws.com", "ecs-tasks.amazonaws.com"]
      }
    }
  ]
}
EOF
        }

        resource "aws_iam_role_policy_attachment" "bioshed_ecs_batch_service_role" {
          role       = aws_iam_role.bioshed_ecs_batch_service_role.name
          count      = length(var.public_ecs_batch_service_role_policy_arns)
          policy_arn = var.public_ecs_batch_service_role_policy_arns[count.index]
        }
        """
        )
    os.chdir(INIT_PATH)
    subprocess.call('terraform plan -out hs_deploy_core.plan', shell=True)
    if 'dryrun' not in str(deployoption).lower():
        subprocess.call('terraform apply hs_deploy_core.plan', shell=True)
    os.chdir(cwd)
    # add roles and other config to aws config file
    quick_utils.add_to_json( configfile, dict(aws_ecr_role='arn:aws:iam::{}:instance-profile/bioshed_ecs_instance_role'.format(aws_id), \
                                              aws_ecs_job_role='arn:aws:iam::{}:role/bioshed_ecs_batch_service_role'.format(aws_id), \
                                              jobqueue='bioshed-managed_batch_job_queue_public', \
                                              working_dir='/home'))

    return
