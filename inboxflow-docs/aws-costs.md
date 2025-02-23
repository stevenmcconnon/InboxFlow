# AWS Cost Estimates

## Services & Estimated Costs

| Service              | Estimated Cost (1 User) | Estimated Cost (10 Users) | Estimated Cost (100 Users) |
|----------------------|------------------------|--------------------------|--------------------------|
| ECS/Fargate         | \$10                    | \$50                      | \$500                      |
| AWS Lambda          | \$2                     | \$5                        | \$10                        |
| API Gateway         | \$2                     | \$10                       | \$50                        |
| S3 & CloudFront     | \$1                     | \$3                        | \$8                         |
| SNS & SQS          | \$1                     | \$3                        | \$10                        |
| Aurora Serverless   | \$3–\$5                 | \$10–\$15                  | \$30–\$40                   |
| CloudWatch          | \$3–\$5                 | \$10                       | \$20                        |
| ECR                 | \$1                     | \$1                        | \$1                         |
| **Total**          | **\$22–\$28**           | **~\$114**                 | **~\$675**                  |

## Cost Reduction Strategies

- Use **Aurora Serverless**, which scales to zero when idle.
- Autoscale **ECS/Fargate** workers, ensuring no idle compute charges.
- Optimize **API Gateway** with caching and request throttling.
- Minimize log storage in **CloudWatch**.
