# Least-privilege access to the artifacts bucket
data "aws_iam_policy_document" "artifacts_rw" {
  statement {
    sid       = "ListBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.ml_artifacts.arn]
  }
  statement {
    sid       = "ReadWriteObjects"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.ml_artifacts.arn}/*"]
  }
}

data "aws_iam_policy_document" "artifacts_read_models" {
  statement {
    sid       = "ReadModels"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.ml_artifacts.arn}/models/*"]
  }
}

# ---- Training role (used by the GPU EC2 instance) ----
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "training" {
  name               = "${var.project}-${var.environment}-training"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy" "training_artifacts" {
  name   = "artifacts-read-write"
  role   = aws_iam_role.training.id
  policy = data.aws_iam_policy_document.artifacts_rw.json
}

# Session Manager access instead of SSH keys / open port 22
resource "aws_iam_role_policy_attachment" "training_ssm" {
  role       = aws_iam_role.training.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "training" {
  name = "${var.project}-${var.environment}-training"
  role = aws_iam_role.training.name
}

# ---- Model API role for EKS (IRSA), only if an EKS OIDC provider is given ----
locals {
  create_irsa = var.eks_oidc_provider_arn != "" && var.eks_oidc_provider_url != ""
}

data "aws_iam_policy_document" "irsa_assume" {
  count = local.create_irsa ? 1 : 0

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [var.eks_oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${var.eks_oidc_provider_url}:sub"
      values   = ["system:serviceaccount:${var.k8s_namespace}:${var.k8s_service_account}"]
    }
    condition {
      test     = "StringEquals"
      variable = "${var.eks_oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "model_api" {
  count              = local.create_irsa ? 1 : 0
  name               = "${var.project}-${var.environment}-model-api"
  assume_role_policy = data.aws_iam_policy_document.irsa_assume[0].json
}

resource "aws_iam_role_policy" "model_api_read" {
  count  = local.create_irsa ? 1 : 0
  name   = "read-models"
  role   = aws_iam_role.model_api[0].id
  policy = data.aws_iam_policy_document.artifacts_read_models.json
}

# The assistant may call only one Bedrock model (least privilege)
data "aws_iam_policy_document" "bedrock_invoke" {
  statement {
    sid       = "InvokeAssistantModel"
    actions   = ["bedrock:InvokeModel"] # the Converse API uses this permission
    resources = ["arn:aws:bedrock:${var.region}::foundation-model/${var.bedrock_model_id}"]
  }
}

resource "aws_iam_role_policy" "model_api_bedrock" {
  count  = local.create_irsa ? 1 : 0
  name   = "invoke-bedrock-model"
  role   = aws_iam_role.model_api[0].id
  policy = data.aws_iam_policy_document.bedrock_invoke.json
}
