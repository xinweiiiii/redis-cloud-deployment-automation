########################
# Assume-role trust policy
########################
data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = var.trusted_principals
    }
  }
}

resource "aws_iam_role" "terraform_exec" {
  name                 = "terraform-exec-redis-vpc"
  assume_role_policy   = data.aws_iam_policy_document.assume_role.json
  description          = "Role assumed by Terraform to provision VPC, S3 state, and VPC peering, Redis Cloud"
  max_session_duration = 43200
  tags = { ManagedBy = "Terraform" }
}


# Render JSON template into a final policy document
locals {
  policy_path = "${path.module}/config/policy-terraform-exec.json"
  rendered_policy = templatefile(local.policy_path, {
    tf_state_bucket      = var.tf_state_bucket
    tf_state_prefix      = var.tf_state_prefix
    aws_region           = var.aws_region
    account_id           = var.aws_account_id
  })
}

resource "aws_iam_policy" "terraform_exec_combined" {
  name   = "TerraformExecCombined"
  policy = local.rendered_policy
}

resource "aws_iam_role_policy_attachment" "attach_combined" {
  role       = aws_iam_role.terraform_exec.name
  policy_arn = aws_iam_policy.terraform_exec_combined.arn
}
