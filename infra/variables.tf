variable "region" {
  type = string
  default = "eu-west-2"
}
variable "vpc_id" { type = string }
variable "private_subnet_ids" {
  type = list(string)
  validation {
    condition = length(var.private_subnet_ids) >= 2
    error_message = "Supply private subnets in at least two availability zones."
  }
}
variable "image" {
  type = string
  description = "ECR image URI pinned to a sha256 digest"
  validation {
    condition = can(regex("@sha256:[a-f0-9]{64}$", var.image))
    error_message = "Pin the container image by SHA256 digest."
  }
}
variable "alarm_email" { type = string }
