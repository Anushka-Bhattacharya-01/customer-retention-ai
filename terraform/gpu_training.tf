# Optional GPU instance for model training.
# Off by default because GPU instances cost money every hour they run.
data "aws_ami" "deep_learning" {
  count       = var.enable_gpu_training ? 1 : 0
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)*"]
  }
}

data "aws_subnet" "training" {
  count = var.enable_gpu_training ? 1 : 0
  id    = var.training_subnet_id
}

# No inbound rules: access is through SSM Session Manager
resource "aws_security_group" "training" {
  count       = var.enable_gpu_training ? 1 : 0
  name        = "${var.project}-${var.environment}-training"
  description = "GPU training instance - outbound only"
  vpc_id      = data.aws_subnet.training[0].vpc_id

  egress {
    description = "Outbound for package installs, S3 and MLflow"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "gpu_training" {
  count                  = var.enable_gpu_training ? 1 : 0
  ami                    = data.aws_ami.deep_learning[0].id
  instance_type          = var.gpu_instance_type
  subnet_id              = var.training_subnet_id
  vpc_security_group_ids = [aws_security_group.training[0].id]
  iam_instance_profile   = aws_iam_instance_profile.training.name

  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }

  root_block_device {
    volume_size = 100
    volume_type = "gp3"
    encrypted   = true
  }

  tags = {
    Name = "${var.project}-${var.environment}-gpu-training"
  }
}
