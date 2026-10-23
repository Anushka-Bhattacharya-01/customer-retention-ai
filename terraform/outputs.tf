output "artifacts_bucket" {
  description = "S3 bucket for MLflow artifacts and models"
  value       = aws_s3_bucket.ml_artifacts.bucket
}

output "ecr_repository_url" {
  description = "ECR repository for the model API image"
  value       = aws_ecr_repository.churn_api.repository_url
}

output "training_role_arn" {
  description = "IAM role used by the training instance"
  value       = aws_iam_role.training.arn
}

output "model_api_role_arn" {
  description = "IRSA role for the model API (empty if no EKS OIDC provider was given)"
  value       = local.create_irsa ? aws_iam_role.model_api[0].arn : ""
}

output "gpu_training_instance_id" {
  description = "GPU training instance ID (empty if disabled)"
  value       = var.enable_gpu_training ? aws_instance.gpu_training[0].id : ""
}
