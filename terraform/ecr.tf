# Container registry for the model API image
resource "aws_ecr_repository" "churn_api" {
  name                 = "${var.project}/churn-api"
  image_tag_mutability = "IMMUTABLE" # a tag always points to the same image

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

# Keep only the last 20 images
resource "aws_ecr_lifecycle_policy" "churn_api" {
  repository = aws_ecr_repository.churn_api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 20 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 20
      }
      action = { type = "expire" }
    }]
  })
}
