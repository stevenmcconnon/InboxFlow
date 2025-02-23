# File: inboxflow-infrastructure/ecs.tf

# This file defines ECS resources for deploying Dockerized services (e.g., the Dispatcher).
# Note: These resources are created only if deploy_ecs is set to true.

resource "aws_ecs_cluster" "inboxflow_cluster" {
  count = var.deploy_ecs ? 1 : 0
  name  = "inboxflow-cluster"
}

resource "aws_iam_role" "ecs_execution_role" {
  count = var.deploy_ecs ? 1 : 0
  name  = "inboxflow-ecs-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  count      = var.deploy_ecs ? 1 : 0
  role       = aws_iam_role.ecs_execution_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Example ECS Task Definition for the Dispatcher Service
resource "aws_ecs_task_definition" "dispatcher_task" {
  count                   = var.deploy_ecs ? 1 : 0
  family                  = "inboxflow_dispatcher"
  requires_compatibilities = ["FARGATE"]
  network_mode            = "awsvpc"
  cpu                     = "256"
  memory                  = "512"
  execution_role_arn      = aws_iam_role.ecs_execution_role[0].arn

  container_definitions = jsonencode([
    {
      name      = "dispatcher",
      image     = "inboxflow_dispatcher:latest",
      essential = true,
      portMappings = [
        {
          containerPort = 8080,
          hostPort      = 8080,
          protocol      = "tcp"
        }
      ]
    }
  ])
}

# Example ECS Service for the Dispatcher Service
resource "aws_ecs_service" "dispatcher_service" {
  count           = var.deploy_ecs ? 1 : 0
  name            = "inboxflow_dispatcher-service"
  cluster         = aws_ecs_cluster.inboxflow_cluster[0].id
  task_definition = aws_ecs_task_definition.dispatcher_task[0].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.ecs_subnet_ids
    security_groups  = var.ecs_security_group_ids
    assign_public_ip = true
  }

  depends_on = [
    aws_ecs_cluster.inboxflow_cluster,
    aws_iam_role_policy_attachment.ecs_execution_role_policy
  ]
}