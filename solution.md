# Lambda + DynamoDB Demo (Solution)

## Step 1: Create the DynamoDB Table

We'll create a DynamoDB table named employees with id as the primary key. Since this is a demo, we'll use the pay-per-request billing mode to keep things simple and avoid capacity planning.

```bash
aws dynamodb create-table \
    --table-name employees \
    --billing-mode PAY_PER_REQUEST \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH
```

## Step 2: Set Up an IAM Role

Our Lambda function needs permissions to interact with DynamoDB and to write its own logs. We handle this by creating an IAM role and attaching the necessary policies.

```bash
# Create the role with a trust policy that allows Lambda to assume it
aws iam create-role \
    --role-name lambda-dynamodb-role \
    --assume-role-policy-document file://aws/policies/LambdaTrustPolicy.json

# Attach a policy for full DynamoDB access
aws iam attach-role-policy \
    --role-name lambda-dynamodb-role \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

# Attach a policy so the function can write to CloudWatch Logs
aws iam attach-role-policy \
    --role-name lambda-dynamodb-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

**A Quick Note on Security**: Using broad, managed policies is great for getting started. For a production app, you should create a custom policy that follows the principle of least privilege, granting only the specific permissions your function actually needs

## Step 3: Deploy the Lambda Function

Now for the main event: the Lambda function itself. I've pre-written the code in `lambda_function/lambda_function.py`. This command packages and deploys it to AWS.

```bash
aws lambda create-function \
    --function-name lambda-function \
    --runtime python3.12 \
    --role arn:aws:iam::147997121814:role/lambda-dynamodb-role \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://lambda_function/lambda_function.zip
```

## Step 4: Create a Public API Endpoint

To call our function from the web, we need to give it a public endpoint. While API Gateway is the full-featured solution, a Function URL is perfect for a simple, direct endpoint like this.

First, let's create the Function URL with public access:

```bash
aws lambda create-function-url-config \
  --function-name lambda-function \
  --auth-type NONE \
  --cors AllowOrigins="*"
```

Then, we grant the necessary permissions for public invocation:

```bash
aws lambda add-permission \
  --function-name lambda-function \
  --statement-id FunctionURLAllowPublicAccess \
  --principal "*" \
  --action lambda:InvokeFunctionUrl \
  --function-url-auth-type NONE

aws lambda add-permission \
  --function-name lambda-function \
  --statement-id FunctionURLAllowInvokeAction \
  --principal "*" \
  --action lambda:InvokeFunction
```

## Conclusion

And that's it! You've now got a serverless API running. Your Lambda function is live, connected to a database, and accessible via a public URL. The next step would be to test it by hitting that endpoint with a tool like curl or Postman.
