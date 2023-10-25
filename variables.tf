variable "openai_api_key" {
    description = "The OpenAI API key"
    default = "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"
    type = string
}

variable "git_url" {
    description = "The app's github url"
    default = "git@github.com:kvnn/LitScenes.git"
    type = string
}

variable "github_deploy_key_local_path" {
    description = "The local path to the github deploy key"
    default = "/Users/kevin/.aws/litscenes_github_deploy_key"
    type = string
}

variable "db_username" {
  description = "The username for the PostgreSQL database"
  default     = "litscenes_user"  # Optional default value
  type        = string
}

variable "db_name" {
    description  = "The name of the PostgreSQL database"
    default      = "litscenes"
    type         = string
}

variable "project_name" {
  description = "Value of the project name (which will be tagged for AWS resources)"
  type        = string
  default     = "litscenes"
}

variable "region" {
  type = string
  default = "us-west-2"
}

variable "availability_zone" {
  type = string
  default = "us-west-2c"
}

variable "instance_type" {
  type = string
  default = "t3a.micro"
}

variable "db_instance_type" {
  type = string
  default = "db.t3.micro"
}