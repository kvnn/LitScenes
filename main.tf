terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
    postgresql = {
      source = "cyrilgdn/postgresql"
    }
  }
}


provider "aws" {
  region = "us-west-2"  # Choose your preferred AWS region
}

# VPC and Networking
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "Main VPC"
  }
}

resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
  availability_zone = "us-west-2a"
  map_public_ip_on_launch = true
  tags = {
    Name = "Public Subnet"
  }
}

resource "aws_subnet" "public2" {
  vpc_id     = aws_vpc.main.id 
  cidr_block = "10.0.3.0/24"
  availability_zone = "us-west-2b"

  tags = {
    Name = "Public Subnet 2"
  }
}

resource "aws_subnet" "private" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.2.0/24"
  tags = {
    Name = "Private Subnet"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# EC2 for FastAPI Server

resource "aws_security_group" "fastapi_sg" {
  vpc_id = aws_vpc.main.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Adjust this to your IP for better security
  }
  tags = {
    Name = "FastAPI SG"
  }
}

resource "random_password" "db_password" {
  length           = 16
  special          = false
}

locals {
  code_setup = [
    "echo 'export DEBIAN_FRONTEND=noninteractive' | sudo tee -a /etc/environment",
    "sudo apt-get update >> /tmp/apt-get-update.log 2>&1",
    "sudo apt-get --assume-yes install -y python3-pip libpq-dev >> /tmp/apt-get-install.log 2>&1",
    "sudo pip install psycopg2-binary >> /tmp/pip-install-pscyopg2-binary.log 2>&1",
    "chmod 600 /home/ubuntu/.ssh/litscenes_deploy_key",
    "ssh-add /home/ubuntu/.ssh/litscenes_deploy_key",
    "ssh-keyscan github.com >> /home/ubuntu/.ssh/known_hosts",
    "git clone git@github.com:kvnn/LitScenes.git >> /tmp/git-clone.log 2>&1",
    "sudo pip install -r /home/ubuntu/LitScenes/app/requirements.prod.txt >> /tmp/pip-install.log 2>&1"
  ]

  # 1. copy values from .env.prod to .env.tmp
  # 2. fill in the .env.tmp values with the newly deployed endpoints
  env_setup = <<-EOL
    IP_ADDRESS=%s
    cp .env.prod .env.tmp
    echo "DB_CONNECTION=postgresql+psycopg2://litscenes_user:${random_password.db_password.result}@${aws_db_instance.litscenes.endpoint}/LitScenes" > .env.tmp
    echo "CELERY_BROKER_URL=redis://${aws_elasticache_cluster.redis_cluster.cache_nodes[0].address}:6379/0" >> .env.tmp
    echo "CELERY_RESULT_BACKEND=redis://${aws_elasticache_cluster.redis_cluster.cache_nodes[0].address}:6379/0" >> .env.tmp
    echo "REDIS_URL=redis://${aws_elasticache_cluster.redis_cluster.cache_nodes[0].address}:6379/0" >> .env.tmp
    scp -o StrictHostKeyChecking=no -i ~/.aws/kevins2023.pem .env.tmp ubuntu@$IP_ADDRESS:/home/ubuntu/LitScenes/app/.env

  EOL
}

resource "aws_instance" "fastapi_server" {
  ami = "ami-0efcece6bed30fd98"
  instance_type = "t3a.micro"
  subnet_id     = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.fastapi_sg.id, aws_security_group.redis_sg.id]
  key_name      = "Kevins2023"

  tags = {
    Name = "FastAPI Server"
  }

  # git clone access
  provisioner "file" {
    source      = "/Users/kevin/.aws/litscenes_github_deploy_key"
    destination = "/home/ubuntu/.ssh/litscenes_deploy_key"
  }

  provisioner "remote-exec" {
    inline = local.code_setup
  }

  connection {
    type        = "ssh"
    user        = "ubuntu"
    private_key = file("~/.aws/kevins2023.pem")
    host        = self.public_ip
  }

  provisioner "local-exec" {
    command = format(local.env_setup, aws_instance.fastapi_server.public_ip)
  }

  depends_on = [aws_elasticache_cluster.redis_cluster]
}

# Celery Worker w/ Elasticache Redis backend
resource "aws_elasticache_subnet_group" "redis_subnet_group" {
  name       = "redis-subnet-group"
  subnet_ids = [aws_subnet.public.id, aws_subnet.public2.id]
}

resource "aws_security_group" "redis_sg" {
  vpc_id = aws_vpc.main.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]  # Only allow internal VPC traffic
  }
}

resource "aws_elasticache_cluster" "redis_cluster" {
  cluster_id           = "redis-cluster"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  /* parameter_group_name = "default.redis6.x" */
  subnet_group_name    = aws_elasticache_subnet_group.redis_subnet_group.name
  security_group_ids    = [aws_security_group.redis_sg.id]
}

resource "aws_instance" "celery_worker" {
  ami = "ami-0efcece6bed30fd98"
  instance_type = "t3a.micro"
  subnet_id     = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.fastapi_sg.id, aws_security_group.redis_sg.id]
  key_name      = "Kevins2023"

  tags = {
    Name = "Celery Worker"
  }

  provisioner "remote-exec" {
    inline = local.code_setup
  }

  connection {
    type        = "ssh"
    user        = "ubuntu"
    private_key = file("~/.aws/kevins2023.pem")
    host        = self.public_ip
  }

  provisioner "local-exec" {
    command = format(local.env_setup, aws_instance.celery_worker.public_ip)
  }

  depends_on = [aws_elasticache_cluster.redis_cluster]
}

resource "aws_db_subnet_group" "db_subnet_group" {
  name       = "my-database-subnet-group"
  subnet_ids = [aws_subnet.public.id, aws_subnet.public2.id]

  tags = {
    Name = "My database subnet group"
  }
}

resource "aws_security_group" "rds_sg" {
  vpc_id = aws_vpc.main.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "RDS SG"
  }
}

resource "aws_db_instance" "litscenes" {
  identifier = "litscenes"
  allocated_storage    = 20
  storage_type         = "gp2"
  engine               = "postgres"
  engine_version       = "15.3" # Choose your preferred version
  instance_class       = "db.t3.micro"
  username             = "litscenes_user"
  password             = random_password.db_password.result
  /* parameter_group_name = "default.postgres13" */
  skip_final_snapshot  = true
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  db_subnet_group_name = aws_db_subnet_group.db_subnet_group.name

  publicly_accessible = true  # this is so that we can create the db , via terraform, from our local machine

  tags = {
    Name = "Postgres DB"
  }
}

provider "postgresql" {
  host            = aws_db_instance.litscenes.address
  port            = aws_db_instance.litscenes.port
  username        = aws_db_instance.litscenes.username
  password        = aws_db_instance.litscenes.password
  sslmode         = "require"
  connect_timeout = 60

}

resource "postgresql_database" "litscenes_db" {
  name  = "LitScenes"
  owner = "litscenes_user"

  depends_on = [aws_db_instance.litscenes]
}

/* resource "aws_security_group_rule" "rds_allow_fastapi" {
  type        = "ingress"
  from_port   = 5432
  to_port     = 5432
  protocol    = "tcp"
  security_group_id = aws_security_group.rds_sg.id
  source_security_group_id = aws_security_group.fastapi_sg.id
} */

resource "aws_security_group_rule" "rds_allow_all" {
  type        = "ingress"
  from_port   = 5432
  to_port     = 5432
  protocol    = "tcp"
  security_group_id = aws_security_group.rds_sg.id
  cidr_blocks = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "fastapi_allow_rds" {
  type        = "ingress"
  from_port   = 5432
  to_port     = 5432
  protocol    = "tcp"
  security_group_id = aws_security_group.fastapi_sg.id
  source_security_group_id = aws_security_group.rds_sg.id
}


output "fastapi_server_ip" {
  value = aws_instance.fastapi_server.public_ip
  description = "The public IP address of the FastAPI server."
}

output "db_endpoint" {
  value = aws_db_instance.litscenes.endpoint
  description = "The connection endpoint for the Postgres DB."
}

output "redis_url" {
  value = aws_elasticache_cluster.redis_cluster.cache_nodes[0].address
}

output "db_password" {
  value = random_password.db_password.result
  sensitive = true
}