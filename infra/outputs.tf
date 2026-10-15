output "cluster_name" { value = aws_ecs_cluster.app.name }
output "database_endpoint" { value = aws_db_instance.db.endpoint }
output "database_admin_secret_arn" { value = aws_db_instance.db.master_user_secret[0].secret_arn }
