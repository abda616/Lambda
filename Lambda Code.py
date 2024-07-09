import boto3
import json
from datetime import datetime

session = boto3.Session(region_name='us-east-1')
required_tags = {"dlm:managed": "true"}
launch_template_id_is = 'lt-06c85cce92beb2a6b'  # Replace with your Launch Template ID


def has_tags(element, tags):
    element_tags = {tag['Key']: tag['Value'] for tag in element.get('Tags', [])}
    for key, value in tags.items():
        if element_tags.get(key) != value:
            return False
    return True


def parse_date(item):
    return datetime.fromisoformat(item["CreationDate"].replace("Z", "+00:00"))


def get_latest_ami_id():
    ec2_client = session.client('ec2')
    response = ec2_client.describe_images(
        Owners=['self']
    )
    data = response['Images']
    data = [element for element in data if has_tags(element, required_tags)]
    images = sorted(data, key=parse_date, reverse=True)
    return images[0]['ImageId'] if images else None


def create_launch_template_version(latest_ami_id, launch_template_id):
    ec2_client = session.client('ec2')
    describe_response = ec2_client.describe_launch_templates(
        LaunchTemplateIds=[launch_template_id]
    )
    response = ec2_client.create_launch_template_version(
        LaunchTemplateId=launch_template_id,
        SourceVersion=str(describe_response['LaunchTemplates'][0]['LatestVersionNumber']),
        LaunchTemplateData={
            'ImageId': latest_ami_id
        }
    )
    return response['LaunchTemplateVersion']['VersionNumber']


def update_launch_template(latest_ami_id, launch_template_id):
    ec2_client = session.client('ec2')
    response = ec2_client.modify_launch_template(
        LaunchTemplateId=launch_template_id,
        DefaultVersion=str(create_launch_template_version(latest_ami_id, launch_template_id))
    )
    return response


def lambda_handler(event, context):
    latest_ami_id = get_latest_ami_id()
    if not latest_ami_id:
        return {
            'statusCode': 500,
            'body': json.dumps('No AMI found')
        }
    launch_template_id = launch_template_id_is
    response = update_launch_template(latest_ami_id, launch_template_id)
    return {
        'statusCode': 200,
        'body': json.dumps(
            f'Launch template updated with AMI ID {latest_ami_id},version is {response["LaunchTemplate"]["LatestVersionNumber"]}')
    }
