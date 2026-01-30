# RDS PostgreSQL Module

resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "aws_secretsmanager_secret" "db_credentials" {
  name_prefix = "skymarshal-${var.environment}-rds-"
  description = "RDS credentials for SkyMarshal"

  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.master_username
    password = random_password.db_password.result
    engine   = "postgres"
    host     = aws_db_instance.main.endpoint
    port     = 5432
    dbname   = var.database_name
  })
}

resource "aws_security_group" "rds" {
  name_prefix = "skymarshal-${var.environment}-rds-"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "PostgreSQL access from private subnets"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = {
    Name = "skymarshal-${var.environment}-rds-sg"
  }
}

resource "aws_db_subnet_group" "main" {
  name_prefix = "skymarshal-${var.environment}-"
  description = "Database subnet group for SkyMarshal"
  subnet_ids  = var.database_subnets

  tags = {
    Name = "skymarshal-${var.environment}-db-subnet-group"
  }
}

resource "aws_db_parameter_group" "main" {
  name_prefix = "skymarshal-${var.environment}-pg14-"
  family      = "postgres14"
  description = "Custom parameter group for SkyMarshal"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # Log queries taking more than 1 second
  }
}

resource "aws_db_instance" "main" {
  identifier_prefix = "skymarshal-${var.environment}-"

  engine               = "postgres"
  engine_version       = "14.10"
  instance_class       = var.instance_class
  allocated_storage    = var.allocated_storage
  storage_type         = "gp3"
  storage_encrypted    = true

  db_name  = var.database_name
  username = var.master_username
  password = random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.main.name

  multi_az               = var.multi_az
  publicly_accessible    = false
  backup_retention_period = var.backup_retention
  backup_window          = "03:00-04:00"  # UTC
  maintenance_window     = "sun:04:00-sun:05:00"  # UTC

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  deletion_protection = var.environment == "prod" ? true : false
  skip_final_snapshot = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "skymarshal-${var.environment}-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  performance_insights_enabled    = true
  performance_insights_retention_period = 7

  tags = {
    Name        = "skymarshal-${var.environment}-rds"
    Environment = var.environment
    Backup      = "daily"
  }
}

# Outputs
output "endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.main.endpoint
}

output "instance_id" {
  description = "RDS instance ID"
  value       = aws_db_instance.main.id
}

output "credentials_secret_arn" {
  description = "ARN of the secrets manager secret containing credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "security_group_id" {
  description = "Security group ID for RDS"
  value       = aws_security_group.rds.id
}
