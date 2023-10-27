terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
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

  lifecycle {
    ignore_changes = all
  }

  tags = {
    Name = "Main VPC"
    Project = var.project_name
  }
}

resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
  availability_zone = "us-west-2a"
  map_public_ip_on_launch = true
  tags = {
    Name = "Public Subnet"
    Project = var.project_name
  }
}

resource "aws_subnet" "public2" {
  vpc_id     = aws_vpc.main.id 
  cidr_block = "10.0.3.0/24"
  availability_zone = "us-west-2b"

  tags = {
    Name = "Public Subnet 2"
    Project = var.project_name
  }
}

resource "aws_subnet" "private" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.2.0/24"
  tags = {
    Name = "Private Subnet"
    Project = var.project_name
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Project = var.project_name
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Project = var.project_name
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# EC2 for FastAPI Server

resource "aws_security_group" "fastapi_sg" {
  name = "${var.project_name}_app_sg"
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
    Project = var.project_name
  }
}

resource "random_password" "db_password" {
  length           = 16
  special          = false
}


locals {
  code_setup = [
    # TODO: I don't think DEBIAN_FRONTEND is supported, and I believe it will be ignored
    "echo 'export DEBIAN_FRONTEND=noninteractive' | sudo tee -a /etc/environment",
    "sudo apt-get update >> /tmp/apt-get-update.log 2>&1",
    # TODO: apt-get update shouldn't be necessary again, but, I'm not sure.
    "sudo apt-get update && sudo apt-get --assume-yes install -y python3-pip libpq-dev postgresql nginx >> /tmp/apt-get-install.log 2>&1",
    "sudo pip install psycopg2-binary >> /tmp/pip-install-pscyopg2-binary.log 2>&1",
    "chmod 600 /home/ubuntu/.ssh/${var.project_name}_deploy_key",
    "ssh-add /home/ubuntu/.ssh/${var.project_name}_deploy_key",
    "ssh-keyscan github.com >> /home/ubuntu/.ssh/known_hosts",
    "git clone ${var.git_url} >> /tmp/git-clone.log 2>&1",
    "sudo pip install -r /home/ubuntu/${var.repo_name}/app/requirements.prod.txt >> /tmp/pip-install.log 2>&1",
    "mkdir -p /home/ubuntu/${var.repo_name}/app/static/img"
  ]

  env_setup = [
    # create .env and load env vars into it
    "echo 'IN_CLOUD=${var.in_cloud}' > /home/ubuntu/${var.repo_name}/app/.env",
    "echo 'S3_BUCKET_NAME_MEDIA=${var.s3_bucket_name_media}' >> /home/ubuntu/${var.repo_name}/app/.env",
    "echo 'OPENAI_API_KEY=${var.openai_api_key}' >> /home/ubuntu/${var.repo_name}/app/.env",
    "echo 'DB_CONNECTION=postgresql+psycopg2://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.db_instance.endpoint}/${var.db_name}' >> /home/ubuntu/${var.repo_name}/app/.env",
    "echo 'CELERY_BROKER_URL=redis://${aws_elasticache_cluster.redis_cluster.cache_nodes[0].address}:6379/0' >> /home/ubuntu/${var.repo_name}/app/.env",
    "echo 'CELERY_RESULT_BACKEND=redis://${aws_elasticache_cluster.redis_cluster.cache_nodes[0].address}:6379/0' >> /home/ubuntu/${var.repo_name}/app/.env",
    "echo 'REDIS_URL=redis://${aws_elasticache_cluster.redis_cluster.cache_nodes[0].address}:6379/0' >> /home/ubuntu/${var.repo_name}/app/.env",
    # copy all env vars to /etc/environment
    "cat /home/ubuntu/${var.repo_name}/app/.env | sed 's/^\\\"\\(.*\\)\\\"$/\\1/' | while read -r line || [[ -n \\\"$line\\\" ]]; do echo \\\"$line\\\" | sudo tee -a /etc/environment; done",
  ]
}

resource "aws_instance" "fastapi_server" {
  ami = "ami-0efcece6bed30fd98"
  instance_type = var.instance_type
  subnet_id     = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.fastapi_sg.id, aws_security_group.redis_sg.id]
  key_name      = "Kevins2023"

  tags = {
    Name = "FastAPI Server"
    Project = var.project_name
  }

  # git clone access
  provisioner "file" {
    source      = var.github_deploy_key_local_path
    destination = "/home/ubuntu/.ssh/${var.project_name}_deploy_key"
  }

  provisioner "remote-exec" {
    inline = concat(
      local.code_setup,
      local.env_setup,
      [
        "cd /home/ubuntu/${var.repo_name}/app",
        "source .env || true",
        "export PGPASSWORD=${random_password.db_password.result} && psql -h $(echo ${aws_db_instance.db_instance.endpoint} | sed 's/:5432//') -U ${var.db_username} -d postgres -c 'create database ${var.db_name};' >> /tmp/db-create.log 2>&1",

        # Try to run alembic mgiration
        "alembic upgrade head >> /tmp/alembic-upgrade.log 2>&1 || (echo 'failed, .env is' >> /tmp/alembic-upgrade.log && cat .env >> /tmp/alembic-upgrade.log && false) || true",

        # Set up uvicorn as a systemd service
        "echo '[Unit]' | sudo tee /etc/systemd/system/fastapi.service > /dev/null",
        "echo 'Description=FastAPI app' | sudo tee -a /etc/systemd/system/fastapi.service > /dev/null",
        "echo 'After=network.target' | sudo tee -a /etc/systemd/system/fastapi.service > /dev/null",
        "echo '' | sudo tee -a /etc/systemd/system/fastapi.service > /dev/null",
        "echo '[Service]' | sudo tee -a /etc/systemd/system/fastapi.service > /dev/null",
        "echo 'User=root' | sudo tee -a /etc/systemd/system/fastapi.service > /dev/null",
        "echo 'WorkingDirectory=/home/ubuntu/${var.repo_name}/app/' | sudo tee -a /etc/systemd/system/fastapi.service > /dev/null",
        "echo 'ExecStart=/usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000' | sudo tee -a /etc/systemd/system/fastapi.service > /dev/null",
        "echo 'Restart=always' | sudo tee -a /etc/systemd/system/fastapi.service > /dev/null",
        "echo '' | sudo tee -a /etc/systemd/system/fastapi.service > /dev/null",
        "echo '[Install]' | sudo tee -a /etc/systemd/system/fastapi.service > /dev/null",
        "echo 'WantedBy=multi-user.target' | sudo tee -a /etc/systemd/system/fastapi.service > /dev/null",
        
        # Reload systemd, enable and start the FastAPI service
        "sudo systemctl daemon-reload",
        "sudo systemctl enable fastapi.service",
        "sudo systemctl start fastapi.service",

        # Configure Reverse Proxy for Uvicorn
        "echo 'server {' | sudo tee /etc/nginx/sites-available/fastapi",
        "echo '    listen 80;' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '    location / {' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '        proxy_pass http://127.0.0.1:8000;' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '        proxy_set_header Host \$host;' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '        proxy_set_header X-Real-IP \$remote_addr;' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '        proxy_set_header X-Forwarded-Proto \$scheme;' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '        # WebSocket support' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '        proxy_http_version 1.1;' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '        proxy_set_header Upgrade \$http_upgrade;' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '        proxy_set_header Connection \"upgrade\";' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '    }' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '    location /static/ {' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '        alias /home/ubuntu/\${var.repo_name}/app/static/;' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '    }' | sudo tee -a /etc/nginx/sites-available/fastapi",
        "echo '}' | sudo tee -a /etc/nginx/sites-available/fastapi",
        
        # Create symlink to enable the configuration
        "sudo ln -s /etc/nginx/sites-available/fastapi /etc/nginx/sites-enabled",

        # Disable the default site
        "sudo rm -f /etc/nginx/sites-enabled/default",

        # Reload NGINX
        "sudo systemctl reload nginx",

        # Set file permissions
        "sudo chmod +x /home /home/ubuntu /home/ubuntu/${var.repo_name} /home/ubuntu/${var.repo_name}/app",
        "sudo chown -R www-data:www-data /home/ubuntu/${var.repo_name}/app/static/"
      ]
    )
  }

  connection {
    type        = "ssh"
    user        = "ubuntu"
    private_key = file(var.server_ssh_key_local_path)
    host        = self.public_ip
  }

  depends_on = [aws_elasticache_cluster.redis_cluster, aws_db_instance.db_instance]
}

/* resource "null_resource" "post_apply_tasks" {
  depends_on = [aws_instance.fastapi_server]

  triggers = {
    instance_id = aws_instance.fastapi_server.id  # Replace with the actual resource id
  }

  provisioner "remote-exec" {
    inline = [
      "cd /home/ubuntu/${var.repo_name}/app",
      "for i in {1..5}; do export PGPASSWORD=${random_password.db_password.result} && psql -h $(echo ${aws_db_instance.db_instance.endpoint} | sed 's/:5432//') -U ${var.db_username} -d postgres -c 'create database ${var.db_name};' && break || sleep 15; done >> /tmp/db-create.log 2>&1",
      "alembic upgrade head >> /tmp/alembic-upgrade.log 2>&1 || exit 1"
    ]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      private_key = file(var.server_ssh_key_local_path)
      host        = aws_instance.fastapi_server.public_ip  # Replace with the actual resource attribute
    }
  }
} */


# Celery Worker w/ Elasticache Redis backend
resource "aws_elasticache_subnet_group" "redis_subnet_group" {
  name       = "redis-subnet-group"
  subnet_ids = [aws_subnet.public.id, aws_subnet.public2.id]

  tags = {
    Project = var.project_name
  }
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

  tags = {
    Project = var.project_name
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

  tags = {
    Project = var.project_name
  }
}

resource "aws_instance" "celery_worker" {
  ami = "ami-0efcece6bed30fd98"
  instance_type = var.instance_type
  subnet_id     = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.fastapi_sg.id, aws_security_group.redis_sg.id]
  key_name      = "Kevins2023"

  tags = {
    Name = "Celery Worker"
    Project = var.project_name
  }

  # git clone access
  provisioner "file" {
    source      = var.github_deploy_key_local_path
    destination = "/home/ubuntu/.ssh/${var.project_name}_deploy_key"
  }

  provisioner "remote-exec" {
    inline = concat(
      local.code_setup,
      local.env_setup,
      [
        # Create the systemd service file for the Celery worker
        "echo '[Unit]' | sudo tee /etc/systemd/system/celery-worker.service",
        "echo 'Description=Celery Worker' | sudo tee -a /etc/systemd/system/celery-worker.service",
        "echo 'After=network.target' | sudo tee -a /etc/systemd/system/celery-worker.service",
        "echo '' | sudo tee -a /etc/systemd/system/celery-worker.service",
        "echo '[Service]' | sudo tee -a /etc/systemd/system/celery-worker.service",
        "echo 'Type=simple' | sudo tee -a /etc/systemd/system/celery-worker.service",
        "echo 'User=ubuntu' | sudo tee -a /etc/systemd/system/celery-worker.service",
        "echo 'WorkingDirectory=/home/ubuntu/${var.repo_name}/app' | sudo tee -a /etc/systemd/system/celery-worker.service",
        "echo 'ExecStart=/usr/local/bin/celery -A worker.celery worker --loglevel=info' | sudo tee -a /etc/systemd/system/celery-worker.service",
        "echo 'Restart=always' | sudo tee -a /etc/systemd/system/celery-worker.service",
        "echo '' | sudo tee -a /etc/systemd/system/celery-worker.service",
        "echo '[Install]' | sudo tee -a /etc/systemd/system/celery-worker.service",
        "echo 'WantedBy=multi-user.target' | sudo tee -a /etc/systemd/system/celery-worker.service",

        # Reload systemd, enable and start the Celery worker service
        "sudo systemctl daemon-reload",
        "sudo systemctl enable celery-worker",
        "sudo systemctl start celery-worker"
      ]
    )
  }

  connection {
    type        = "ssh"
    user        = "ubuntu"
    private_key = file(var.server_ssh_key_local_path)
    host        = self.public_ip
  }

  depends_on = [aws_elasticache_cluster.redis_cluster, aws_db_instance.db_instance]
}

resource "aws_iam_policy" "celery_worker_s3_write_policy" {
  name        = "celery-worker-s3-write-policy"
  description = "Allows writing to the litscenes-scenes S3 bucket"
  policy      = <<-EOF
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": "s3:PutObject",
          "Resource": "arn:aws:s3:::litscenes-scenes/*"
        }
      ]
    }
    EOF
}

resource "aws_iam_role_policy_attachment" "celery_worker_s3_write_policy_attach" {
  role       = aws_iam_role.celery_worker_role.name
  policy_arn = aws_iam_policy.celery_worker_s3_write_policy.arn
}


resource "aws_db_subnet_group" "db_subnet_group" {
  name       = "${var.project_name}-database-subnet-group"
  subnet_ids = [aws_subnet.public.id, aws_subnet.public2.id]

  tags = {
    Name = "${var.project_name} database subnet group"
    Project = var.project_name
  }
}

resource "aws_security_group" "rds_sg" {
  name = "${var.project_name}_rds_sg"
  vpc_id = aws_vpc.main.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "RDS SG"
    Project = var.project_name
  }
}

resource "aws_db_instance" "db_instance" {
  identifier = var.project_name
  allocated_storage    = 20
  storage_type         = "gp2"
  engine               = "postgres"
  engine_version       = "15.3" # Choose your preferred version
  instance_class       = var.db_instance_type
  username             = var.db_username
  password             = random_password.db_password.result
  /* parameter_group_name = "default.postgres13" */
  skip_final_snapshot  = true
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  db_subnet_group_name = aws_db_subnet_group.db_subnet_group.name

  publicly_accessible = true  # this is so that we can create the db , via terraform, from our local machine

  tags = {
    Name = "Postgres DB"
    Project = var.project_name
  }
}

# allow access to the rds instance from the internet
resource "aws_security_group_rule" "rds_allow_all" {
  type        = "ingress"
  from_port   = 5432
  to_port     = 5432
  protocol    = "tcp"
  security_group_id = aws_security_group.rds_sg.id
  cidr_blocks = ["0.0.0.0/0"]
  # replace cidr_blocks with the following to only allow traffic from the fastapi server
  # source_security_group_id = aws_security_group.fastapi_sg.id
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

output "app_server_public_url" {
  value = aws_instance.fastapi_server.public_ip
  description = "The public URL to access the FastAPI application."
}

output "celery_server_public_url" {
  value = aws_instance.celery_worker.public_ip
  description = "The public URL to access the Celery application."
}

output "db_endpoint" {
  value = aws_db_instance.db_instance.endpoint
  description = "The connection endpoint for the Postgres DB."
}

output "redis_url" {
  value = aws_elasticache_cluster.redis_cluster.cache_nodes[0].address
}

output "db_password" {
  value = random_password.db_password.result
  sensitive = true
}