# PROJECT_HIRE_DESK_AI — Technology and Architecture

## Frontend

- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- Responsive web interface

## AWS backend

- Amazon API Gateway for the HTTP API
- AWS Lambda with Python
- Amazon DynamoDB for job application data
- Amazon Bedrock for job-description analysis
- Amazon CloudWatch for logs
- AWS Amplify Hosting for the frontend

## Infrastructure as Code

- AWS SAM
- Infrastructure must be reproducible from template.yaml

## MVP architecture rules

- Use a minimal serverless architecture.
- Use a single demo user.
- Do not implement Amazon Cognito unless the core MVP is finished.
- Do not use S3, SES, or EventBridge in the initial MVP.
- The frontend must never call DynamoDB or Amazon Bedrock directly.
- All AWS service calls must go through the backend API.
- Never expose AWS credentials or secrets in frontend code.
- Validate all API inputs.
- Validate all responses returned by Amazon Bedrock.
- Keep deterministic business rules separate from AI-generated explanations.
- The application must remain usable if the AI analysis temporarily fails.

## AI responsibilities

Amazon Bedrock may:

- extract job information;
- identify required skills;
- summarize responsibilities;
- identify languages and experience level;
- compare job requirements with a candidate profile;
- explain a recommended next action.

Amazon Bedrock must not save information without user validation.

## Next-action responsibilities

Dates, delays, priorities, and statuses must be calculated by deterministic
application rules.

AI may explain or personalize a recommendation, but it must not replace the
business rules.