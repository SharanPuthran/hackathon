# ============================================================
# SkyMarshal RDS PostgreSQL Database
# Production-ready database for multi-agent system
# ============================================================

# Variables for database configuration
variable "db_username" {
  description = "Master username for RDS PostgreSQL"
  type        = string
  default     = "skymarshal_admin"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "skymarshal_aviation"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro" # Free tier eligible, 2GB RAM
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20 # Minimum for RDS
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = false # Set true for production
}

# ============================================================
# Security Group for RDS
# ============================================================

resource "aws_security_group" "rds" {
  name_prefix = "skymarshal-rds-"
  description = "Security group for SkyMarshal RDS PostgreSQL"
  vpc_id      = data.aws_vpc.main.id

  # Allow PostgreSQL access from anywhere (restrict this in production)
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # TODO: Restrict to specific IPs/VPCs in production
    description = "PostgreSQL access for agents and development"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "skymarshal-rds-sg"
    Project     = "SkyMarshal"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

# ============================================================
# DB Subnet Group
# ============================================================

# Use existing VPC
data "aws_vpc" "main" {
  id = "vpc-02537189f171ae9b8"
}

# Get subnets in the VPC
data "aws_subnets" "main" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }
}

resource "aws_db_subnet_group" "skymarshal" {
  name_prefix = "skymarshal-db-subnet-"
  subnet_ids  = data.aws_subnets.main.ids
  description = "Subnet group for SkyMarshal RDS"

  tags = {
    Name        = "skymarshal-db-subnet-group"
    Project     = "SkyMarshal"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

# ============================================================
# RDS PostgreSQL Instance
# ============================================================

resource "aws_db_instance" "skymarshal_postgres" {
  # Instance Configuration
  identifier     = "skymarshal-aviation-db"
  engine         = "postgres"
  engine_version = "16.3" # Latest stable PostgreSQL version

  # Instance Size
  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage
  storage_type      = "gp3" # General Purpose SSD (gp3 is more cost-effective than gp2)
  storage_encrypted = true

  # Database Configuration
  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result
  port     = 5432

  # Network Configuration
  db_subnet_group_name   = aws_db_subnet_group.skymarshal.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = true # Temporarily enabled for data loading

  # Backup Configuration
  backup_retention_period = 7 # Keep backups for 7 days
  backup_window          = "03:00-04:00" # UTC
  maintenance_window     = "mon:04:00-mon:05:00" # UTC

  # High Availability (optional, increases cost)
  multi_az = false # Set true for production HA

  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  monitoring_interval             = 60 # Enhanced monitoring every 60 seconds
  monitoring_role_arn            = aws_iam_role.rds_monitoring.arn

  # Performance Insights
  performance_insights_enabled    = true
  performance_insights_retention_period = 7 # Free tier: 7 days

  # Deletion Protection
  deletion_protection = var.enable_deletion_protection
  skip_final_snapshot = true # Set false for production

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  # Apply changes immediately (set false for production)
  apply_immediately = true

  tags = {
    Name        = "skymarshal-aviation-db"
    Project     = "SkyMarshal"
    Environment = "production"
    ManagedBy   = "Terraform"
    Purpose     = "Multi-agent aviation data"
  }
}

# ============================================================
# Random Password for Database
# ============================================================

resource "random_password" "db_password" {
  length  = 32
  special = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Store password in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name_prefix = "skymarshal/rds/password-"
  description = "Master password for SkyMarshal RDS PostgreSQL"

  tags = {
    Name        = "skymarshal-rds-password"
    Project     = "SkyMarshal"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id = aws_secretsmanager_secret.db_password.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
    engine   = "postgres"
    host     = aws_db_instance.skymarshal_postgres.address
    port     = aws_db_instance.skymarshal_postgres.port
    dbname   = var.db_name
    endpoint = aws_db_instance.skymarshal_postgres.endpoint
  })
}

# ============================================================
# IAM Role for RDS Enhanced Monitoring
# ============================================================

resource "aws_iam_role" "rds_monitoring" {
  name_prefix = "skymarshal-rds-monitoring-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "skymarshal-rds-monitoring-role"
    Project     = "SkyMarshal"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# ============================================================
# Outputs
# ============================================================

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.skymarshal_postgres.endpoint
}

output "rds_address" {
  description = "RDS PostgreSQL address (hostname)"
  value       = aws_db_instance.skymarshal_postgres.address
}

output "rds_port" {
  description = "RDS PostgreSQL port"
  value       = aws_db_instance.skymarshal_postgres.port
}

output "rds_database_name" {
  description = "Database name"
  value       = aws_db_instance.skymarshal_postgres.db_name
}

output "rds_username" {
  description = "Master username"
  value       = var.db_username
  sensitive   = true
}

output "rds_password_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the database password"
  value       = aws_secretsmanager_secret.db_password.arn
}

output "rds_connection_string" {
  description = "PostgreSQL connection string (password stored in Secrets Manager)"
  value       = "postgresql://${var.db_username}@${aws_db_instance.skymarshal_postgres.address}:${aws_db_instance.skymarshal_postgres.port}/${var.db_name}"
  sensitive   = true
}

# ============================================================
# CloudWatch Alarms for Monitoring
# ============================================================

resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  alarm_name          = "skymarshal-rds-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This metric monitors RDS CPU utilization"
  alarm_actions       = [] # Add SNS topic ARN for notifications

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.skymarshal_postgres.id
  }

  tags = {
    Name        = "skymarshal-rds-cpu-alarm"
    Project     = "SkyMarshal"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

resource "aws_cloudwatch_metric_alarm" "database_storage" {
  alarm_name          = "skymarshal-rds-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 2000000000 # 2GB in bytes
  alarm_description   = "This metric monitors RDS free storage space"
  alarm_actions       = [] # Add SNS topic ARN for notifications

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.skymarshal_postgres.id
  }

  tags = {
    Name        = "skymarshal-rds-storage-alarm"
    Project     = "SkyMarshal"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

resource "aws_cloudwatch_metric_alarm" "database_connections" {
  alarm_name          = "skymarshal-rds-high-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80 # Adjust based on max_connections setting
  alarm_description   = "This metric monitors RDS database connections"
  alarm_actions       = [] # Add SNS topic ARN for notifications

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.skymarshal_postgres.id
  }

  tags = {
    Name        = "skymarshal-rds-connections-alarm"
    Project     = "SkyMarshal"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}
