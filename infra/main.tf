resource "aws_security_group" "app" {
  name_prefix = "ap-controls-app-"
  vpc_id = var.vpc_id
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_security_group" "db" {
  name_prefix = "ap-controls-db-"
  vpc_id = var.vpc_id
  ingress {
    from_port = 5432
    to_port = 5432
    protocol = "tcp"
    security_groups = [aws_security_group.app.id]
  }
}
resource "aws_db_subnet_group" "db" {
  subnet_ids = var.private_subnet_ids
}
resource "aws_db_instance" "db" {
  identifier = "ap-controls"
  engine = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.micro"
  allocated_storage = 20
  max_allocated_storage = 100
  storage_encrypted = true
  db_name = "controls"
  username = "platform_admin"
  manage_master_user_password = true
  db_subnet_group_name = aws_db_subnet_group.db.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible = false
  multi_az = true
  backup_retention_period = 7
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "ap-controls-final"
  auto_minor_version_upgrade = true
}
resource "aws_cloudwatch_log_group" "app" {
  name = "/ecs/ap-controls"
  retention_in_days = 30
}
resource "aws_ecs_cluster" "app" {
  name = "ap-controls"
  setting {
    name = "containerInsights"
    value = "enabled"
  }
}
resource "aws_iam_role" "execution" {
  name_prefix = "ap-controls-execution-"
  assume_role_policy = jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Principal={Service="ecs-tasks.amazonaws.com"},Action="sts:AssumeRole"}]})
}
resource "aws_iam_role_policy_attachment" "execution" {
  role = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
resource "aws_iam_role" "task" {
  name_prefix = "ap-controls-task-"
  assume_role_policy = aws_iam_role.execution.assume_role_policy
}
resource "aws_ecs_task_definition" "app" {
  family = "ap-controls"
  network_mode = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu = "256"
  memory = "512"
  execution_role_arn = aws_iam_role.execution.arn
  task_role_arn = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name="api", image=var.image, essential=true, user="10001", readonlyRootFilesystem=true,
    portMappings=[{containerPort=8080,protocol="tcp"}],
    environment=[{name="DB_HOST",value=aws_db_instance.db.address}],
    secrets=[
      {name="DB_USER",valueFrom="${aws_db_instance.db.master_user_secret[0].secret_arn}:username::"},
      {name="DB_PASSWORD",valueFrom="${aws_db_instance.db.master_user_secret[0].secret_arn}:password::"}
    ],
    mountPoints=[{sourceVolume="scratch",containerPath="/tmp",readOnly=false}],
    logConfiguration={logDriver="awslogs",options={awslogs-group=aws_cloudwatch_log_group.app.name,awslogs-region=var.region,awslogs-stream-prefix="api"}},
    healthCheck={command=["CMD-SHELL","python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8080/health',timeout=2)\""],interval=30,timeout=5,retries=3,startPeriod=30}
  }])
  volume { name = "scratch" }
}
resource "aws_ecs_service" "app" {
  name = "ap-controls"
  cluster = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count = 1
  launch_type = "FARGATE"
  platform_version = "1.4.0"
  network_configuration {
    subnets = var.private_subnet_ids
    security_groups = [aws_security_group.app.id]
    assign_public_ip = false
  }
  deployment_circuit_breaker {
    enable = true
    rollback = true
  }
  depends_on = [aws_iam_role_policy_attachment.execution, aws_iam_role_policy.database_secret]
}
resource "aws_sns_topic" "alerts" { name = "ap-controls-alerts" }
resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol = "email"
  endpoint = var.alarm_email
}
resource "aws_cloudwatch_metric_alarm" "cpu" {
  alarm_name = "ap-controls-high-cpu"
  namespace = "AWS/ECS"
  metric_name = "CPUUtilization"
  dimensions = {ClusterName=aws_ecs_cluster.app.name,ServiceName=aws_ecs_service.app.name}
  statistic = "Average"
  period = 60
  evaluation_periods = 5
  threshold = 80
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data = "missing"
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_iam_role_policy" "database_secret" {
  role = aws_iam_role.execution.id
  policy = jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Action=["secretsmanager:GetSecretValue"],Resource=aws_db_instance.db.master_user_secret[0].secret_arn}]})
}
