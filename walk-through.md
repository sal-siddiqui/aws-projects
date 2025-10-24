# AWS Flask App Walk-through

## Step 1: Getting the Application Running

To get this application up and running, we need to set up a few AWS resources first:

- A DynamoDB table to store our data
- An S3 bucket for file storage
- An IAM role with the right permissions
- A user script to bootstrap our EC2 instance

We'll handle all of this using the AWS CLI.

### Setting Up the DynamoDB Table

Let's create a table called `Employees` to store our employee data:

```bash
aws dynamodb create-table \
    --table-name Employees \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST
```

### Creating the S3 Bucket

Next up, we'll create an S3 bucket. Make sure to jot down the bucket name—you'll need it later:

```bash
aws s3 mb s3://aws-flask-app-147779121814
```

### Configuring the IAM Role

For the IAM role, we'll need to create it first and then attach the necessary policies:

```bash
aws iam create-role \
  --role-name EC2Role \
  --assume-role-policy-document file://policies/trust-policy.json

aws iam put-role-policy \
  --role-name EC2Role \
  --policy-name EC2InlinePolicy \
  --policy-document file://policies/ec2-permissions.json

aws iam create-instance-profile --instance-profile-name EC2Role

aws iam add-role-to-instance-profile --instance-profile-name EC2Role --role-name EC2Role
```

### Preparing the User Script

Create a new file called `user-script.txt` and paste in the following content. **Important:** Replace the bucket name with the one you just created above.

```bash
#!/bin/bash -ex

yum -y install python3-pip git stress

git clone https://github.com/sal-siddiqui/aws-flask-app.git

cd aws-flask-app
pip install -r requirements.txt

export PHOTOS_BUCKET=aws-flask-app-147779121814

export AWS_DEFAULT_REGION=us-east-1
export DYNAMO_MODE=on
export FLASK_APP=application.py

/usr/local/bin/flask run --host=0.0.0.0 --port=80
```

Now we're ready to launch an EC2 instance through the management console. We'll assign the IAM role we just created and take the application for a spin to see how everything works together.

We’ve taken a closer look at the application and spotted two areas that could use some improvement:

- Image processing: Right now, the app minimizes images locally before uploading them to the cloud. We could move this step to a Lambda function instead. That way, the instance won’t get bogged down during peak times, and performance should improve overall.
- User cleanup: When a user is deleted, their images aren’t being removed from the storage bucket. Over time, this can lead to unnecessary storage costs for files that no one needs anymore.

## Step 2: Minimizing the Uploaded Image with Lambda
